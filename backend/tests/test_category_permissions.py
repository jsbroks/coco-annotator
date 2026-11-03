"""Roles: who may make new categories, and who may change everyone's."""
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


def _role(key, perms):
    from database import RoleModel
    RoleModel.objects(key=key).delete()
    RoleModel(key=key, name=key, permissions=perms).save()


def test_making_categories_needs_the_permission():
    from database import CategoryModel, DatasetModel
    # everyone (the default role) may
    maker = _login("cp_maker")
    assert maker.post("/api/category/", json={"name": "cp_one"}).status_code == 200
    assert maker.post("/api/dataset/", json={"name": "cp_ds1", "categories": ["cp_new1"]}).status_code == 200
    assert CategoryModel.objects(name="cp_new1").first() is not None

    _role("cp_nocreate", ["models"])
    plain = _login("cp_plain", role="cp_nocreate")
    r = plain.post("/api/category/", json={"name": "cp_two"})
    assert r.status_code == 403 and r.get_json()["code"] == "no_create_categories"
    assert CategoryModel.objects(name="cp_two").first() is None

    # a dataset with a new category name: refused, nothing made
    r = plain.post("/api/dataset/", json={"name": "cp_ds2", "categories": ["cp_one", "cp_new2"]})
    assert r.status_code == 403 and r.get_json()["name"] == "cp_new2"
    assert CategoryModel.objects(name="cp_new2").first() is None
    assert DatasetModel.objects(name="cp_ds2").first() is None
    # existing categories are fine
    r = plain.post("/api/dataset/", json={"name": "cp_ds3", "categories": ["cp_one"]})
    assert r.status_code == 200, r.data
    ds = r.get_json()["id"]
    r = plain.post(f"/api/dataset/{ds}", json={"categories": ["cp_one", "cp_new3"]})
    assert r.status_code == 403
    assert CategoryModel.objects(name="cp_new3").first() is None


def test_managing_categories_changes_everyones():
    from database import CategoryModel
    owner = _login("cp_owner")
    cat = owner.post("/api/category/", json={"name": "cp_owned"}).get_json()["id"]

    other = _login("cp_other")
    assert other.put(f"/api/category/{cat}", json={"name": "cp_renamed"}).status_code in (400, 403)

    _role("cp_curator", ["manage_categories"])
    curator = _login("cp_cur", role="cp_curator")
    # sees it without being in any of its datasets
    assert any(c["id"] == cat for c in curator.get("/api/category/").get_json())
    assert curator.put(f"/api/category/{cat}", json={"name": "cp_renamed", "color": "#123456"}).status_code == 200
    assert CategoryModel.objects(id=cat).first().name == "cp_renamed"
    assert curator.delete(f"/api/category/{cat}").status_code == 200


def test_roles_from_before_keep_making_categories():
    from database import RoleModel
    from database import roles
    RoleModel.objects(key="cp_old").delete()
    # saved by an older version: no perm_rev
    RoleModel._get_collection().insert_one({"_id": "cp_old", "name": "old", "permissions": ["models"]})
    roles._migrated = False
    assert "create_categories" in RoleModel.permissions_of("cp_old")
    # once: taking it away afterwards sticks
    RoleModel.objects(key="cp_old").update(set__permissions=["models"])
    roles._migrated = False
    assert "create_categories" not in RoleModel.permissions_of("cp_old")
    RoleModel.objects(key="cp_old").delete()
