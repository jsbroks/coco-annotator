"""COCO <-> YOLO label conversion (pure functions and the API)."""
import io
import os
import zipfile

import pytest

from geometry.yolo_format import coco_to_yolo, data_yaml, detect_task, parse_names, read_zip, yolo_to_coco

W, H = 200, 100
IMAGES = [{"id": 1, "file_name": "a.jpg", "width": W, "height": H},
          {"id": 2, "file_name": "sub/b.png", "width": W, "height": H}]


def _coco(annotations, keypoints=None):
    cats = [{"id": 10, "name": "ship"}, {"id": 20, "name": "car"}]
    if keypoints:
        cats[0]["keypoints"] = keypoints
    return {"images": IMAGES, "categories": cats, "annotations": annotations}


def _values(line):
    return [float(v) for v in line.split()]


def test_detect_round_trip():
    coco = _coco([{"id": 1, "image_id": 1, "category_id": 20, "bbox": [20, 10, 40, 30],
                   "segmentation": [[20, 10, 60, 10, 60, 40, 20, 40]]}])
    out = coco_to_yolo(coco, "detect")
    assert out["names"] == ["ship", "car"]
    assert _values(out["labels"][1][0]) == pytest.approx([1, 0.2, 0.25, 0.2, 0.3])
    assert out["labels"][2] == []

    back, stats = yolo_to_coco({"a": out["labels"][1][0]}, IMAGES, names=out["names"])
    assert stats["task"] == "detect" and stats["matched"] == 1
    ann = back["annotations"][0]
    assert ann["bbox"] == pytest.approx([20, 10, 40, 30])
    assert back["categories"][ann["category_id"] - 1]["name"] == "car"


def test_segment_merges_multi_polygons():
    poly1 = [10, 10, 30, 10, 30, 30, 10, 30]
    poly2 = [100, 50, 120, 50, 120, 70]
    coco = _coco([{"id": 1, "image_id": 1, "category_id": 10, "segmentation": [poly1, poly2]}])
    line = coco_to_yolo(coco, "segment")["labels"][1][0]
    values = _values(line)
    assert values[0] == 0 and (len(values) - 1) // 2 == 4 + 3 + 2  # both rings + 2 bridge points

    back, stats = yolo_to_coco({"a.txt": "0 0.1 0.1 0.5 0.1 0.5 0.9"}, IMAGES, names=["ship"])
    assert stats["task"] == "segment"
    ann = back["annotations"][0]
    assert ann["segmentation"] == [[20, 10, 100, 10, 100, 90]]
    assert ann["area"] == pytest.approx(80 * 80 / 2)


def test_obb_round_trip_keeps_orientation():
    from geometry import rbbox_to_polygon
    rbbox = [100, 50, 60, 20, 30]
    coco = _coco([{"id": 1, "image_id": 1, "category_id": 10, "isrbbox": True, "rbbox": rbbox,
                   "segmentation": [rbbox_to_polygon(rbbox)]},
                  # a plain polygon gets the minimum-area rectangle
                  {"id": 2, "image_id": 2, "category_id": 10,
                   "segmentation": [[10, 10, 50, 10, 50, 30, 10, 30, 30, 20]]}])
    out = coco_to_yolo(coco, "obb")
    assert len(_values(out["labels"][1][0])) == 9 and len(out["labels"][2]) == 1
    assert coco_to_yolo(coco, "obb", only_rbbox=True)["skipped"] == 1

    back, stats = yolo_to_coco({"a": out["labels"][1][0]}, IMAGES, names=out["names"])
    assert stats["task"] == "obb"
    ann = back["annotations"][0]
    assert ann["isrbbox"] and ann["rbbox"] == pytest.approx(rbbox, abs=0.05)


