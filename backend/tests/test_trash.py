"""Trash: who / batch recorded, grouped listing, restore with parents, purge,
expiry, previews and visibility."""
import datetime
import os

import pytest


@pytest.fixture(autouse=True)
def _pages_allowed(monkeypatch):
    """These test the log itself; who may open the page: test_page_access.py"""
    from database import UserModel
    monkeypatch.setattr(UserModel, "can_page", lambda self, page: True)


@pytest.fixture(scope="module")
def trash_world(world, dataset_directory):
    from PIL import Image
    from database import CategoryModel, UserModel
    c = world["client"]
    UserModel.objects(username="smoke").update(set__is_admin=False)
    ds = c.post("/api/dataset/", json={"name": "trash_ds", "categories": ["car", "bus"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "trash_ds")
    os.makedirs(folder, exist_ok=True)
    for i in range(3):
        Image.new("RGB", (200, 100), (40 * i, 90, 120)).save(os.path.join(folder, f"t{i}.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    images = sorted(c.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])
    cats = {n: CategoryModel.objects(name=n).first().id for n in ("car", "bus")}
    return {"c": c, "ds": ds, "images": images, "cats": cats, "folder": folder}


def _ann(c, image_id, cat, x=10):
    from database import AnnotationModel
    r = c.post("/api/annotation/", json={"image_id": image_id, "category_id": cat,
                                         "segmentation": [[x, 10, x + 30, 10, x + 30, 40, x, 40]]})
    ann = r.get_json()["id"]
    AnnotationModel.objects(id=ann).update(set__area=900, set__bbox=[x, 10, 30, 30])
    return ann


def _group(c, **params):
    return c.get("/api/trash/", query_string=params).get_json()


def test_batches_listing_and_restore(trash_world):
    from database import AnnotationModel, ImageModel
    w = trash_world
    c, img = w["c"], w["images"][0]["id"]
    a1 = _ann(c, img, w["cats"]["car"], 10)
    _ann(c, img, w["cats"]["car"], 50)
    _ann(c, img, w["cats"]["bus"], 90)
    from webserver.util.trash import refresh_image
    refresh_image(img)
    assert ImageModel.objects(id=img).first().num_annotations == 3

    # one annotation deleted on its own: counts follow at once
    c.delete(f"/api/annotation/{a1}")
    deleted = AnnotationModel.objects(id=a1).first()
    assert deleted.deleted_by == "smoke" and deleted.delete_batch
    assert ImageModel.objects(id=img).first().num_annotations == 2

    # clearing the image = one entry with a per-category summary
    c.delete(f"/api/image/{img}/annotations")
    body = _group(c, type="annotation", dataset_id=w["ds"])
    batch = next(g for g in body["groups"] if g["count"] == 2)
    assert {x["name"]: x["n"] for x in batch["categories"]} == {"car": 1, "bus": 1}
    assert batch["image"]["file_name"] == "t0.jpg" and batch["dataset"]["name"] == "trash_ds"
    assert batch["deleted_by"] == "smoke" and batch["expires_at"]
    assert body["counts"]["annotation"] >= 2 and "smoke" in body["deleters"]
    assert any(d["name"] == "trash_ds" for d in body["datasets"])
    assert _group(c, q="t0.jpg")["total"] >= 2 and _group(c, q="no-such-thing")["total"] == 0

    r = c.post("/api/trash/restore", json={"items": [{"type": "annotation", "ids": batch["ids"]}]})
    assert r.status_code == 200 and r.get_json()["restored"] == 2
    image = ImageModel.objects(id=img).first()
    assert image.num_annotations == 2 and set(image.category_ids) == set(w["cats"].values())
    assert AnnotationModel.objects(id=batch["ids"][0]).first().deleted_date is None


def test_restore_needs_parent_and_purge(trash_world):
    from database import AnnotationModel, ImageModel
    w = trash_world
    c, img = w["c"], w["images"][1]
    ann = _ann(c, img["id"], w["cats"]["car"])
    c.delete(f"/api/annotation/{ann}")
    c.delete(f"/api/image/{img['id']}")

    r = c.post("/api/trash/restore", json={"items": [{"type": "annotation", "ids": [ann]}]})
    assert r.status_code == 409 and r.get_json()["parents"] == {"image": [img["id"]]}
    r = c.post("/api/trash/restore", json={"items": [{"type": "annotation", "ids": [ann]}], "include_parents": True})
    assert r.get_json()["restored"] == 2
    assert not ImageModel.objects(id=img["id"]).first().deleted
    assert ImageModel.objects(id=img["id"]).first().num_annotations == 1

    # preview: the image with the annotation outlined, cropped
    r = c.get(f"/api/trash/preview?image_id={img['id']}&annotations={ann}&crop=1&size=120")
    assert r.status_code == 200 and r.mimetype == "image/jpeg" and r.data[:2] == b"\xff\xd8"

    # permanent delete of an image removes the file and its annotations
    path = os.path.join(w["folder"], img["file_name"])
    c.delete(f"/api/image/{img['id']}")
    r = c.post("/api/trash/purge", json={"items": [{"type": "image", "ids": [img["id"]]}]})
    assert r.get_json()["deleted"] == 1
    assert not os.path.exists(path)
    assert ImageModel.objects(id=img["id"]).first() is None
    assert AnnotationModel.objects(id=ann).first() is None


def test_visibility_expiry_and_empty(trash_world):
    from webserver import app
    from webserver.util.passwords import hash_password
    from webserver.util import trash
    from database import AnnotationModel, UserModel
    w = trash_world
    c, img = w["c"], w["images"][2]["id"]
    ann = _ann(c, img, w["cats"]["bus"])
    c.delete(f"/api/annotation/{ann}")

    if UserModel.objects(username="outsider").first() is None:
        UserModel(username="outsider", password=hash_password("pw"), name="O", is_admin=False).save()
    o = app.test_client()
    o.post("/api/user/login", json={"username": "outsider", "password": "pw"})
    seen = [i for g in _group(o, type="annotation")["groups"] for i in g["ids"]]
    assert ann not in seen
    assert o.post("/api/trash/purge", json={"items": [{"type": "annotation", "ids": [ann]}]}).get_json()["deleted"] == 0
    assert o.get(f"/api/trash/preview?image_id={img}").status_code == 400

    # older than TRASH_DAYS: removed for good
    AnnotationModel.objects(id=ann).update(set__deleted_date=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=91))
    assert trash.purge_expired(force=True) >= 1
    assert AnnotationModel.objects(id=ann).first() is None

    ann2 = _ann(c, img, w["cats"]["bus"])
    c.delete(f"/api/annotation/{ann2}")
    assert c.post("/api/trash/empty").get_json()["deleted"] >= 1
    assert _group(c, dataset_id=w["ds"])["total"] == 0
