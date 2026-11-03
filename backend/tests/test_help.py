"""Asking the dataset's creator / reviewers for help on an image."""
import os

from webserver.util.passwords import hash_password


def _login(username, **fields):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username.title(), **fields).save()
    c = app.test_client()
    c.post("/api/user/login", json={"username": username, "password": "pw"})
    return c


def test_ask_and_answer(world, dataset_directory, monkeypatch):
    from PIL import Image
    from database import HelpModel, ImageModel
    from webserver import sockets

    pushed = []
    monkeypatch.setattr(sockets, "notify_user", lambda user, event, data: pushed.append((user, event, data["id"])))

    owner = _login("helpowner")
    reviewer = _login("helprev")
    student = _login("helpstudent")
    outsider = _login("helpother")
    ds = owner.post("/api/dataset/", json={"name": "helpds"}).get_json()["id"]
    owner.post(f"/api/dataset/{ds}/share", json={"users": ["helprev", "helpstudent"]})
    owner.post(f"/api/review/dataset/{ds}/reviewers", json={"reviewers": ["helprev"]})
    folder = os.path.join(dataset_directory, "helpds")
    os.makedirs(folder, exist_ok=True)
    Image.new("RGB", (40, 30)).save(os.path.join(folder, "q.jpg"))
    owner.get(f"/api/dataset/{ds}/scan")
    image = ImageModel.objects(dataset_id=ds).first()

    sockets.ONLINE["helprev"] = {"sid1"}
    try:
        helpers = student.get(f"/api/help/helpers/{image.id}").get_json()["helpers"]
    finally:
        sockets.ONLINE.pop("helprev", None)
    # both online (the owner was just active, the reviewer has the app open): creator first
    assert [h["username"] for h in helpers] == ["helpowner", "helprev"] and all(h["online"] for h in helpers)
    assert {h["username"]: h["role"] for h in helpers} == {"helprev": "reviewer", "helpowner": "creator"}

    assert student.post("/api/help/", json={"image_id": image.id, "message": ""}).status_code == 400
    # no note needed: where the asker zoomed to is enough (kept inside the image)
    r = student.post("/api/help/", json={"image_id": image.id, "region": {"x": 30, "y": -5, "w": 50, "h": 10}})
    assert r.status_code == 200 and r.get_json()["region"] == {"x": 30.0, "y": 0.0, "w": 10.0, "h": 10.0}
    HelpModel.objects(id=r.get_json()["id"]).delete()
    pushed.clear()
    assert outsider.post("/api/help/", json={"image_id": image.id, "message": "?"}).status_code == 400
    r = student.post("/api/help/", json={"image_id": image.id, "message": "這個針頭要框到哪裡？", "to": ["helprev", "nobody"]})
    assert r.status_code == 200, r.get_json()
    req = r.get_json()
    assert req["to"] == ["helprev"] and pushed == [("helprev", "helpRequest", req["id"])]

    inbox = reviewer.get("/api/help/inbox").get_json()
    assert [q["id"] for q in inbox["incoming"]] == [req["id"]]
    on_image = reviewer.get(f"/api/help/image/{image.id}").get_json()["requests"]
    assert on_image[0]["can_answer"] is True and on_image[0]["user_name"] == "Helpstudent"

    assert outsider.post(f"/api/help/{req['id']}/reply", json={"message": "x"}).status_code in (400, 403)
    r = reviewer.post(f"/api/help/{req['id']}/reply", json={"message": "框到針尖", "resolve": True})
    assert r.status_code == 200 and r.get_json()["status"] == "resolved"
    assert ("helpstudent", "helpReply", req["id"]) in pushed
    assert reviewer.get("/api/help/inbox").get_json()["incoming"] == []
    mine = student.get("/api/help/inbox").get_json()["mine"]
    assert mine[0]["replies"][0]["message"] == "框到針尖" and mine[0]["replies"][0]["name"] == "Helprev"
    # the asker closes it: gone from their lists and the image
    assert student.post(f"/api/help/{req['id']}/seen").get_json()["success"]
    assert student.get("/api/help/inbox").get_json()["mine"] == []
    assert student.get(f"/api/help/image/{image.id}").get_json()["requests"] == []
    HelpModel.objects.delete()
