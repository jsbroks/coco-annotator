"""Who may change what: viewers vs members, user managers, trash, sockets,
review and help requests."""
import os

from webserver.util.passwords import hash_password


def _login(username, **fields):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, **fields).save()
    c = app.test_client()
    r = c.post("/api/user/login", json={"username": username, "password": "pw"})
    assert r.status_code == 200, r.data
    return c


def _setup(dataset_directory, name):
    from PIL import Image
    owner = _login(name + "own")
    r = owner.post("/api/dataset/", json={"name": name, "categories": [name + "cat"]})
    assert r.status_code == 200, r.data
    ds = r.get_json()["id"]
    folder = os.path.join(dataset_directory, name)
    os.makedirs(folder, exist_ok=True)
    for i in range(2):
        Image.new("RGB", (64, 48), (10 * i, 80, 120)).save(os.path.join(folder, f"p{i}.jpg"))
    assert owner.get(f"/api/dataset/{ds}/scan").status_code == 200
    images = sorted(owner.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])
    cats = {c["name"]: c["id"] for c in owner.get("/api/category/").get_json()}
    return owner, ds, images, cats[name + "cat"]


def _role(key, perms):
    from database import RoleModel
    RoleModel.objects(key=key).delete()
    RoleModel(key=key, name=key, permissions=perms).save()


def test_seeing_every_dataset_does_not_allow_changing_them(dataset_directory):
    from database import AnnotationModel, DatasetModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_view")
    ann = owner.post("/api/annotation/", json={"image_id": images[0]["id"], "category_id": cat,
                                               "segmentation": [[1, 1, 30, 1, 30, 30]]}).get_json()["id"]
    _role("sec_seeall", ["all_datasets"])
    seer = _login("sec_seer", role="sec_seeall")

    # can look
    assert seer.get(f"/api/dataset/{ds}/data").status_code == 200
    # can not change
    assert seer.post("/api/annotation/", json={"image_id": images[0]["id"], "category_id": cat,
                                               "segmentation": [[1, 1, 9, 1, 9, 9]]}).status_code == 400
    assert seer.put(f"/api/annotation/{ann}", json={"category_id": cat}).status_code == 400
    assert seer.delete(f"/api/annotation/{ann}").status_code == 400
    assert not AnnotationModel.objects(id=ann).first().deleted
    assert seer.get(f"/api/dataset/{ds}/reset/metadata").status_code == 400
    assert seer.post(f"/api/dataset/{ds}", json={"categories": []}).status_code == 400
    assert DatasetModel.objects(id=ds).first().categories == [cat]
    assert seer.delete(f"/api/image/{images[1]['id']}/annotations").status_code == 400
    assert seer.post(f"/api/image/copy/{images[0]['id']}/{images[1]['id']}/annotations", json={}).status_code == 400
    assert seer.post(f"/api/review/image/{images[0]['id']}", json={"action": "submit"}).status_code == 403
    assert seer.get(f"/api/dataset/{ds}/scan").status_code == 400
    saved = seer.post("/api/annotator/data", json={"image": {"id": images[0]["id"]}, "dataset": {},
                                                    "categories": [{"id": cat, "color": "#000000"}]})
    assert saved.status_code == 403

    # a member can
    DatasetModel.objects(id=ds).update(push__users="sec_seer")
    assert seer.put(f"/api/annotation/{ann}", json={"category_id": cat}).status_code == 200


def test_annotation_category_must_belong_to_the_dataset(dataset_directory):
    from database import AnnotationModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_cat")
    other_owner, other_ds, _, other_cat = _setup(dataset_directory, "sec_cat2")
    ann = owner.post("/api/annotation/", json={"image_id": images[0]["id"], "category_id": cat,
                                               "segmentation": [[1, 1, 30, 1, 30, 30]]}).get_json()["id"]
    # an empty body changes nothing
    assert owner.put(f"/api/annotation/{ann}", json={}).status_code == 200
    assert AnnotationModel.objects(id=ann).first().category_id == cat
    # a category of another dataset is refused
    from database import UserModel
    UserModel.objects(username="sec_catown").update(set__is_admin=True)
    assert owner.put(f"/api/annotation/{ann}", json={"category_id": other_cat}).status_code == 400
    assert AnnotationModel.objects(id=ann).first().category_id == cat


