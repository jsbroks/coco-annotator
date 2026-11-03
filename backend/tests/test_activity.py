"""Activity log: annotating is merged per image, deletes can be restored from
the log, imports can be taken back, legacy trash gets lines, visibility."""
import datetime
import json
import os

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _pages_allowed(monkeypatch):
    """These test the log itself; who may open the page: test_page_access.py"""
    from database import UserModel
    monkeypatch.setattr(UserModel, "can_page", lambda self, page: True)



def _compound(polygon, width, height):
    pts = np.array(polygon).reshape(-1, 2) - [width / 2, height / 2]
    return ["CompoundPath", {"applyMatrix": True, "children": [
        ["Path", {"applyMatrix": True, "segments": pts.tolist(), "closed": True}]]}]


@pytest.fixture(scope="module")
def act_world(world, dataset_directory):
    from PIL import Image
    from database import CategoryModel, UserModel
    c = world["client"]
    UserModel.objects(username="smoke").update(set__is_admin=False)
    ds = c.post("/api/dataset/", json={"name": "act_ds", "categories": ["car", "bus"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "act_ds")
    os.makedirs(folder, exist_ok=True)
    for i in range(3):
        Image.new("RGB", (200, 100), (30 * i, 80, 120)).save(os.path.join(folder, f"a{i}.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    images = sorted(c.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])
    cats = {n: CategoryModel.objects(name=n).first().id for n in ("car", "bus")}
    return {"c": c, "ds": ds, "images": images, "cats": cats}


def _log(c, **params):
    return c.get("/api/activity/", query_string=params).get_json()


def _save(c, image_id, cat, ann_id, polygon):
    data = c.get(f"/api/annotator/data/{image_id}").get_json()
    payload = {
        "user": {}, "dataset": data["dataset"],
        "image": {"id": image_id, "metadata": {}, "category_ids": [cat]},
        "categories": [{"id": cat, "color": "#ff0000", "annotations": [{
            "id": ann_id, "isbbox": True, "color": "#ff0000", "metadata": {},
            "compoundPath": _compound(polygon, 200, 100), "sessions": []}]}],
    }
    assert c.post("/api/annotator/data", data=json.dumps(payload)).status_code == 200


def test_scan_and_annotating_merged(act_world):
    w = act_world
    c, img = w["c"], w["images"][0]["id"]
    body = _log(c, dataset_id=w["ds"])
    scan = next(e for e in body["entries"] if e["action"] == "scan")
    assert scan["counts"]["images"] == 3 and scan["user"] == "smoke"
    assert any(e["action"] == "dataset_create" for e in body["entries"])

    # an empty annotation (the annotator creates it before drawing) is not shown yet
    a1 = c.post("/api/annotation/", json={"image_id": img, "category_id": w["cats"]["car"]}).get_json()["id"]
    assert not [e for e in _log(c, group="annotate")["entries"] if e["image"] and e["image"]["id"] == img]

    box = [10, 10, 60, 10, 60, 40, 10, 40]
    _save(c, img, w["cats"]["car"], a1, box)
    _save(c, img, w["cats"]["car"], a1, box)  # autosave, nothing changed
    a2 = c.post("/api/annotation/", json={"image_id": img, "category_id": w["cats"]["car"]}).get_json()["id"]
    _save(c, img, w["cats"]["car"], a2, [100, 10, 150, 10, 150, 40, 100, 40])
    lines = [e for e in _log(c, group="annotate")["entries"] if e["image"] and e["image"]["id"] == img]
    assert len(lines) == 1 and lines[0]["counts"] == {"added": 2, "edited": 0}

    # an annotation from an earlier session is changed: "edited"
    from database import ActivityModel
    ActivityModel.objects(action="annotate", image_id=img).update(
        set__updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=2))
    _save(c, img, w["cats"]["car"], a1, [12, 10, 60, 10, 60, 45, 12, 45])
    lines = [e for e in _log(c, group="annotate")["entries"] if e["image"] and e["image"]["id"] == img]
    assert [l["counts"] for l in lines] == [{"added": 0, "edited": 1}, {"added": 2, "edited": 0}]
    assert _log(c, q="a0.jpg", group="annotate")["total"] == 2


def test_delete_restore_from_log(act_world):
    w = act_world
    c, img = w["c"], w["images"][0]["id"]
    c.delete(f"/api/image/{img}/annotations")
    body = _log(c, group="trash")
    line = body["entries"][0]
    assert line["action"] == "delete" and line["type"] == "annotation"
    assert line["trash"] == {"in_trash": 2, "restored": 0, "purged": 0} and len(line["ids"]) == 2
    assert line["detail"]["categories"] == [{"name": "car", "color": line["detail"]["categories"][0]["color"], "n": 2}]
    assert body["counts"]["trash"] >= 1

    r = c.post("/api/trash/restore", json={"items": [{"type": "annotation", "ids": line["ids"]}],
                                           "activity_id": line["id"]})
    assert r.get_json()["restored"] == 2
    entries = _log(c, group="delete")["entries"]
    assert entries[0]["action"] == "restore" and entries[0]["counts"]["items"] == 2
    assert entries[0]["detail"]["file_name"] == "a0.jpg"
    again = next(e for e in entries if e["id"] == line["id"])
    assert again["trash"]["restored"] == 2 and again["trash"]["in_trash"] == 0
    assert line["id"] not in [e["id"] for e in _log(c, group="trash")["entries"]]


def test_import_and_take_back(act_world):
    from database import AnnotationModel, ImageModel
    w = act_world
    c, img = w["c"], w["images"][1]
    coco = {"images": [{"id": 1, "file_name": img["file_name"], "width": 200, "height": 100}],
            "categories": [{"id": 1, "name": "bus"}, {"id": 2, "name": "tram"}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [5, 5, 20, 20]},
                            {"id": 2, "image_id": 1, "category_id": 2, "bbox": [50, 5, 20, 20]}]}
    import io
    r = c.post(f"/api/dataset/{w['ds']}/coco", data={"coco": (io.BytesIO(json.dumps(coco).encode()), "c.json")},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    line = _log(c, group="import")["entries"][0]
    assert line["action"] == "import" and line["counts"] == {"annotations": 2, "images": 1, "categories": 1}
    assert line["detail"]["new_categories"] == ["tram"] and line["can_undo"]
    assert ImageModel.objects(id=img["id"]).first().num_annotations == 2

    r = c.post(f"/api/activity/{line['id']}/undo")
    assert r.get_json()["deleted"] == 2
    assert AnnotationModel.objects(image_id=img["id"], deleted=False).count() == 0
    assert ImageModel.objects(id=img["id"]).first().num_annotations == 0
    line = next(e for e in _log(c, group="import")["entries"] if e["id"] == line["id"])
    assert line["undone"]["by"] == "smoke" and not line["can_undo"]
    assert c.post(f"/api/activity/{line['id']}/undo").status_code == 400
    kinds = [e["action"] for e in _log(c, group="delete")["entries"][:2]]
    assert kinds == ["undo_import", "delete"]


def test_legacy_backfill_visibility_and_expiry(act_world):
    from webserver import app
    from webserver.api import activity as activity_api
    from webserver.util import activity, trash
    from webserver.util.passwords import hash_password
    from database import ActivityModel, AnnotationModel, UserModel
    w = act_world
    c, img = w["c"], w["images"][2]["id"]

    # deleted before the log existed: no batch, no line
    old = AnnotationModel(image_id=img, category_id=w["cats"]["bus"], segmentation=[[1, 1, 9, 1, 9, 9]], area=32)
    old.save()
    AnnotationModel.objects(id=old.id).update(set__deleted=True, set__deleted_date=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    activity_api._backfilled[0] = False
    lines = [e for e in _log(c, group="trash")["entries"] if old.id in e["ids"]]
    assert len(lines) == 1 and lines[0]["user"] is None
    assert activity.backfill_trash() == 0  # only once

    if UserModel.objects(username="outsider2").first() is None:
        UserModel(username="outsider2", password=hash_password("pw"), name="O", is_admin=False).save()
    o = app.test_client()
    o.post("/api/user/login", json={"username": "outsider2", "password": "pw"})
    assert _log(o)["total"] == 0
    assert o.post(f"/api/activity/{lines[0]['id']}/undo").status_code == 400

    ActivityModel.objects(id=lines[0]["id"]).update(
        set__updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=91))
    trash.purge_expired(force=True)
    assert ActivityModel.objects(id=lines[0]["id"]).first() is None


def test_admin_actions_are_logged(world):
    """Accounts, roles, passwords and tasks show up in the activity log."""
    from database import ActivityModel, TaskModel, UserModel
    from webserver import app
    from webserver.util.passwords import hash_password
    UserModel.objects(username__in=["logboss", "LOGGED1", "D11111111"]).delete()
    UserModel(username="logboss", password=hash_password("pw"), name="B", is_admin=True).save()
    c = app.test_client()
    c.post("/api/user/login", json={"username": "logboss", "password": "pw"})
    start = ActivityModel.objects.count()

    c.post("/api/admin/user/", json={"username": "LOGGED1", "password": "pw123", "name": "L"})
    c.patch("/api/admin/user/LOGGED1", json={"name": "Logged", "password": "reset1"})
    role = c.post("/api/admin/roles", json={"name": "LogRole"}).get_json()["key"]
    c.put(f"/api/admin/roles/{role}", json={"permissions": ["tasks"]})
    c.patch("/api/admin/user/LOGGED1", json={"name": "", "password": "", "role": role})
    c.post("/api/admin/users/bulk", json={"users": [{"username": "D11111111"}]})
    c.delete(f"/api/admin/roles/{role}")
    c.delete("/api/admin/user/LOGGED1")
    c.post("/api/user/password", json={"password": "pw", "new_password": "pw999"})
    TaskModel(name="old", group="t", creator="logboss", completed=True).save()
    c.delete("/api/tasks/completed")

    actions = [a.action for a in ActivityModel.objects.order_by('id')[start:]]
    for action in ("user_create", "user_update", "role_create", "role_update", "user_bulk", "role_delete",
                   "user_delete", "password_change", "task_clear"):
        assert action in actions, action
    update = ActivityModel.objects(action="user_update", detail__name="LOGGED1").order_by('id')
    assert update[0].detail["changes"] == ["name", "password"]
    assert update[1].detail["role_from"] == "user" and update[1].detail["role_to"] == role

    listed = c.get("/api/activity/", query_string={"group": "admin", "per_page": 100}).get_json()
    assert {"user_delete", "role_create"} <= {e["action"] for e in listed["entries"]}
    UserModel.objects(username__in=["logboss", "D11111111"]).delete()
