"""Models page: settings per model, turning a model off, usage, download."""
import pytest


@pytest.fixture
def fake_models(monkeypatch, tmp_path):
    from webserver.util.yolo import YoloService, yolo
    weights = tmp_path / "boats.pt"
    weights.write_bytes(b"weights")
    monkeypatch.setattr(YoloService, "installed", property(lambda self: True))
    monkeypatch.setattr(yolo, "list", lambda: [{"name": "boats.pt", "task": "detect", "classes": ["boat"]}])

    def path_for(name):
        if name != "boats.pt":
            raise ValueError("Unknown model")
        return str(weights)
    monkeypatch.setattr(yolo, "path_for", path_for)
    monkeypatch.setattr(yolo, "device_name", lambda: "cpu")
    yield "boats.pt"
    from database import ModelInfoModel
    ModelInfoModel.objects(name="boats.pt").delete()


def test_manage_models(world, fake_models):
    from database import ActivityModel, UserModel
    from webserver import app
    from webserver.util.passwords import hash_password
    c = world["client"]
    UserModel.objects(username="smoke").update(set__is_admin=True)

    listing = c.get("/api/model/yolo?all=1").get_json()
    model = listing["models"][0]
    assert model["enabled"] is True and model["usage"]["runs"] == 0 and listing["can_manage"]

    ActivityModel(action="auto_annotate", user="smoke", detail={"model": "boats.pt"},
                  counts={"annotations": 7}).save()
    r = c.put("/api/model/yolo/model/boats.pt", json={"display_name": "Harbour boats v2", "note": "trained 10/01",
                                                      "default_conf": 0.4, "enabled": False})
    assert r.status_code == 200
    listing = c.get("/api/model/yolo?all=1").get_json()["models"][0]
    assert listing["display_name"] == "Harbour boats v2" and listing["default_conf"] == 0.4
    assert listing["enabled"] is False and listing["usage"] == {
        "runs": 1, "annotations": 7, "last_used": listing["usage"]["last_used"], "last_user": "smoke"}

    # turned off: not offered, and refused
    assert c.get("/api/model/yolo").get_json()["models"] == []
    r = c.post(f"/api/model/yolo/image/{world['images'][0]['id']}", json={"model": "boats.pt"})
    assert r.status_code == 400 and "turned off" in r.get_json()["message"]
    c.put("/api/model/yolo/model/boats.pt", json={"enabled": True})
    assert len(c.get("/api/model/yolo").get_json()["models"]) == 1

    r = c.get("/api/model/yolo/model/boats.pt/download")
    assert r.status_code == 200 and r.data == b"weights"

    # not an admin: read only
    if UserModel.objects(username="viewer").first() is None:
        UserModel(username="viewer", password=hash_password("pw"), name="V", is_admin=False).save()
    v = app.test_client()
    v.post("/api/user/login", json={"username": "viewer", "password": "pw"})
    # Models page needs to be given; running a model does not
    assert v.get("/api/model/yolo?all=1").status_code == 403
    assert v.get("/api/model/yolo").status_code == 200
    from database import RoleModel
    RoleModel(key="seemodels", name="See models", permissions=["models"]).save()
    UserModel.objects(username="viewer").update(set__role="seemodels")
    assert v.get("/api/model/yolo?all=1").get_json()["can_manage"] is False
    assert v.put("/api/model/yolo/model/boats.pt", json={"enabled": False}).status_code == 403
    assert v.get("/api/model/yolo/model/boats.pt/download").status_code == 403
    UserModel.objects(username="smoke").update(set__is_admin=False)
    RoleModel.objects(key="seemodels").delete()
