"""Pre-annotation inside boxes people drew: a crop per box, the result moved
back into the image, one prediction kept per box, the box left as it was."""
import os

import pytest
from PIL import Image

from webserver.util import preannotate


def _pred(x, y, w, h, score=0.9, kp=True):
    p = {"class_id": 0, "class_name": "person", "score": score, "type": "pose" if kp else "detect",
         "segmentation": [[x, y, x + w, y, x + w, y + h, x, y + h]], "isbbox": True, "bbox": [x, y, w, h],
         "area": w * h}
    if kp:
        p.update(keypoints=[x + 1, y + 2, 2, 0, 0, 0, x + w - 1, y + h - 1, 2], num_keypoints=3)
    return p


def test_shift_moves_everything_but_unlabelled_points():
    p = preannotate.shift_prediction(dict(_pred(10, 20, 30, 40), rbbox=[25, 40, 30, 40, 0]), 100, 50)
    assert p["bbox"] == [110, 70, 30, 40] and p["segmentation"][0][:4] == [110, 70, 140, 70]
    assert p["keypoints"] == [111, 72, 2, 0, 0, 0, 139, 109, 2]
    assert p["rbbox"] == [125, 90, 30, 40, 0] and p["area"] == 1200


def test_each_box_gets_its_best_fitting_prediction(tmp_path, monkeypatch):
    path = str(tmp_path / "people.png")
    Image.new("RGB", (400, 300)).save(path)
    crops = []

    def fake_predict(name, crop_path, conf=0.25):
        with Image.open(crop_path) as im:
            crops.append(im.size)
            w, h = im.size
        # the boxed person (fits the crop's middle) and a neighbour at the edge, more confident
        return [_pred(w * 0.13, h * 0.13, w * 0.74, h * 0.74, score=0.6), _pred(0, 0, 10, 10, score=0.99)]
    monkeypatch.setattr(preannotate.yolo, "predict", fake_predict)
    boxes = [[100, 50, 100, 200], [390, 290, 15, 15]]  # the second runs off the corner: its crop is clipped
    out = preannotate.predict_in_boxes("m.task", path, boxes)
    # 15 % around: 100 -> 85..215 (130 x 260); the clipped one stops at the image's edge
    assert crops[0] == (130, 260) and crops[1] == (400 - 387, 300 - 287)
    assert len(out) == 2 and out[0]["score"] == 0.6
    x, y, w, h = out[0]["bbox"]
    assert abs(x - (85 + 130 * 0.13)) < 0.01 and abs(y - (20 + 260 * 0.13)) < 0.01


@pytest.fixture
def boxed(world, monkeypatch):
    """A person box (with keypoints) people drew on the first image."""
    from config import Config
    from database import AnnotationModel, CategoryModel, DatasetModel, ImageModel
    ds = world["dataset"]["id"]
    category = CategoryModel(name="BoxTest_Pose", keypoint_labels=["a", "b", "c"])
    category.save()
    DatasetModel.objects(id=ds).update(push__categories=category.id)
    image = ImageModel.objects(dataset_id=ds, deleted=False).order_by("id").first()
    box = AnnotationModel(image_id=image.id, dataset_id=ds, category_id=category.id, bbox=[40, 30, 100, 120],
                          area=12000, segmentation=[[40, 30, 140, 30, 140, 150, 40, 150]], isbbox=True,
                          keypoints=[50, 40, 2, 0, 0, 0, 0, 0, 0])
    box.save()
    os.makedirs(Config.MODELS_DIRECTORY, exist_ok=True)
    model = os.path.join(Config.MODELS_DIRECTORY, "box-test.task")
    open(model, "wb").write(b"x")
    monkeypatch.setattr(type(preannotate.yolo), "installed", property(lambda self: True))
    calls = []

    def fake_predict(name, crop_path, conf=0.25):
        calls.append(crop_path)
        return [_pred(20, 25, 90, 120)]
    monkeypatch.setattr(preannotate.yolo, "predict", fake_predict)
    yield {"dataset": ds, "category": category, "image": image, "box": box, "calls": calls}
    AnnotationModel.objects(category_id=category.id).delete()
    DatasetModel.objects(id=ds).update(pull__categories=category.id)
    category.delete()
    os.remove(model)


def test_api_runs_inside_the_boxes(world, boxed):
    from database import AnnotationModel
    c = world["client"]
    cat, image = boxed["category"], boxed["image"]
    r = c.post(f"/api/model/yolo/image/{image.id}", json={
        "model": "box-test.task", "class_map": {"person": cat.id},
        "in_boxes": {"category_id": cat.id, "source": "human"}})
    assert r.status_code == 200, r.data
    assert r.get_json()["boxes"] == 1 and r.get_json()["created"] == 1 and len(boxed["calls"]) == 1
    made = AnnotationModel.objects(image_id=image.id, category_id=cat.id, source="model").first()
    # crop from (40 - 15, 30 - 18) = (25, 12): the prediction moved by that
    assert made.bbox == [45, 37, 90, 120] and made.keypoints[:3] == [46, 39, 2]
    # people's box untouched
    box = AnnotationModel.objects(id=boxed["box"].id).first()
    assert box.keypoints == [50, 40, 2, 0, 0, 0, 0, 0, 0] and getattr(box, "source", None) is None

    # again: only people's boxes count, the model's own new one is not a box to run in
    r = c.post(f"/api/model/yolo/image/{image.id}", json={
        "model": "box-test.task", "class_map": {"person": cat.id},
        "in_boxes": {"category_id": cat.id, "source": "human"}})
    assert r.get_json()["boxes"] == 1


def test_api_checks_the_box_category(world, boxed):
    from database import CategoryModel
    c = world["client"]
    other = CategoryModel(name="BoxTest_Elsewhere")
    other.save()
    try:
        for bad in ({"category_id": other.id}, {"category_id": "x"}, {"category_id": boxed["category"].id, "source": "z"}):
            r = c.post(f"/api/model/yolo/image/{boxed['image'].id}", json={"model": "box-test.task", "in_boxes": bad})
            assert r.status_code == 400, bad
    finally:
        other.delete()


def test_a_dataset_run_takes_only_images_with_boxes(world, boxed):
    from database import AnnotationModel, DatasetModel, TaskModel
    dataset = DatasetModel.objects(id=boxed["dataset"]).first()
    cat = boxed["category"]
    started = preannotate.annotate_dataset(dataset, "box-test.task", class_map={"person": cat.id},
                                           in_boxes={"category_id": cat.id, "source": "human"},
                                           skip_annotated=True, background=False)
    # one image has a box (and is annotated: skip_annotated does not apply here)
    assert len(boxed["calls"]) == 1
    assert AnnotationModel.objects(category_id=cat.id, source="model").count() == 1
    task = TaskModel.objects(id=started["id"]).first()
    assert any("boxes of BoxTest_Pose" in str(line) for line in (task.logs or []))