def test_pose_round_trip():
    labels = ["nose", "left_eye", "right_eye"]
    coco = _coco([{"id": 1, "image_id": 1, "category_id": 10, "bbox": [0, 0, 100, 50],
                   "keypoints": [50, 25, 2, 0, 0, 0, 80, 40, 1]}], keypoints=labels)
    out = coco_to_yolo(coco, "pose")
    assert out["kpt_shape"] == [3, 3]
    assert out["flip_idx"] == [0, 2, 1]
    yaml_text = data_yaml(out["names"], "pose", out["kpt_shape"], out["flip_idx"])
    names, kpt_shape = parse_names(yaml_text, "data.yaml")
    assert names == ["ship", "car"] and kpt_shape == [3, 3]

    back, stats = yolo_to_coco({"a": out["labels"][1][0]}, IMAGES, names=names, kpt_shape=kpt_shape)
    assert stats["task"] == "pose"
    ann = back["annotations"][0]
    assert ann["keypoints"] == pytest.approx([50, 25, 2, 0, 0, 0, 80, 40, 1])
    assert ann["isbbox"] and ann["bbox"] == pytest.approx([0, 0, 100, 50])
    assert back["categories"][0]["keypoints"] == ["1", "2", "3"]


def test_task_detection_and_matching():
    assert detect_task(["0 .5 .5 .1 .1"]) == "detect"
    assert detect_task(["0 .1 .1 .2 .1 .2 .2 .1 .2"]) == "obb"
    assert detect_task(["0 .1 .1 .2 .1 .2 .2", "0 .5 .5 .1 .1"]) == "segment"
    assert detect_task(["0 .5 .5 .1 .1 .2 .2 2 .3 .3 1"]) == "pose"

    coco, stats = yolo_to_coco({"zzz": "0 .5 .5 .1 .1", "b": "3 .5 .5 .1 .1\nbad line"}, IMAGES)
    assert stats["matched"] == 1 and stats["unmatched"] == ["zzz"]
    assert coco["images"][0]["file_name"] == "sub/b.png"
    assert [c["name"] for c in coco["categories"]] == ["class_3"]


def test_read_zip_layouts():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ds/data.yaml", "names:\n  0: ship\n  1: car\n")
        zf.writestr("ds/labels/train/a.txt", "1 .5 .5 .2 .2\n")
        zf.writestr("ds/labels/val/b.txt", "0 .5 .5 .2 .2\n")
        zf.writestr("ds/classes.txt", "wrong\n")
        zf.writestr("__MACOSX/ds/labels/._a.txt", "junk")
    texts, names, shape = read_zip(io.BytesIO(buf.getvalue()))
    assert sorted(texts) == ["a", "b"] and names == ["ship", "car"] and shape is None


# ------------------------------------------------------------------ API

@pytest.fixture(scope="module")
def yolo_world(world, dataset_directory):
    from PIL import Image
    c = world["client"]
    r = c.post("/api/dataset/", json={"name": "yolo_conv", "categories": ["ship"]})
    assert r.status_code == 200, r.data
    ds = r.get_json()
    folder = os.path.join(dataset_directory, "yolo_conv")
    os.makedirs(folder, exist_ok=True)
    for name in ("p1.jpg", "p2.jpg"):
        Image.new("RGB", (W, H), (10, 80, 120)).save(os.path.join(folder, name))
    assert c.get(f"/api/dataset/{ds['id']}/scan").status_code == 200
    images = {i["file_name"]: i for i in c.get(f"/api/dataset/{ds['id']}/data").get_json()["images"]}
    return {"client": c, "dataset": ds, "images": images}


