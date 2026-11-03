"""Pre-annotation with your own YOLO models.

The conversion is tested with fake ultralytics results (no PyTorch needed).
Set YOLO_TEST_WEIGHTS to a folder with yolo11n*.pt to also run real models.
"""
import os
import shutil

import numpy as np
import pytest

from webserver.util.yolo import result_to_predictions, YoloService

pytestmark = pytest.mark.order(-1)


class T:
    """Minimal stand-in for a torch tensor."""

    def __init__(self, a):
        self.a = np.asarray(a, dtype=float)

    def cpu(self):
        return self

    def numpy(self):
        return self.a

    @property
    def shape(self):
        return self.a.shape


class Boxes:
    def __init__(self, xyxy, cls, conf):
        self.xyxy, self.cls, self.conf = T(xyxy), T(cls), T(conf)

    def __len__(self):
        return len(self.xyxy.a)


class Result:
    def __init__(self, boxes=None, masks=None, keypoints=None, obb=None):
        self.boxes, self.masks, self.keypoints, self.obb = boxes, masks, keypoints, obb


NAMES = {0: "ship", 1: "person"}


def test_detect_to_bbox():
    r = Result(boxes=Boxes([[10, 20, 50, 80]], [0], [0.9]))
    [p] = result_to_predictions(r, NAMES)
    assert p["class_name"] == "ship" and p["type"] == "detect"
    assert p["isbbox"] is True
    assert p["segmentation"] == [[10, 20, 50, 20, 50, 80, 10, 80]]
    assert p["bbox"] == [10, 20, 40, 60] and p["area"] == 2400


def test_obb_to_rotated_box():
    class Obb:
        xyxyxyxy = T([[[0, 0], [40, 0], [40, 20], [0, 20]]])
        cls, conf = T([0]), T([0.8])

        def __len__(self):
            return 1

    [p] = result_to_predictions(Result(obb=Obb()), NAMES)
    assert p["type"] == "obb" and p["isrbbox"] is True
    assert p["segmentation"] == [[0, 0, 40, 0, 40, 20, 0, 20]]
    cx, cy, w, h, angle = p["rbbox"]
    assert (cx, cy, w, h) == (20, 10, 40, 20) and abs(angle) < 1e-6


def test_segment_to_polygon():
    class Masks:
        xy = [np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)]

    r = Result(boxes=Boxes([[0, 0, 10, 10]], [0], [0.7]), masks=Masks())
    [p] = result_to_predictions(r, NAMES)
    assert p["type"] == "segment" and p["isbbox"] is False
    assert p["segmentation"] == [[0, 0, 10, 0, 10, 10, 0, 10]] and p["area"] == 100


def test_pose_to_box_and_keypoints():
    class Kp:
        data = T([[[5, 6, 0.9], [7, 8, 0.1], [9, 10, 0.95]]])

    r = Result(boxes=Boxes([[0, 0, 20, 20]], [1], [0.9]), keypoints=Kp())
    [p] = result_to_predictions(r, NAMES)
    assert p["type"] == "pose" and p["isbbox"] is True
    # low-confidence keypoint is stored as "not labelled"
    assert p["keypoints"] == [5, 6, 2, 0, 0, 0, 9, 10, 2]
    assert p["num_keypoints"] == 3


def test_model_paths_stay_inside_folder(tmp_path):
    (tmp_path / "a.pt").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.pt").write_bytes(b"x")
    (tmp_path / "sam.pth").write_bytes(b"x")
    service = YoloService(str(tmp_path))
    assert service.model_names() == ["a.pt", os.path.join("sub", "b.pt")]
    assert service.path_for("sub/b.pt").endswith("b.pt")
    for bad in ["../a.pt", "/etc/passwd", "sam.pth", "missing.pt", ""]:
        with pytest.raises(ValueError):
            service.path_for(bad)


def test_apply_predictions_creates_annotations(world):
    from database import AnnotationModel, CategoryModel, DatasetModel, ImageModel
    from webserver.util.preannotate import CategoryResolver, apply_predictions

    dataset = DatasetModel.objects(id=world["dataset"]["id"]).first()
    image = ImageModel.objects(id=world["images"][1]["id"]).first()
    before = AnnotationModel.objects(image_id=image.id, deleted=False).count()

    predictions = result_to_predictions(
        Result(boxes=Boxes([[1, 1, 30, 30], [2, 2, 9, 9]], [0, 1], [0.9, 0.8])), NAMES)

    resolver = CategoryResolver(dataset, create_missing=False)
    assert apply_predictions(image, predictions, resolver) == 1   # "person" skipped
    assert resolver.skipped == {"person"}

    resolver = CategoryResolver(dataset, create_missing=True)
    assert apply_predictions(image, predictions, resolver, username="smoke") == 2
    person = CategoryModel.objects(name="person").first()
    assert person.id in DatasetModel.objects(id=dataset.id).first().categories

    after = AnnotationModel.objects(image_id=image.id, deleted=False)
    assert after.count() == before + 3
    assert after.order_by('-id').first().creator == "smoke"
    image.reload()
    assert image.annotated and person.id in image.category_ids


