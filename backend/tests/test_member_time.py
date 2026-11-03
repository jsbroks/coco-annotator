"""Time per member on the statistics page (image open in the annotator)."""
import datetime
import os
import time

from webserver.util.passwords import hash_password


def _login(username):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, is_admin=False).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def test_time_per_member(dataset_directory):
    from PIL import Image
    from database import ImageModel, SessionEvent
    from webserver import app
    from webserver.sockets import socketio
    import socketio as python_socketio

    owner = _login("tm_own")
    member = _login("tm_mem")
    ds = owner.post("/api/dataset/", json={"name": "tm_ds"}).get_json()["id"]
    folder = os.path.join(dataset_directory, "tm_ds")
    os.makedirs(folder, exist_ok=True)
    for i in range(2):
        Image.new("RGB", (16, 16)).save(os.path.join(folder, f"t{i}.jpg"))
    owner.get(f"/api/dataset/{ds}/scan")
    owner.post(f"/api/dataset/{ds}/members", json={"add": ["tm_mem"]})
    images = sorted(owner.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])

    # an old session without a time stamp (logged before sessions had one)
    ImageModel.objects(id=images[1]["id"]).update(
        push__events=SessionEvent(user="tm_mem", milliseconds=60000), inc__milliseconds=60000)
    # one from 10 days ago
    ImageModel.objects(id=images[1]["id"]).update(
        push__events=SessionEvent(user="tm_mem", milliseconds=30000,
                                  created_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=10)))

    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s = socketio.test_client(app, flask_test_client=member)
        s.emit("annotating", {"image_id": images[0]["id"], "active": True})
        time.sleep(0.2)
        # going idle stops the time
        s.emit("annotating", {"image_id": images[0]["id"], "active": False, "idle": True})
        time.sleep(0.3)
        # idle noticed 0.3 s after the last input: those 0.3 s are not counted
        s.emit("annotating", {"image_id": images[0]["id"], "active": True})
        time.sleep(0.5)
        s.emit("annotating", {"image_id": images[0]["id"], "active": False, "idle": True, "idle_ms": 300})
        time.sleep(0.2)
        s.emit("annotating", {"image_id": images[0]["id"], "active": True})
        time.sleep(0.2)
        s.emit("annotating", {"image_id": images[0]["id"], "active": False})
    finally:
        socketio.server.manager = queue_manager

    t = owner.get(f"/api/dataset/{ds}/stats").get_json()["time"]
    me = t["tm_mem"]
    assert me["images"] == 2
    # three short sessions (0.2 + (0.5 - 0.3) + 0.2 s; idle parts not counted) + 60 s + 30 s
    assert 90.5 < me["seconds"] < 90.8, me
    assert 0.5 < me["recent_seconds"] < 0.8, me
    assert me["last"] and me["last"].endswith("Z")
    assert "tm_own" not in t
