"""Pre-annotation: model classes can be sent to a category of another name
(e.g. MediaPipe's "person" into "MediaPipe_Pose"), or left out."""
import os

import pytest

from webserver.util import mediapipe_models as mpm


def _pose_prediction():
    keypoints = []
    for i in range(33):
        keypoints += [10.0 + i, 20.0 + i, 2]
    return {"class_id": 0, "class_name": "person", "score": 0.9, "type": "pose",
            "segmentation": [[5, 5, 80, 5, 80, 90, 5, 90]], "isbbox": True, "bbox": [5, 5, 75, 85],
            "area": 6375, "keypoints": keypoints, "num_keypoints": 33,
            "keypoint_labels": mpm.POSE_KEYPOINTS, "skeleton": mpm.POSE_SKELETON}


@pytest.fixture
def pose_model(world, monkeypatch):
    from config import Config
    from webserver.util.yolo import yolo
    os.makedirs(Config.MODELS_DIRECTORY, exist_ok=True)
    path = os.path.join(Config.MODELS_DIRECTORY, "map-test.task")
    open(path, "wb").write(b"x")
    monkeypatch.setattr(type(yolo), "installed", property(lambda self: True))
    monkeypatch.setattr(yolo, "predict", lambda name, image_path, conf=0.25: [_pose_prediction()])
    yield "map-test.task"
    os.remove(path)


def _image(world):
    from database import ImageModel
    return ImageModel.objects(dataset_id=world["dataset"]["id"], deleted=False).order_by("id").first()


def test_a_class_goes_to_the_chosen_category(world, pose_model):
    from database import AnnotationModel, CategoryModel, DatasetModel
    c = world["client"]
    ds = world["dataset"]["id"]
    target = CategoryModel(name="MapTest_Pose", keypoint_labels=list(mpm.POSE_KEYPOINTS),
                           keypoint_edges=[[1, 2]])
    target.save()
    DatasetModel.objects(id=ds).update(push__categories=target.id)
    image = _image(world)
    try:
        r = c.post(f"/api/model/yolo/image/{image.id}", json={
            "model": pose_model, "conf": 0.5, "create_categories": True, "class_map": {"person": target.id}})
        assert r.status_code == 200, r.data
        assert r.get_json()["created"] == 1
        made = AnnotationModel.objects(image_id=image.id, category_id=target.id, source="model")
        assert made.count() == 1 and len(made.first().keypoints) == 99
        # no "person" category made for it, and the category's own skeleton is kept
        assert CategoryModel.objects(id__in=DatasetModel.objects(id=ds).first().categories,
                                     name="person").count() == 0
        assert CategoryModel.objects(id=target.id).first().keypoint_edges == [[1, 2]]
    finally:
        AnnotationModel.objects(image_id=image.id, category_id=target.id).delete()
        DatasetModel.objects(id=ds).update(pull__categories=target.id)
        target.delete()


def test_a_class_can_be_left_out(world, pose_model):
    from database import AnnotationModel
    c = world["client"]
    image = _image(world)
    before = AnnotationModel.objects(image_id=image.id).count()
    r = c.post(f"/api/model/yolo/image/{image.id}", json={
        "model": pose_model, "create_categories": True, "class_map": {"person": None}})
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body["created"] == 0 and body["ignored_classes"] == ["person"] and body["skipped_classes"] == []
    assert AnnotationModel.objects(image_id=image.id).count() == before


def test_only_the_datasets_categories(world, pose_model):
    from database import CategoryModel
    c = world["client"]
    image = _image(world)
    elsewhere = CategoryModel(name="MapTest_Elsewhere")
    elsewhere.save()
    try:
        for bad in ({"person": elsewhere.id}, {"person": "abc"}):
            r = c.post(f"/api/model/yolo/image/{image.id}", json={"model": pose_model, "class_map": bad})
            assert r.status_code == 400, bad
        r = c.post(f"/api/model/yolo/dataset/{world['dataset']['id']}",
                   json={"model": pose_model, "class_map": {"person": elsewhere.id}})
        assert r.status_code == 400
    finally:
        elsewhere.delete()


def test_the_mapping_wins_over_a_category_of_the_same_name(world, pose_model):
    """The dataset has a "person" category; mapped elsewhere (or left out),
    "person" predictions must not go into it."""
    from database import AnnotationModel, CategoryModel, DatasetModel
    c = world["client"]
    ds = world["dataset"]["id"]
    same = CategoryModel(name="person")
    same.save()
    target = CategoryModel(name="MapTest_Pose2", keypoint_labels=list(mpm.POSE_KEYPOINTS))
    target.save()
    DatasetModel.objects(id=ds).update(push_all__categories=[same.id, target.id])
    image = _image(world)
    try:
        r = c.post(f"/api/model/yolo/image/{image.id}", json={"model": pose_model, "class_map": {"person": target.id}})
        assert r.get_json()["created"] == 1
        assert AnnotationModel.objects(image_id=image.id, category_id=target.id, source="model").count() == 1
        assert AnnotationModel.objects(image_id=image.id, category_id=same.id).count() == 0
        r = c.post(f"/api/model/yolo/image/{image.id}", json={"model": pose_model, "class_map": {"person": None}})
        assert r.get_json()["created"] == 0 and r.get_json()["ignored_classes"] == ["person"]
        assert AnnotationModel.objects(image_id=image.id, category_id=same.id).count() == 0
    finally:
        AnnotationModel.objects(image_id=image.id, category_id__in=[same.id, target.id]).delete()
        DatasetModel.objects(id=ds).update(pull_all__categories=[same.id, target.id])
        same.delete()
        target.delete()