def test_pose_category_gets_keypoint_labels(world):
    from database import CategoryModel, DatasetModel, ImageModel
    from webserver.util.preannotate import CategoryResolver, apply_predictions

    class Kp:
        data = T([[[5, 6, 0.9]] * 17])

    dataset = DatasetModel.objects(id=world["dataset"]["id"]).first()
    image = ImageModel.objects(id=world["images"][1]["id"]).first()
    predictions = result_to_predictions(
        Result(boxes=Boxes([[0, 0, 20, 20]], [0], [0.9]), keypoints=Kp()), {0: "walker"})
    apply_predictions(image, predictions, CategoryResolver(dataset))
    walker = CategoryModel.objects(name="walker").first()
    assert len(walker.keypoint_labels) == 17 and walker.keypoint_edges

    # a category with a different number of keypoints keeps its labels
    walker.update(keypoint_labels=["a", "b"])
    resolver = CategoryResolver(dataset)
    apply_predictions(image, predictions, resolver)
    assert resolver.keypoints_mismatch == {"walker"}


def test_api_without_models(world):
    c = world["client"]
    r = c.get("/api/model/yolo")
    assert r.status_code == 200
    r = c.post(f"/api/model/yolo/image/{world['images'][0]['id']}", json={"model": "../x.pt"})
    assert r.status_code == 400


WEIGHTS = os.environ.get("YOLO_TEST_WEIGHTS")


@pytest.mark.skipif(not WEIGHTS, reason="set YOLO_TEST_WEIGHTS to run real models")
def test_real_models_end_to_end(world, tmp_path, monkeypatch):
    pytest.importorskip("ultralytics")
    import ultralytics
    from PIL import Image as PILImage
    from database import AnnotationModel, ImageModel, TaskModel
    from webserver.util.yolo import yolo

    for f in os.listdir(WEIGHTS):
        if f.endswith(".pt"):
            shutil.copy(os.path.join(WEIGHTS, f), tmp_path / f)
    monkeypatch.setattr(yolo, "directory", str(tmp_path))

    c = world["client"]
    models = {m["name"]: m for m in c.get("/api/model/yolo").get_json()["models"]}
    assert models["yolo11n-pose.pt"]["task"] == "pose"

    # put a real photo into the dataset
    bus = os.path.join(os.path.dirname(ultralytics.__file__), "assets", "bus.jpg")
    image = ImageModel.objects(id=world["images"][0]["id"]).first()
    PILImage.open(bus).save(image.path)
    w, h = PILImage.open(bus).size
    image.update(width=w, height=h)

    for name, kind in [("yolo11n.pt", "isbbox"), ("yolo11n-seg.pt", None),
                       ("yolo11n-pose.pt", "keypoints")]:
        r = c.post(f"/api/model/yolo/image/{image.id}", json={"model": name, "conf": 0.3})
        assert r.status_code == 200, r.data
        assert r.get_json()["created"] > 0, name

    anns = AnnotationModel.objects(image_id=image.id, deleted=False)
    assert any(a.isbbox for a in anns)
    assert any(len(a.keypoints) == 51 for a in anns)
    assert any(not a.isbbox and len(a.segmentation[0]) > 8 for a in anns)

    # whole dataset, synchronously
    from webserver.util import preannotate
    from database import DatasetModel, UserModel
    task = preannotate.annotate_dataset(
        DatasetModel.objects(id=world["dataset"]["id"]).first(), "yolo11n.pt",
        skip_annotated=False, user=UserModel.objects(username="smoke").first(),
        background=False)
    t = TaskModel.objects(id=task["id"]).first()
    assert t.completed and t.errors == 0, t.logs


def _make_admin(username="smoke"):
    from database import UserModel
    UserModel.objects(username=username).update(set__is_admin=True)


def test_upload_rejects_bad_files(world):
    import io
    _make_admin()
    c = world["client"]
    r = c.post("/api/model/yolo/upload", data={"file": (io.BytesIO(b"not a model"), "evil.txt")},
               content_type="multipart/form-data")
    assert r.status_code == 400
    r = c.post("/api/model/yolo/upload", data={"file": (io.BytesIO(b"not a model"), "fake.pt")},
               content_type="multipart/form-data")
    assert r.status_code == 400
    from webserver.util.yolo import yolo
    assert "fake.pt" not in yolo.model_names()


def test_upload_needs_admin(world):
    import io
    from webserver import app
    from webserver.util.passwords import hash_password
    from database import UserModel
    if UserModel.objects(username="plain").first() is None:
        UserModel(username="plain", password=hash_password("pw"), name="P", is_admin=False).save()
    m = app.test_client()
    assert m.post("/api/user/login", json={"username": "plain", "password": "pw"}).status_code == 200
    r = m.post("/api/model/yolo/upload", data={"file": (io.BytesIO(b"x"), "a.pt")},
               content_type="multipart/form-data")
    assert r.status_code == 403
    assert m.delete("/api/model/yolo/model/a.pt").status_code == 403


@pytest.mark.skipif(not WEIGHTS, reason="set YOLO_TEST_WEIGHTS to run real models")
def test_upload_and_delete_real_model(world, tmp_path, monkeypatch):
    pytest.importorskip("ultralytics")
    from webserver.util.yolo import yolo
    monkeypatch.setattr(yolo, "directory", str(tmp_path))
    _make_admin()
    c = world["client"]

    def upload(overwrite="false"):
        with open(os.path.join(WEIGHTS, "yolo11n-obb.pt"), "rb") as f:
            return c.post("/api/model/yolo/upload",
                          data={"file": (f, "my obb.pt"), "overwrite": overwrite},
                          content_type="multipart/form-data")

    r = upload()
    assert r.status_code == 200, r.data
    assert r.get_json()["model"] == {**r.get_json()["model"], "name": "my_obb.pt", "task": "obb"}
    assert upload().status_code == 409
    assert upload("true").status_code == 200
    assert c.delete("/api/model/yolo/model/my_obb.pt").status_code == 200
    assert yolo.model_names() == []