def _upload(c, ds_id, files, task="auto"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    buf.seek(0)
    return c.post(f"/api/dataset/{ds_id}/yolo", data={"yolo": (buf, "labels.zip"), "task": task},
                  content_type="multipart/form-data")


def test_api_yolo_import_then_export(yolo_world):
    from database import AnnotationModel, CategoryModel, ExportModel, TaskModel
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    p1 = yolo_world["images"]["p1.jpg"]

    r = _upload(c, ds, {"data.yaml": "names: [ship, kayak]\n",
                        "labels/p1.txt": "1 0.5 0.5 0.2 0.4\n0 0.1 0.1 0.3 0.1 0.3 0.3 0.1 0.3\n",
                        "labels/missing.txt": "0 .5 .5 .1 .1\n"})
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body["stats"]["matched"] == 1 and body["stats"]["unmatched"] == 1
    assert body["stats"]["task"] == "segment"  # mixed 5 / 9 values -> polygons + boxes
    task = TaskModel.objects(id=body["id"]).first()
    assert task.completed and task.errors == 0, task.logs

    kayak = CategoryModel.objects(name="kayak").first()
    anns = AnnotationModel.objects(image_id=p1["id"], deleted=False)
    assert anns.count() == 2
    box = anns.filter(category_id=kayak.id).first()
    assert box.isbbox and box.bbox == pytest.approx([80, 30, 40, 40])

    # nothing matches -> a clear error, no task
    r = _upload(c, ds, {"labels/nope.txt": "0 .5 .5 .1 .1\n"})
    assert r.status_code == 400 and "file name" in r.get_json()["message"]
    r = c.post(f"/api/dataset/{ds}/yolo", data={"yolo": (io.BytesIO(b"not a zip"), "x.zip")},
               content_type="multipart/form-data")
    assert r.status_code == 400

    # export the same dataset as YOLO detect, with images
    r = c.get(f"/api/dataset/{ds}/export?format=yolo&yolo_task=detect&with_images=true&with_empty_images=true")
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-created_at").first()
    assert export.path.endswith(".zip") and export.tags[:2] == ["YOLO", "detect"]
    d = c.get(f"/api/export/{export.id}/download")
    assert d.status_code == 200
    assert ".zip" in d.headers["Content-Disposition"]
    with zipfile.ZipFile(io.BytesIO(d.data)) as zf:
        names = set(zf.namelist())
        assert {"data.yaml", "classes.txt", "yolo_conv/train/labels/yolo_conv_p1.txt", "yolo_conv/train/labels/yolo_conv_p2.txt", "yolo_conv/train/images/yolo_conv_p1.jpg"} <= names
        lines = zf.read("yolo_conv/train/labels/yolo_conv_p1.txt").decode().split("\n")
        classes = zf.read("classes.txt").decode().split()
        assert zf.read("yolo_conv/train/labels/yolo_conv_p2.txt") == b""
    kayak_lines = [l for l in lines if l and classes[int(l.split()[0])] == "kayak"]
    assert _values(kayak_lines[0])[1:] == pytest.approx([0.5, 0.5, 0.2, 0.4])

    # COCO export still downloads as .json
    assert c.get(f"/api/dataset/{ds}/export").status_code == 200
    export = ExportModel.objects(dataset_id=ds).order_by("-created_at").first()
    d = c.get(f"/api/export/{export.id}/download")
    assert ".json" in d.headers["Content-Disposition"]


def test_api_category_counts_and_export_order(yolo_world):
    from database import CategoryModel, ExportModel
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    # runs after the import test above: p1 has a kayak box and a ship polygon
    ship = CategoryModel.objects(name="ship").first().id
    kayak = CategoryModel.objects(name="kayak").first().id

    body = c.get(f"/api/dataset/{ds}/category_counts").get_json()
    counts = body["categories"]
    assert body["total_images"] == 2 and sorted(map(sorted, body["image_categories"])) == [sorted([ship, kayak])]
    assert counts[str(kayak)]["annotations"] == 1 and counts[str(kayak)]["boxes"] == 1
    assert counts[str(ship)]["polygons"] == 1 and counts[str(ship)]["images"] == 1

    # the order of the ids is the YOLO class order
    r = c.get(f"/api/dataset/{ds}/export?format=yolo&categories={kayak},{ship}")
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        assert zf.read("classes.txt").decode().split() == ["kayak", "ship"]
    r = c.get(f"/api/dataset/{ds}/export?format=yolo&categories={ship}")
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        assert zf.read("classes.txt").decode().split() == ["ship"]
        assert zf.read("yolo_conv/train/labels/yolo_conv_p1.txt").decode().count("\n") == 1


def test_api_export_list_and_delete(yolo_world):
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    rows = c.get(f"/api/dataset/{ds}/exports").get_json()
    assert rows, "earlier tests made exports"
    yolo_row = next(r for r in rows if r["format"] == "YOLO")
    assert yolo_row["yolo_task"] in ("detect", "obb", "segment", "pose")
    assert "YOLO" not in yolo_row["categories"] and yolo_row["created_at"].endswith("Z")
    assert yolo_row["exists"] and yolo_row["size"] > 0
    coco_row = next(r for r in rows if r["format"] == "COCO")
    assert "COCO" not in coco_row["categories"]

    from database import ExportModel
    path = ExportModel.objects(id=yolo_row["id"]).first().path
    assert c.delete(f"/api/export/{yolo_row['id']}").status_code == 200
    assert not os.path.exists(path)
    assert yolo_row["id"] not in [r["id"] for r in c.get(f"/api/dataset/{ds}/exports").get_json()]


def test_split_helpers():
    from geometry.yolo_format import parse_split, split_images
    assert parse_split("") is None
    assert parse_split("80,10,10") == {"train": 80, "val": 10, "test": 10}
    assert parse_split("70:30") == {"train": 70, "val": 30, "test": 0}
    for bad in ("50,10,10", "0,50,50", "a,b,c", "90,-10,20"):
        with pytest.raises(ValueError):
            parse_split(bad)

    ids = list(range(1, 101))
    a = split_images(ids, {"train": 70, "val": 20, "test": 10}, seed=1)
    assert sorted(a) == ids
    assert [sum(v == k for v in a.values()) for k in ("train", "val", "test")] == [70, 20, 10]
    assert a == split_images(list(reversed(ids)), {"train": 70, "val": 20, "test": 10}, seed=1)
    assert a != split_images(ids, {"train": 70, "val": 20, "test": 10}, seed=2)
    # tiny datasets: every non-zero subset gets an image, train keeps one
    small = split_images([1, 2, 3], {"train": 80, "val": 10, "test": 10})
    assert sorted(small.values()) == ["test", "train", "val"]
    assert list(split_images([5], {"train": 50, "val": 50, "test": 0}).values()) == ["train"]


def test_api_export_with_split(yolo_world):
    import json as _json
    from database import ExportModel
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    assert c.get(f"/api/dataset/{ds}/export?format=yolo&split=50,10,10").status_code == 400

    r = c.get(f"/api/dataset/{ds}/export?format=yolo&split=50,50,0&with_empty_images=true&with_images=true&seed=3"
              f"&folder=My boats/v2")
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        names = zf.namelist()
        yaml_text = zf.read("data.yaml").decode()
    assert sum(n.startswith("My_boats_v2/train/labels/") for n in names) == 1
    assert sum(n.startswith("My_boats_v2/val/labels/") for n in names) == 1
    assert sum(n.startswith("My_boats_v2/val/images/") for n in names) == 1
    assert "train: My_boats_v2/train/images" in yaml_text and "val: My_boats_v2/val/images" in yaml_text and "test:" not in yaml_text
    row = next(x for x in c.get(f"/api/dataset/{ds}/exports").get_json() if x["id"] == export.id)
    assert row["split"] == {"train": 50, "val": 50, "test": 0}
    assert row["split_counts"] == {"train": 1, "val": 1, "test": 0} and row["seed"] == 3
    assert row["folder"] == "My_boats_v2"

    # 2 images split 80/10/10: test gets none, so data.yaml has no test line
    c.get(f"/api/dataset/{ds}/export?format=yolo&split=80,10,10&with_empty_images=true")
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        text = zf.read("data.yaml").decode()
    assert "val: yolo_conv/val/images" in text and "test:" not in text
    assert {n.split("/")[0] for n in names} == {"data.yaml", "classes.txt", "My_boats_v2"}

    r = c.get(f"/api/dataset/{ds}/export?format=coco&split=50,50,0&with_empty_images=true")
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    assert export.path.endswith(".zip")
    with zipfile.ZipFile(export.path) as zf:
        assert sorted(zf.namelist()) == ["train.json", "val.json"]
        parts = [_json.loads(zf.read(n)) for n in ("train.json", "val.json")]
    assert sum(len(p["images"]) for p in parts) == 2
    for p in parts:
        ids = {i["id"] for i in p["images"]}
        assert all(a["image_id"] in ids for a in p["annotations"])
    d = c.get(f"/api/export/{export.id}/download")
    assert ".zip" in d.headers["Content-Disposition"]


def test_dataset_name_prefix(yolo_world):
    from geometry.yolo_format import safe_prefix
    from database import ExportModel
    assert safe_prefix("ships") == "ships_"
    assert safe_prefix("My ships/2024") == "My_ships_2024_"
    assert safe_prefix("") == ""
    # a label named with a prefix still finds its image
    coco, stats = yolo_to_coco({"ships_a": "0 .5 .5 .1 .1"}, IMAGES, prefixes=["ships_"])
    assert stats["matched"] == 1

    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    r = c.get(f"/api/dataset/{ds}/export?format=yolo&with_images=true&with_empty_images=true")
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        names = set(zf.namelist())
        data = {n: zf.read(n) for n in names}
    assert {"yolo_conv/train/labels/yolo_conv_p1.txt", "yolo_conv/train/images/yolo_conv_p1.jpg", "yolo_conv/train/images/yolo_conv_p2.jpg"} <= names
    row = next(x for x in c.get(f"/api/dataset/{ds}/exports").get_json() if x["id"] == export.id)
    assert row["prefix_dataset"] is True

    # importing that export back matches the original images
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n, b in data.items():
            if "/labels/" in n or n == "data.yaml":
                zf.writestr(n, b)
    buf.seek(0)
    r = c.post(f"/api/dataset/{ds}/yolo", data={"yolo": (buf, "x.zip")}, content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    assert r.get_json()["stats"]["matched"] == 2 and r.get_json()["stats"]["unmatched"] == 0


def test_image_classes_and_semantic_mask():
    from geometry.yolo_format import image_classes, semantic_mask
    coco = _coco([
        {"id": 1, "image_id": 1, "category_id": 10, "segmentation": [[0, 0, 100, 0, 100, 100, 0, 100]]},
        {"id": 2, "image_id": 1, "category_id": 10, "segmentation": [[10, 10, 20, 10, 20, 20]]},
        {"id": 3, "image_id": 2, "category_id": 10, "segmentation": [[0, 0, 5, 0, 5, 5]]},
        {"id": 4, "image_id": 2, "category_id": 20, "segmentation": [[0, 0, 5, 0, 5, 5]]},
    ])
    single, mixed, empty = image_classes(coco)
    assert single == {1: 0} and [i["id"] for i in mixed] == [2] and empty == []

    # big ship box with a small car on top: the car stays visible
    anns = [{"category_id": 10, "segmentation": [[0, 0, 100, 0, 100, 80, 0, 80]], "area": 8000},
            {"category_id": 20, "segmentation": [[40, 30, 60, 30, 60, 50, 40, 50]], "area": 400}]
    mask = semantic_mask(IMAGES[0], anns, {10: 0, 20: 1})
    assert mask.shape == (H, W)
    assert mask[10, 10] == 1 and mask[40, 50] == 2 and mask[95, 150] == 0


def test_api_export_classify_and_semantic(yolo_world):
    from database import AnnotationModel, CategoryModel, ExportModel
    import numpy as np
    import cv2
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    images = yolo_world["images"]
    ship = CategoryModel.objects(name="ship").first().id
    # p2 gets one ship box, so it has a single class; p1 has ship + kayak (mixed)
    c.post("/api/annotation/", json={"image_id": images["p2.jpg"]["id"], "category_id": ship,
                                     "segmentation": [[10, 10, 60, 10, 60, 40, 10, 40]]})
    AnnotationModel.objects(image_id=images["p2.jpg"]["id"]).update(set__area=1500, set__bbox=[10, 10, 50, 30])

    def latest():
        return ExportModel.objects(dataset_id=ds).order_by("-id").first()

    r = c.get(f"/api/dataset/{ds}/export?format=yolo&yolo_task=classify&folder=cls")
    assert r.status_code == 200, r.data
    with zipfile.ZipFile(latest().path) as zf:
        names = zf.namelist()
    assert "cls/ship/yolo_conv_p2.jpg" in names           # no split: class folders at the top
    assert not any("yolo_conv_p1" in n for n in names)     # mixed image skipped
    assert "cls/kayak/" in names and "classes.txt" in names and "data.yaml" not in names
    with zipfile.ZipFile(latest().path) as zf:
        assert zf.read("classes.txt").decode().split() == sorted(zf.read("classes.txt").decode().split())

    c.get(f"/api/dataset/{ds}/export?format=yolo&yolo_task=classify&folder=cls&split=50,50,0")
    with zipfile.ZipFile(latest().path) as zf:
        names = zf.namelist()
    assert "cls/train/ship/yolo_conv_p2.jpg" in names
    assert "cls/train/kayak/" in names

    r = c.get(f"/api/dataset/{ds}/export?format=yolo&yolo_task=semantic&folder=sem&with_images=true"
              "&with_empty_images=true")
    assert r.status_code == 200, r.data
    with zipfile.ZipFile(latest().path) as zf:
        names = set(zf.namelist())
        yaml_text = zf.read("data.yaml").decode()
        mask = cv2.imdecode(np.frombuffer(zf.read("sem/train/masks/yolo_conv_p2.png"), np.uint8), cv2.IMREAD_UNCHANGED)
        classes = zf.read("classes.txt").decode().split()
    assert {"sem/train/images/yolo_conv_p2.jpg", "sem/train/masks/yolo_conv_p1.png"} <= names
    assert "masks_dir: masks" in yaml_text and "0: 'background'" in yaml_text
    assert classes[0] == "background"
    assert mask.shape == (H, W) and mask.dtype == np.uint8
    assert mask[20, 30] == classes.index("ship") and mask[90, 190] == 0


def test_whole_image_class(yolo_world):
    from database import CategoryModel, ExportModel, ImageModel
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    p1, p2 = yolo_world["images"]["p1.jpg"]["id"], yolo_world["images"]["p2.jpg"]["id"]
    ship = CategoryModel.objects(name="ship").first().id
    kayak = CategoryModel.objects(name="kayak").first().id

    assert c.post(f"/api/image/{p1}/class", json={"category_id": 999999}).status_code == 400
    # p1 has ship + kayak annotations (mixed): the whole-image class decides
    assert c.post(f"/api/image/{p1}/class", json={"category_id": kayak}).get_json()["image_class"] == kayak
    assert ImageModel.objects(id=p1).first().image_class == kayak
    data = c.get(f"/api/dataset/{ds}/data?image_class={kayak}").get_json()["images"]
    assert [i["id"] for i in data] == [p1] and data[0]["image_class"] == kayak

    counts = c.get(f"/api/dataset/{ds}/category_counts").get_json()
    assert counts["categories"][str(kayak)]["classified"] == 1 and counts["image_classes"] == [kayak]
    assert all(len(x) for x in counts["unclassified_image_categories"])

    c.get(f"/api/dataset/{ds}/export?format=yolo&yolo_task=classify&folder=wc")
    with zipfile.ZipFile(ExportModel.objects(dataset_id=ds).order_by("-id").first().path) as zf:
        names = zf.namelist()
    assert "wc/kayak/yolo_conv_p1.jpg" in names and "wc/ship/yolo_conv_p2.jpg" in names

    assert c.post(f"/api/image/{p1}/class", json={"category_id": None}).status_code == 200
    assert ImageModel.objects(id=p1).first().image_class is None
    assert c.get(f"/api/dataset/{ds}/data?image_class=none").get_json()["total"] == 2


def test_api_export_with_augmentation(yolo_world):
    """Split first, then augmented copies of the training images (boxes follow
    the picture); with scope "all" every part gets them, each picture's copies
    staying in its part."""
    import json as _json
    import cv2
    import numpy as np
    from database import AnnotationModel, ExportModel
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    cat = c.get("/api/category/").get_json()
    ship = next(x["id"] for x in cat if x["name"] == "ship")
    AnnotationModel.objects(dataset_id=ds).delete()  # (earlier tests share this dataset)
    # a white box on each (dark) picture, annotated exactly
    import os
    for name, img in yolo_world["images"].items():
        pic = np.full((H, W, 3), 40, np.uint8)
        pic[20:60, 30:90] = 255
        from database import ImageModel
        cv2.imwrite(ImageModel.objects(id=img["id"]).first().path, pic)
        r = c.post("/api/annotation/", json={"image_id": img["id"], "category_id": ship,
                                             "segmentation": [[30, 20, 90, 20, 90, 60, 30, 60]]})
        assert r.status_code == 200, r.data
    AnnotationModel.objects(dataset_id=ds).update(set__isbbox=True)

    aug = {"copies": 3, "ops": {"hflip": True, "vflip": True, "rot90": True, "rotate": 10, "color": True}}
    r = c.get(f"/api/dataset/{ds}/export", query_string={"format": "yolo", "yolo_task": "detect", "split": "50,50,0",
                                                          "seed": 5, "augment": _json.dumps(aug)})
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    assert export.augment["images"] == 3 and export.augment["parts"] == {"train": 3}
    assert export.split_counts == {"train": 1, "val": 1, "test": 0}  # the originals
    row = next(x for x in c.get(f"/api/dataset/{ds}/exports").get_json() if x["id"] == export.id)
    assert row["augment"]["copies"] == 3 and "ship" in row["categories"] and "augmented" not in row["categories"]
    with zipfile.ZipFile(export.path) as zf:
        names = zf.namelist()
        train_imgs = sorted(n for n in names if "/train/images/" in n)
        val_imgs = sorted(n for n in names if "/val/images/" in n)
        assert len(train_imgs) == 4 and len(val_imgs) == 1  # validation stays original
        assert not any("_aug" in n for n in val_imgs)
        for n in train_imgs + val_imgs:
            pic = cv2.imdecode(np.frombuffer(zf.read(n), np.uint8), cv2.IMREAD_GRAYSCALE)
            h, w = pic.shape
            label = zf.read(n.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt").decode().split()
            cls, cx, cy, bw, bh = int(label[0]), *map(float, label[1:5])
            ys, xs = np.where(pic > (int(pic.max()) + int(pic.min())) / 2)  # (colour changes move both)
            # the label box is where the white box is (within a couple of pixels)
            assert abs(xs.min() - (cx - bw / 2) * w) < 3 and abs(xs.max() + 1 - (cx + bw / 2) * w) < 3, n
            assert abs(ys.min() - (cy - bh / 2) * h) < 3 and abs(ys.max() + 1 - (cy + bh / 2) * h) < 3, n

    # COCO: a zip with the pictures and one json per part
    r = c.get(f"/api/dataset/{ds}/export", query_string={"format": "coco", "split": "50,50,0", "seed": 5,
                                                          "augment": _json.dumps({"copies": 2, "ops": {"hflip": True}})})
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    with zipfile.ZipFile(export.path) as zf:
        train = _json.loads(zf.read("train.json"))
        val = _json.loads(zf.read("val.json"))
        assert len(train["images"]) == 3 and len(val["images"]) == 1
        for img in train["images"] + val["images"]:
            assert f"images/{img['file_name']}" in zf.namelist() and "path" not in img
        assert len(train["annotations"]) == 3

    # every part, each picture's versions in its own part
    r = c.get(f"/api/dataset/{ds}/export", query_string={
        "format": "yolo", "split": "50,50,0", "seed": 5, "with_images": "true",
        "augment": _json.dumps({"copies": 2, "ops": {"hflip": True}, "scope": "all"})})
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    assert export.augment["parts"] == {"train": 2, "val": 2}
    with zipfile.ZipFile(export.path) as zf:
        stem = lambda n: n.rsplit("/", 1)[1].split("_aug")[0].rsplit(".", 1)[0]
        parts = {p: {stem(n) for n in zf.namelist() if f"/{p}/images/" in n} for p in ("train", "val")}
        assert len(parts["train"]) == 1 and len(parts["val"]) == 1 and parts["train"] != parts["val"]

    # nothing chosen: no augmentation
    c.get(f"/api/dataset/{ds}/export", query_string={"format": "coco", "augment": _json.dumps({"copies": 2, "ops": {}})})
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    assert export.path.endswith(".json") and not getattr(export, "augment", None)
    assert c.get(f"/api/dataset/{ds}/export", query_string={"augment": "{bad"}).status_code == 400


def test_failed_export_is_marked_failed(yolo_world, monkeypatch):
    """An export that breaks while writing says so (the bar must not look done)."""
    from database import ExportModel, TaskModel
    from workers.tasks import data
    c, ds = yolo_world["client"], yolo_world["dataset"]["id"]
    before = ExportModel.objects(dataset_id=ds).count()

    def broken(*args, **kwargs):
        raise OSError("No space left on device")
    monkeypatch.setattr(data, "_write_export", broken)
    c.get(f"/api/dataset/{ds}/export?format=coco&with_empty_images=true")
    task = TaskModel.objects(group="Annotation Export").order_by("-id").first()
    assert task.failed and task.status == "FAILURE"
    assert any("No space left" in (log or "") for log in task.logs)
    assert ExportModel.objects(dataset_id=ds).count() == before
