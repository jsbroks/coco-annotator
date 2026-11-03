import pytest

pytestmark = pytest.mark.order(-1)


@pytest.fixture(scope="module")
def admin_client():
    from webserver import app
    from database import UserModel

    client = app.test_client()
    if UserModel.objects(username="boss").first() is None:
        if UserModel.total() == 0:
            client.post("/api/user/register", json={"username": "boss", "password": "pw", "name": "Boss"})
        else:
            from webserver.util.passwords import hash_password
            UserModel(username="boss", password=hash_password("pw"), name="Boss", is_admin=True).save()
    r = client.post("/api/user/login", json={"username": "boss", "password": "pw"})
    assert r.status_code == 200, r.data
    return client


def test_toggle_admin(admin_client):
    c = admin_client
    r = c.post("/api/admin/user/", json={"username": "student", "password": "pw", "name": "S", "isAdmin": True})
    assert r.status_code == 200, r.data

    r = c.patch("/api/admin/user/student", json={"isAdmin": False})
    assert r.status_code == 200, r.data
    assert r.get_json()["is_admin"] is False
    assert "password" not in r.get_json()

    # name/password only: admin flag unchanged
    r = c.patch("/api/admin/user/student", json={"name": "Student"})
    assert r.get_json()["is_admin"] is False
    assert r.get_json()["name"] == "Student"

    r = c.patch("/api/admin/user/student", json={"isAdmin": True})
    assert r.get_json()["is_admin"] is True
    assert "password" not in c.get("/api/admin/user/student").get_json()


def test_cannot_demote_or_delete_self(admin_client):
    r = admin_client.patch("/api/admin/user/boss", json={"isAdmin": False})
    assert r.status_code == 400
    r = admin_client.delete("/api/admin/user/boss")
    assert r.status_code == 400


def test_share_dataset_with_member(admin_client):
    from webserver import app
    c = admin_client
    r = c.post("/api/dataset/", json={"name": "shared_ds"})
    assert r.status_code == 200, r.data
    ds = r.get_json()["id"]
    c.post("/api/admin/user/", json={"username": "member", "password": "pw", "name": "M", "isAdmin": False})

    m = app.test_client()
    assert m.post("/api/user/login", json={"username": "member", "password": "pw"}).status_code == 200
    # not shared yet: a clean 400, not a server error
    assert m.get(f"/api/dataset/{ds}/data").status_code == 400

    assert c.post(f"/api/dataset/{ds}/share", json={"users": ["member"]}).status_code == 200
    names = [d["name"] for d in m.get("/api/dataset/data").get_json()["datasets"]]
    assert "shared_ds" in names
    assert m.get(f"/api/dataset/{ds}/data").status_code == 200


def test_clear_image_annotations(world):
    from database import AnnotationModel, ImageModel
    c = world["client"]
    image_id = world["images"][1]["id"]
    category = world["categories"]["ship"]
    for _ in range(2):
        r = c.post("/api/annotation/", json={"image_id": image_id, "category_id": category,
                                             "segmentation": [[1, 1, 20, 1, 20, 20]]})
        assert r.status_code == 200, r.data
    assert AnnotationModel.objects(image_id=image_id, deleted=False).count() >= 2

    r = c.delete(f"/api/image/{image_id}/annotations")
    assert r.status_code == 200, r.data
    assert r.get_json()["deleted"] >= 2
    assert AnnotationModel.objects(image_id=image_id, deleted=False).count() == 0
    # soft-deleted, so they can be restored from Undo
    assert AnnotationModel.objects(image_id=image_id, deleted=True).count() >= 2
    image = ImageModel.objects(id=image_id).first()
    assert image.num_annotations == 0 and not image.annotated
