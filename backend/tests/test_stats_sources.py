"""Statistics: annotations by hand per member, per model, and imported."""
import io
import json
import os


def test_stats_split_by_source(world, dataset_directory):
    from PIL import Image
    from database import AnnotationModel, CategoryModel, ImageModel
    from webserver.util import preannotate
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "stats_src", "categories": ["car"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "stats_src")
    os.makedirs(folder, exist_ok=True)
    for i in range(2):
        Image.new("RGB", (100, 80)).save(os.path.join(folder, f"s{i}.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    images = sorted(ImageModel.objects(dataset_id=ds), key=lambda i: i.file_name)
    car = CategoryModel.objects(name="car").first().id

    # by hand
    c.post("/api/annotation/", json={"image_id": images[0].id, "category_id": car,
                                     "segmentation": [[1, 1, 20, 1, 20, 20, 1, 20]]})
    # a model run on one image
    class Resolver:
        skipped, keypoints_mismatch = set(), set()

        def get(self, name):
            return CategoryModel.objects(id=car).first()
    preds = [{"class_name": "car", "segmentation": [[5, 5, 30, 5, 30, 30, 5, 30]], "bbox": [5, 5, 25, 25],
              "area": 625, "isbbox": True}] * 3
    preannotate.apply_predictions(images[1], preds, Resolver(), username="smoke", model_name="yolo11n.pt")
    # an import
    coco = {"images": [{"id": 1, "file_name": "s0.jpg"}], "categories": [{"id": 1, "name": "car"}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [40, 40, 10, 10]},
                            {"id": 2, "image_id": 1, "category_id": 1, "bbox": [60, 40, 10, 10]}]}
    c.post(f"/api/dataset/{ds}/coco", data={"coco": (io.BytesIO(json.dumps(coco).encode()), "c.json")},
           content_type="multipart/form-data")

    stats = c.get(f"/api/dataset/{ds}/stats").get_json()
    assert stats["users"]["smoke"] == {"annotations": 1, "images": 1}
    model = next(s for s in stats["sources"] if s["kind"] == "model")
    assert model["name"] == "yolo11n.pt" and model["annotations"] == 3 and model["images"] == 1
    assert model["by"] == ["smoke"]
    imported = next(s for s in stats["sources"] if s["kind"] == "import")
    assert imported["annotations"] == 2 and imported["images"] == 1
    assert AnnotationModel.objects(dataset_id=ds, source="model").count() == 3

    # image filters: has annotations / has model annotations, and the AI tag
    def shown(status):
        data = c.get(f"/api/dataset/{ds}/data", query_string={"status": status, "limit": 50}).get_json()
        return {i["file_name"]: i["ai"] for i in data["images"]}
    assert shown("ai") == {"s1.jpg": True}
    assert shown("annotated") == {"s0.jpg": False, "s1.jpg": True}
    AnnotationModel.objects(dataset_id=ds, source="model").update(set__deleted=True)
    assert shown("ai") == {}


def test_copy_keeps_ai_but_not_the_run(world, dataset_directory, monkeypatch):
    """Copying (C) a model's annotations: still AI, credited to whoever copied,
    and taking the model run back leaves the copies."""
    from PIL import Image
    from database import ActivityModel, AnnotationModel, CategoryModel, ImageModel, TaskModel
    from webserver.util import preannotate
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "copy_ai", "categories": ["bus"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "copy_ai")
    os.makedirs(folder, exist_ok=True)
    for i in range(2):
        Image.new("RGB", (100, 80)).save(os.path.join(folder, f"c{i}.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    a, b = sorted(ImageModel.objects(dataset_id=ds), key=lambda i: i.file_name)
    bus = CategoryModel.objects(name="bus").first()

    task = TaskModel(name="run", group="t", dataset_id=ds); task.save()
    ActivityModel(action="auto_annotate", user="smoke", dataset_id=ds, task_id=task.id,
                  detail={"model": "bus.pt"}).save()

    class Resolver:
        skipped, keypoints_mismatch = set(), set()

        def get(self, name):
            return bus
    preds = [{"class_name": "bus", "segmentation": [[5, 5, 30, 5, 30, 30, 5, 30]], "bbox": [5, 5, 25, 25],
              "area": 625, "isbbox": True}] * 2
    preannotate.apply_predictions(a, preds, Resolver(), username="smoke", model_name="bus.pt", task_id=task.id)
    # a run from before annotations were marked: only the task id is known
    AnnotationModel.objects(image_id=a.id).update(unset__source=1, unset__model=1, unset__creator=1)

    r = c.post(f"/api/image/copy/{a.id}/{b.id}/annotations", json={"category_ids": []}).get_json()
    copies = list(AnnotationModel.objects(id__in=r["ids"]))
    assert len(copies) == 2
    for copy in copies:
        assert copy.source == "model" and copy.model == "bus.pt" and copy.creator == "smoke"
        assert getattr(copy, "import_task", None) is None and copy.copied_from

    data = c.get(f"/api/dataset/{ds}/data", query_string={"status": "ai"}).get_json()
    assert {i["file_name"] for i in data["images"]} == {"c0.jpg", "c1.jpg"}

    from database import UserModel
    monkeypatch.setattr(UserModel, "can_page", lambda self, page: True)
    entry = ActivityModel.objects(task_id=task.id).first()
    assert c.post(f"/api/activity/{entry.id}/undo").status_code == 200
    assert AnnotationModel.objects(image_id=a.id, deleted=False).count() == 0
    assert AnnotationModel.objects(image_id=b.id, deleted=False).count() == 2
