import pytest

pytestmark = pytest.mark.order(-1)


def test_undo_only_own_items(world):
    from webserver import app
    from webserver.util.passwords import hash_password
    from database import AnnotationModel, UserModel

    c = world["client"]
    image_id = world["images"][1]["id"]
    category = world["categories"]["ship"]
    r = c.post("/api/annotation/", json={"image_id": image_id, "category_id": category,
                                         "segmentation": [[1, 1, 30, 1, 30, 30]]})
    ann = r.get_json()["id"]
    assert c.delete(f"/api/annotation/{ann}").status_code == 200

    if UserModel.objects(username="stranger").first() is None:
        UserModel(username="stranger", password=hash_password("pw"), name="S", is_admin=False).save()
    s = app.test_client()
    assert s.post("/api/user/login", json={"username": "stranger", "password": "pw"}).status_code == 200

    listed = [i["id"] for i in s.get("/api/undo/list/?limit=100&type=annotation").get_json()]
    assert ann not in listed
    assert s.post(f"/api/undo/?id={ann}&instance=annotation").status_code == 400
    assert s.delete(f"/api/undo/?id={ann}&instance=dataset").status_code in (400, 403)
    assert AnnotationModel.objects(id=ann).first().deleted

    # the owner can restore it
    UserModel.objects(username="smoke").update(set__is_admin=True)
    assert c.post(f"/api/undo/?id={ann}&instance=annotation").status_code == 200
    assert not AnnotationModel.objects(id=ann).first().deleted


def test_copy_restored_annotations(world):
    """Annotations that were deleted and restored (they have a deleted_date)
    used to make "copy annotations" fail with a date ValidationError."""
    from database import AnnotationModel, UserModel
    UserModel.objects(username="smoke").update(set__is_admin=True)
    c = world["client"]
    src, dst = world["images"][0]["id"], world["images"][1]["id"]
    category = world["categories"]["boat"]
    r = c.post("/api/annotation/", json={"image_id": src, "category_id": category,
                                         "segmentation": [[5, 5, 60, 5, 60, 40, 5, 40]]})
    ann = r.get_json()["id"]
    # (the annotator computes the area when saving)
    AnnotationModel.objects(id=ann).update(set__area=1925, set__width=320, set__height=200)
    c.delete(f"/api/annotation/{ann}")
    c.post(f"/api/undo/?id={ann}&instance=annotation")
    assert AnnotationModel.objects(id=ann).first().deleted is False   # restored (and no stale deleted_date)

    before = AnnotationModel.objects(image_id=dst, deleted=False).count()
    r = c.post(f"/api/image/copy/{src}/{dst}/annotations", json={"category_ids": [category]})
    assert r.status_code == 200, r.data
    assert r.get_json()["annotations_created"] >= 1
    copies = AnnotationModel.objects(image_id=dst, deleted=False)
    assert copies.count() == before + r.get_json()["annotations_created"]
    copy = copies.order_by('-id').first()
    assert copy.id != ann and not copy.deleted and copy.deleted_date is None
    assert copy.segmentation == [[5, 5, 60, 5, 60, 40, 5, 40]]
