import pytest

pytestmark = pytest.mark.order(-1)


def test_bulk_create_students(world):
    from database import DatasetModel, UserModel
    from webserver import app
    UserModel.objects(username="smoke").update(set__is_admin=True)
    c = world["client"]
    ds = world["dataset"]["id"]
    r = c.post("/api/admin/users/bulk", json={"datasetId": ds, "users": [
        {"username": "b11223344", "name": "王小明"},
        {"username": "B11223355", "name": "陳小華", "password": "given-pw"},
        {"username": "B11223355", "name": "dup"},
        {"username": "12345678", "name": "no letter"},
        {"username": "B1234567", "name": "too short"},
    ]})
    assert r.status_code == 200, r.data
    body = r.get_json()
    names = {u["username"]: u for u in body["created"]}
    assert set(names) == {"B11223344", "B11223355"}
    assert len(names["B11223344"]["password"]) == 8
    assert names["B11223355"]["password"] == "given-pw"
    assert {i["reason"] for i in body["invalid"]} == {"format", "duplicate"}

    # members of the dataset, can log in, not admins
    assert {"B11223344", "B11223355"} <= set(DatasetModel.objects(id=ds).first().users)
    s = app.test_client()
    assert s.post("/api/user/login", json={"username": "B11223355", "password": "given-pw"}).status_code == 200
    assert not UserModel.objects(username="B11223355").first().is_admin
    assert world["dataset"]["name"] in [d["name"] for d in s.get("/api/dataset/data").get_json()["datasets"]]

    # running it again skips existing accounts
    r = c.post("/api/admin/users/bulk", json={"users": [{"username": "B11223344"}]})
    assert r.get_json()["created"] == [] and r.get_json()["existing"] == ["B11223344"]

    # students cannot create accounts
    assert s.post("/api/admin/users/bulk", json={"users": [{"username": "B99999999"}]}).status_code == 401


def test_first_login_must_change_password(world):
    """Accounts whose password an admin chose must pick their own first."""
    from database import UserModel
    from webserver import app
    from webserver.util.passwords import hash_password
    UserModel.objects(username="pwboss").delete()
    UserModel(username="pwboss", password=hash_password("pw"), name="B", is_admin=True).save()
    admin = app.test_client()
    admin.post("/api/user/login", json={"username": "pwboss", "password": "pw"})
    UserModel.objects(username__in=["C11111111", "C22222222"]).delete()
    r = admin.post("/api/admin/users/bulk", json={"users": [{"username": "C11111111", "password": "lab2026"},
                                                           {"username": "C22222222"}]}).get_json()
    assert len(r["created"]) == 2

    s = app.test_client()
    me = s.post("/api/user/login", json={"username": "C11111111", "password": "lab2026"}).get_json()["user"]
    assert me["must_change_password"] is True
    assert s.get("/api/user/").get_json()["user"]["must_change_password"] is True

    bad = s.post("/api/user/password", json={"password": "lab2026", "new_password": "lab2026"})
    assert bad.status_code == 400 and bad.get_json()["code"] == "same"
    assert s.post("/api/user/password", json={"password": "lab2026", "new_password": "abc"}).get_json()["code"] == "too_short"
    assert s.post("/api/user/password", json={"password": "lab2026", "new_password": "mine123"}).status_code == 200
    assert s.get("/api/user/").get_json()["user"]["must_change_password"] is False

    # an admin resetting the password asks again
    admin.patch("/api/admin/user/C11111111", json={"name": "", "password": "reset99"})
    assert UserModel.objects(username="C11111111").first().must_change_password is True
    # but not for the admin's own password
    admin.patch("/api/admin/user/pwboss", json={"name": "", "password": "newboss"})
    assert not UserModel.objects(username="pwboss").first().must_change_password