def test_only_the_creator_renames_a_category(dataset_directory):
    from database import CategoryModel, DatasetModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_ren")
    member = _login("sec_renmem")
    DatasetModel.objects(id=ds).update(push__users="sec_renmem")
    r = member.put(f"/api/category/{cat}", json={"name": "renamed"})
    assert r.status_code == 403
    assert CategoryModel.objects(id=cat).first().name == "sec_rencat"
    assert owner.put(f"/api/category/{cat}", json={"name": "renamed"}).status_code == 200


def test_user_managers_stay_within_their_own_permissions(dataset_directory):
    from database import DatasetModel, UserModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_mu")
    _role("sec_hr", ["manage_users"])
    _role("sec_big", ["all_datasets", "activity"])
    _role("sec_small", [])
    hr = _login("sec_hrperson", role="sec_hr")

    # no roles with more than they have
    r = hr.post("/api/admin/user/", json={"username": "sec_sock", "password": "pw123", "role": "sec_big"})
    assert r.status_code == 403
    assert UserModel.objects(username="sec_sock").first() is None
    assert hr.post("/api/admin/user/", json={"username": "sec_ok", "password": "pw123",
                                             "role": "sec_small"}).status_code == 200
    # no adding people to someone else's dataset
    r = hr.post("/api/admin/users/bulk", json={"users": [{"username": "Z12345678", "password": "pw123"}],
                                               "datasetId": ds})
    assert r.status_code == 403
    assert "Z12345678" not in (DatasetModel.objects(id=ds).first().users or [])
    # no resetting the password of someone with more permissions
    _login("sec_bigperson", role="sec_big")
    assert hr.patch("/api/admin/user/sec_bigperson", json={"password": "newpw1"}).status_code == 403
    assert hr.delete("/api/admin/user/sec_bigperson").status_code == 403
    # plain users: fine
    _login("sec_plain")
    assert hr.patch("/api/admin/user/sec_plain", json={"password": "newpw1"}).status_code == 200
    # bad input is a 400, not a crash
    assert hr.patch("/api/admin/user/sec_plain", json={"name": None}).status_code in (200, 400)
    assert hr.get("/api/admin/users?limit=0").status_code == 200


def test_old_purge_endpoint_follows_trash_rules(dataset_directory):
    from database import DatasetModel, ImageModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_purge")
    member = _login("sec_purgemem")
    DatasetModel.objects(id=ds).update(push__users="sec_purgemem")
    img = images[0]["id"]
    assert owner.delete(f"/api/image/{img}").status_code == 200
    assert ImageModel.objects(id=img).first().deleted
    # no activity page: refused
    assert member.delete(f"/api/undo/?id={img}&instance=image").status_code == 403
    # with the page, still only the owner purges images for good
    _role("sec_act", ["activity"])
    from database import UserModel
    UserModel.objects(username="sec_purgemem").update(set__role="sec_act")
    member.delete(f"/api/undo/?id={img}&instance=image")
    member.post("/api/trash/purge", json={"items": [{"type": "image", "ids": [img]}]})
    member.post("/api/trash/empty")
    assert ImageModel.objects(id=img).first() is not None
    # bad ids do not crash
    assert member.post("/api/trash/purge", json={"items": [{"type": "image", "ids": ["x", None]}, "junk"]}) \
        .status_code == 200


def test_submit_does_not_undo_an_approval(dataset_directory):
    from database import DatasetModel, ImageModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_rev")
    labeler = _login("sec_revlab")
    DatasetModel.objects(id=ds).update(push__users="sec_revlab")
    img = images[0]["id"]
    assert labeler.post(f"/api/review/image/{img}", json={"action": "submit"}).status_code == 200
    assert owner.post(f"/api/review/image/{img}", json={"action": "approve"}).status_code == 200
    labeler.post(f"/api/review/image/{img}", json={"action": "submit"})
    labeler.post(f"/api/review/image/{img}", json={"action": "submit", "image_ids": [img]})
    assert ImageModel.objects(id=img).first().status == "approved"
    # broken id lists are a 400
    r = owner.post(f"/api/review/image/{img}", json={"action": "approve", "image_ids": ["x", [1]]})
    assert r.status_code == 400


