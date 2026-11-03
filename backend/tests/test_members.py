"""Inviting and removing dataset members from the dataset page."""
from webserver.util.passwords import hash_password


def _login(username, name=""):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=name or username).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def test_invite_and_remove_members():
    from database import DatasetModel
    owner = _login("mb_owner")
    _login("B11111111", "王小明")
    _login("B22222222", "陳小華")
    member = _login("mb_member")
    ds = owner.post("/api/dataset/", json={"name": "mb_set"}).get_json()["id"]

    # search by username or name, members and the owner are not offered
    names = [u["username"] for u in owner.get(f"/api/dataset/{ds}/candidates?q=小").get_json()["users"]]
    assert names == ["B11111111", "B22222222"]
    r = owner.post(f"/api/dataset/{ds}/members", json={"add": ["b11111111", "mb_member", "mb_owner"]})
    assert r.status_code == 200, r.data
    assert r.get_json()["added"] == ["B11111111", "mb_member"]
    roles = {m["username"]: m["role"] for m in r.get_json()["members"]}
    assert roles == {"mb_owner": "owner", "B11111111": "member", "mb_member": "member"}
    assert "B11111111" not in [u["username"] for u in owner.get(f"/api/dataset/{ds}/candidates").get_json()["users"]]

    # unknown accounts: nothing changes
    r = owner.post(f"/api/dataset/{ds}/members", json={"add": ["B22222222", "nobody"]})
    assert r.status_code == 400 and r.get_json()["unknown"] == ["nobody"]
    assert "B22222222" not in DatasetModel.objects(id=ds).first().users

    # members can see the list but not change it
    data = member.get(f"/api/dataset/{ds}/members").get_json()
    assert data["can_manage"] is False and len(data["members"]) == 3
    assert member.post(f"/api/dataset/{ds}/members", json={"add": ["B22222222"]}).status_code == 403
    assert member.get(f"/api/dataset/{ds}/candidates").status_code == 403

    # removing a member also removes them as reviewer
    DatasetModel.objects(id=ds).update(set__reviewers=["mb_member"])
    r = owner.post(f"/api/dataset/{ds}/members", json={"remove": ["mb_member"]})
    assert r.get_json()["removed"] == ["mb_member"]
    d = DatasetModel.objects(id=ds).first()
    assert d.users == ["B11111111"] and d.reviewers == []

    # the old share call refuses unknown names too
    assert owner.post(f"/api/dataset/{ds}/share", json={"users": ["ghost"]}).status_code == 400
