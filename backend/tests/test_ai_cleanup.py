"""Deleting what models made, all at once: by model / category, people's
annotations and (by default) model results people changed stay, and the
deleted ones go to the trash."""
import pytest


@pytest.fixture
def made(world):
    from database import AnnotationModel, ImageModel
    from database.events import SessionEvent
    ds = world["dataset"]["id"]
    cats = world["dataset"]["categories"]
    images = list(ImageModel.objects(dataset_id=ds, deleted=False).order_by("id"))
    seg = [[1, 1, 30, 1, 30, 30, 1, 30]]

    def add(image, category, **fields):
        a = AnnotationModel(image_id=image.id, dataset_id=ds, category_id=category, segmentation=seg,
                            bbox=[1, 1, 29, 29], area=841, **fields)
        a.save()
        return a.id
    ids = {
        "human": add(images[0], cats[0]),
        "a1": add(images[0], cats[0], source="model", model="a.pt"),
        "a2": add(images[1], cats[1], source="model", model="a.pt"),
        "b1": add(images[1], cats[0], source="model", model="b.task"),
        "nomodel": add(images[1], cats[1], source="model"),
        "edited": add(images[1], cats[0], source="model", model="a.pt",
                      events=[SessionEvent(user="smoke", milliseconds=1200)]),
    }
    yield {"ds": ds, "cats": cats, "ids": ids, "images": images}
    AnnotationModel.objects(id__in=list(ids.values())).delete()


def _live(ids):
    from database import AnnotationModel
    return {k for k, v in ids.items() if AnnotationModel.objects(id=v, deleted=False).first()}


def test_summary_counts_models_categories_and_edits(world, made):
    c = world["client"]
    s = c.get(f"/api/dataset/{made['ds']}/ai").get_json()
    assert s["total"] == 5 and s["edited"] == 1
    assert {m["name"]: m["count"] for m in s["models"]} == {"a.pt": 3, "b.task": 1, "": 1}
    assert s["matching"] == 4 and s["matching_images"] == 2 and s["can_edit"]
    s = c.get(f"/api/dataset/{made['ds']}/ai", query_string={"model": "a.pt", "keep_edited": "false"}).get_json()
    assert s["matching"] == 3
    assert c.get(f"/api/dataset/{made['ds']}/ai", query_string={"category_id": "x"}).status_code == 400


def test_delete_by_model_keeps_people_and_edits(world, made):
    from database import AnnotationModel, ImageModel
    c = world["client"]
    r = c.post(f"/api/dataset/{made['ds']}/ai/delete", json={"model": "a.pt"})
    assert r.status_code == 200, r.data
    assert r.get_json()["deleted"] == 2 and r.get_json()["images"] == 2
    assert _live(made["ids"]) == {"human", "b1", "edited", "nomodel"}
    # in the trash, restorable
    gone = AnnotationModel.objects(id=made["ids"]["a1"]).first()
    assert gone.deleted and gone.delete_batch == r.get_json()["batch"]
    # the image counts follow
    first = ImageModel.objects(id=made["images"][0].id).first()
    assert first.num_annotations == AnnotationModel.objects(image_id=first.id, deleted=False, area__gt=0).count()


def test_delete_by_category_and_edited_too(world, made):
    c = world["client"]
    r = c.post(f"/api/dataset/{made['ds']}/ai/delete",
               json={"category_id": made["cats"][0], "keep_edited": False}).get_json()
    assert r["deleted"] == 3 and _live(made["ids"]) == {"human", "a2", "nomodel"}


def test_delete_only_results_without_a_model_name(world, made):
    """'(older, model not recorded)' must not mean 'all models'."""
    c = world["client"]
    s = c.get(f"/api/dataset/{made['ds']}/ai", query_string={"model": "__none__"}).get_json()
    assert s["matching"] == 1
    r = c.post(f"/api/dataset/{made['ds']}/ai/delete", json={"model": "__none__"}).get_json()
    assert r["deleted"] == 1 and _live(made["ids"]) == {"human", "a1", "a2", "b1", "edited"}


def test_only_editors_may_delete(world, made):
    from database import DatasetModel, UserModel
    from webserver import app
    from webserver.util.passwords import hash_password
    UserModel.objects(username="ai_viewer").delete()
    UserModel(username="ai_viewer", password=hash_password("pw"), name="v", is_admin=False).save()
    DatasetModel.objects(id=made["ds"]).update(push__users="ai_viewer")
    viewer = app.test_client()
    viewer.post("/api/user/login", json={"username": "ai_viewer", "password": "pw"})
    try:
        if not viewer.get(f"/api/dataset/{made['ds']}/ai").get_json()["can_edit"]:
            assert viewer.post(f"/api/dataset/{made['ds']}/ai/delete", json={}).status_code == 403
            assert _live(made["ids"]) == set(made["ids"])
    finally:
        DatasetModel.objects(id=made["ds"]).update(pull__users="ai_viewer")
    stranger = app.test_client()
    UserModel.objects(username="ai_stranger").delete()
    UserModel(username="ai_stranger", password=hash_password("pw"), name="s", is_admin=False).save()
    stranger.post("/api/user/login", json={"username": "ai_stranger", "password": "pw"})
    assert stranger.post(f"/api/dataset/{made['ds']}/ai/delete", json={}).status_code == 400