def test_help_answers_need_a_current_reviewer(dataset_directory):
    from database import DatasetModel, HelpModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_help")
    rev = _login("sec_helprev")
    asker = _login("sec_helpask")
    DatasetModel.objects(id=ds).update(push__users="sec_helprev", push__reviewers="sec_helprev")
    DatasetModel.objects(id=ds).update(push__users="sec_helpask")
    r = asker.post("/api/help/", json={"image_id": images[0]["id"], "message": "?",
                                       "to": [{"x": 1}, "sec_helprev"], "annotation_id": 999999})
    assert r.status_code == 200, r.data
    hid = r.get_json()["id"]
    assert HelpModel.objects(id=hid).first().annotation_id is None
    assert [q["id"] for q in rev.get("/api/help/inbox").get_json()["incoming"]] == [hid]
    # taken off the dataset: no longer in the inbox, can not answer
    DatasetModel.objects(id=ds).update(pull__reviewers="sec_helprev", pull__users="sec_helprev")
    assert rev.get("/api/help/inbox").get_json()["incoming"] == []
    assert rev.post(f"/api/help/{hid}/reply", json={"message": "x"}).status_code == 403
    # a withdrawn question can not be answered
    assert asker.post(f"/api/help/{hid}/cancel").status_code == 200
    assert owner.post(f"/api/help/{hid}/reply", json={"message": "x", "resolve": True}).status_code == 400


def test_annotation_events_go_only_to_the_same_image(dataset_directory):
    from webserver import app
    from webserver.sockets import socketio
    from database import DatasetModel
    owner, ds, images, cat = _setup(dataset_directory, "sec_sock")
    member = _login("sec_sockmem")
    DatasetModel.objects(id=ds).update(push__users="sec_sockmem")
    stranger = _login("sec_sockstr")
    ann = owner.post("/api/annotation/", json={"image_id": images[0]["id"], "category_id": cat,
                                               "segmentation": [[1, 1, 30, 1, 30, 30]]}).get_json()

    # the test client needs the in-memory manager (no message queue)
    import socketio as python_socketio
    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s_owner = socketio.test_client(app, flask_test_client=owner)
        s_member = socketio.test_client(app, flask_test_client=member)
        s_other_image = socketio.test_client(app, flask_test_client=_login("sec_sockmem2"))
        DatasetModel.objects(id=ds).update(push__users="sec_sockmem2")
        s_stranger = socketio.test_client(app, flask_test_client=stranger)
        s_owner.emit("annotating", {"image_id": images[0]["id"], "active": True})
        s_member.emit("annotating", {"image_id": images[0]["id"], "active": True})
        s_other_image.emit("annotating", {"image_id": images[1]["id"], "active": True})
        s_stranger.emit("annotating", {"image_id": images[0]["id"], "active": True})
        for s in (s_owner, s_member, s_other_image, s_stranger):
            s.get_received()

        s_owner.emit("annotation", {"action": "modify", "annotation": ann})
        got = lambda s: [m for m in s.get_received() if m["name"] == "annotation"]
        assert len(got(s_member)) == 1
        # no echo back to the sender (a late echo would undo a newer edit)
        assert got(s_owner) == []
        assert got(s_other_image) == []
        assert got(s_stranger) == []
        # a stranger can not send (fake deletes)
        s_stranger.emit("annotation", {"action": "delete", "annotation": ann})
        assert got(s_member) == []
    finally:
        socketio.server.manager = queue_manager


