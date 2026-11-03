"""Assigning whole folders (e.g. the frames of one video) to one person."""
import os

from webserver.util.passwords import hash_password


def _login(username):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def test_assign_by_folder(dataset_directory):
    from PIL import Image
    from database import DatasetModel, ImageModel
    owner = _login("af_owner")
    for u in ("af_a", "af_b", "af_c"):
        _login(u)
    ds = owner.post("/api/dataset/", json={"name": "af_videos", "categories": ["af_cat"]}).get_json()["id"]
    DatasetModel.objects(id=ds).update(set__users=["af_a", "af_b", "af_c"])
    root = os.path.join(dataset_directory, "af_videos")
    sizes = {"clip1": 5, "clip2": 3, "clip3": 2}
    for folder, n in sizes.items():
        os.makedirs(os.path.join(root, folder), exist_ok=True)
        for i in range(n):
            Image.new("RGB", (32, 24), (i * 20, 50, 90)).save(os.path.join(root, folder, f"f{i:03d}.jpg"))
    Image.new("RGB", (32, 24)).save(os.path.join(root, "cover.jpg"))
    assert owner.get(f"/api/dataset/{ds}/scan").status_code == 200

    folders = owner.get(f"/api/review/dataset/{ds}/folders").get_json()["folders"]
    assert [(f["folder"], f["images"], f["unassigned"]) for f in folders] == \
        [("", 1, 1), ("clip1", 5, 5), ("clip2", 3, 3), ("clip3", 2, 2)]

    r = owner.post(f"/api/review/dataset/{ds}/assign",
                   json={"folders": {"clip1": "af_a", "clip2": "af_b", "clip3": "af_c"}, "scope": "unassigned"})
    assert r.status_code == 200, r.data
    assert r.get_json()["assigned"] == {"af_a": 5, "af_b": 3, "af_c": 2}

    def who(folder):
        return {i.assignee for i in ImageModel.objects(dataset_id=ds, path__contains=f"/{folder}/")}
    assert who("clip1") == {"af_a"} and who("clip2") == {"af_b"} and who("clip3") == {"af_c"}
    assert ImageModel.objects(dataset_id=ds, path__endswith="cover.jpg").first().assignee in (None, "")

    folders = {f["folder"]: f for f in owner.get(f"/api/review/dataset/{ds}/folders").get_json()["folders"]}
    assert folders["clip1"]["assignees"] == {"af_a": 5}
    # progress per folder
    img = ImageModel.objects(dataset_id=ds, path__contains="/clip2/").first()
    owner.post(f"/api/review/image/{img.id}", json={"action": "submit"})
    folders = {f["folder"]: f for f in owner.get(f"/api/review/dataset/{ds}/folders").get_json()["folders"]}
    assert folders["clip2"]["status"]["approved"] == 1 and folders["clip2"]["status"]["unlabeled"] == 2
    assert folders["clip1"]["status"]["unlabeled"] == 5 and folders["clip1"]["annotated"] == 0

    # "unassigned" scope: already assigned folders are left alone
    r = owner.post(f"/api/review/dataset/{ds}/assign", json={"folders": {"clip1": "af_b"}, "scope": "unassigned"})
    assert r.get_json()["assigned"] == {} and who("clip1") == {"af_a"}
    # "all" moves it; "" unassigns
    owner.post(f"/api/review/dataset/{ds}/assign", json={"folders": {"clip1": "af_b"}, "scope": "all"})
    assert who("clip1") == {"af_b"}
    r = owner.post(f"/api/review/dataset/{ds}/assign", json={"folders": {"clip3": ""}, "scope": "all"})
    assert r.get_json()["unassigned"] == 2 and who("clip3") <= {None, ""}

    # only members, only sensible input, only people who may assign
    assert owner.post(f"/api/review/dataset/{ds}/assign",
                      json={"folders": {"clip2": "stranger"}, "scope": "all"}).status_code == 400
    assert owner.post(f"/api/review/dataset/{ds}/assign",
                      json={"folders": {"clip2": ["af_a"]}, "scope": "all"}).status_code == 400
    member = _login("af_c")
    DatasetModel.objects(id=ds).update(set__users=["af_a", "af_b", "af_c"])
    assert member.post(f"/api/review/dataset/{ds}/assign",
                       json={"folders": {"clip2": "af_c"}, "scope": "all"}).status_code == 403