def test_second_round(dataset_directory):
    """Import through /export, reviewers taken off with members, bulk default
    role, category checks on create, category colour by its creator only."""
    from database import AnnotationModel, CategoryModel, DatasetModel, UserModel
    import io
    import json
    owner, ds, images, cat = _setup(dataset_directory, "sec_r2")
    other_owner, other_ds, _, other_cat = _setup(dataset_directory, "sec_r2b")
    _role("sec_r2see", ["all_datasets"])
    seer = _login("sec_r2seer", role="sec_r2see")

    # the old import route is closed to viewers too
    coco = {"images": [{"id": 1, "file_name": "p0.jpg", "width": 64, "height": 48}],
            "categories": [{"id": 1, "name": "sec_r2cat"}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "segmentation": [[1, 1, 9, 1, 9, 9]],
                             "bbox": [1, 1, 8, 8], "area": 32, "iscrowd": 0}]}
    r = seer.post(f"/api/dataset/{ds}/export", data={"coco": (io.BytesIO(json.dumps(coco).encode()), "c.json")},
                  content_type="multipart/form-data")
    assert r.status_code == 400
    assert AnnotationModel.objects(dataset_id=ds).count() == 0
    # (the same request from the owner works)
    r = owner.post(f"/api/dataset/{ds}/export", data={"coco": (io.BytesIO(json.dumps(coco).encode()), "c.json")},
                   content_type="multipart/form-data")
    assert r.status_code == 200, r.data

    # removing a member removes them as reviewer
    DatasetModel.objects(id=ds).update(set__users=["sec_r2seer"], set__reviewers=["sec_r2seer"])
    img = images[0]["id"]
    assert owner.post(f"/api/dataset/{ds}/share", json={"users": []}).status_code == 200
    d = DatasetModel.objects(id=ds).first()
    assert d.reviewers == [] and d.users == []
    # and stale data (reviewer but not member) does not count either
    DatasetModel.objects(id=ds).update(set__reviewers=["sec_r2seer"])
    owner.post(f"/api/review/image/{img}", json={"action": "submit"})
    assert seer.post(f"/api/review/image/{img}", json={"action": "reject", "note": "x"}).status_code == 403

    # bulk create without a role: the default role must be within the manager's own
    from database import RoleModel
    _role("sec_r2hr", ["manage_users"])
    RoleModel.objects(key="user").update(set__permissions=["activity", "create_categories"], upsert=True)
    hr = _login("sec_r2hrp", role="sec_r2hr")
    try:
        r = hr.post("/api/admin/users/bulk", json={"users": [{"username": "Y12345678"}]})
        assert r.status_code == 403
        assert UserModel.objects(username="Y12345678").first() is None
    finally:
        RoleModel.objects(key="user").update(set__permissions=["create_categories"])

    # a category of another dataset can not be used on create
    r = owner.post("/api/annotation/", json={"image_id": img, "category_id": other_cat,
                                             "segmentation": [[1, 1, 9, 1, 9, 9]]})
    assert r.status_code == 400

    # colour of a category only by its creator
    member = _login("sec_r2mem")
    DatasetModel.objects(id=ds).update(push__users="sec_r2mem")
    before = CategoryModel.objects(id=cat).first().color
    r = member.post("/api/annotator/data", json={"image": {"id": img}, "dataset": {},
                                                  "categories": [{"id": cat, "color": "#123456", "annotations": []}]})
    assert r.status_code == 200
    assert CategoryModel.objects(id=cat).first().color == before
    owner.post("/api/annotator/data", json={"image": {"id": img}, "dataset": {},
                                            "categories": [{"id": cat, "color": "#123456", "annotations": []}]})
    assert CategoryModel.objects(id=cat).first().color == "#123456"


def test_dataset_page_hears_who_annotates(dataset_directory):
    from webserver import app
    from webserver.sockets import socketio
    from database import DatasetModel
    import socketio as python_socketio
    owner, ds, images, cat = _setup(dataset_directory, "sec_room")
    member = _login("sec_roommem")
    DatasetModel.objects(id=ds).update(push__users="sec_roommem")
    stranger = _login("sec_roomstr")
    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        page = socketio.test_client(app, flask_test_client=owner)
        outsider = socketio.test_client(app, flask_test_client=stranger)
        assert page.emit("watch_dataset", {"dataset_id": ds}, callback=True) is True
        assert outsider.emit("watch_dataset", {"dataset_id": ds}, callback=True) is False
        annot = socketio.test_client(app, flask_test_client=member)
        annot.emit("annotating", {"image_id": images[0]["id"], "active": True})
        got = [m for m in page.get_received() if m["name"] == "annotating"]
        assert got and got[-1]["args"][0]["active"] is True
        assert [m for m in outsider.get_received() if m["name"] == "annotating"] == []
    finally:
        socketio.server.manager = queue_manager
