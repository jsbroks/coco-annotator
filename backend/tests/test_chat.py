"""Chat: one room per dataset."""
import os

from webserver.util.passwords import hash_password


def _login(username, name=""):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=name or username, is_admin=False).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def _world(dataset_directory, prefix):
    from PIL import Image
    owner = _login(prefix + "_own", "老師")
    member = _login(prefix + "_mem", "阿明")
    stranger = _login(prefix + "_str")
    ds = owner.post("/api/dataset/", json={"name": prefix + "_ds"}).get_json()["id"]
    folder = os.path.join(dataset_directory, prefix + "_ds")
    os.makedirs(folder, exist_ok=True)
    Image.new("RGB", (32, 32)).save(os.path.join(folder, "a.jpg"))
    owner.get(f"/api/dataset/{ds}/scan")
    assert owner.post(f"/api/dataset/{ds}/members", json={"add": [prefix + "_mem"]}).status_code == 200
    image = owner.get(f"/api/dataset/{ds}/data").get_json()["images"][0]
    return owner, member, stranger, ds, image


def test_members_chat_and_unread(dataset_directory):
    owner, member, stranger, ds, image = _world(dataset_directory, "ch1")

    r = member.post(f"/api/chat/dataset/{ds}", json={"text": "  第一張是什麼？ ", "image_id": image["id"]})
    assert r.status_code == 200, r.data
    msg = r.get_json()
    assert msg["text"] == "第一張是什麼？" and msg["name"] == "阿明" and msg["file_name"] == "a.jpg"

    data = owner.get(f"/api/chat/dataset/{ds}").get_json()
    assert [m["text"] for m in data["messages"]] == ["第一張是什麼？"] and data["unread"] == 1
    # the sender has nothing unread
    assert member.get(f"/api/chat/dataset/{ds}").get_json()["unread"] == 0

    assert owner.post(f"/api/chat/dataset/{ds}/read", json={"last_id": msg["id"]}).get_json()["unread"] == 0
    owner.post(f"/api/chat/dataset/{ds}", json={"text": "是 vial"})
    assert member.get(f"/api/chat/dataset/{ds}").get_json()["unread"] == 1

    # not a member: no reading, no writing
    assert stranger.get(f"/api/chat/dataset/{ds}").status_code == 400
    assert stranger.post(f"/api/chat/dataset/{ds}", json={"text": "hi"}).status_code == 400
    # empty, too long, an image of another dataset
    assert member.post(f"/api/chat/dataset/{ds}", json={"text": "   "}).status_code == 400
    assert member.post(f"/api/chat/dataset/{ds}", json={"text": "x" * 1001}).status_code == 400
    assert member.post(f"/api/chat/dataset/{ds}", json={"text": "x", "image_id": 999999}).status_code == 400


def test_paging(dataset_directory):
    owner, member, _, ds, _ = _world(dataset_directory, "ch2")
    for i in range(7):
        owner.post(f"/api/chat/dataset/{ds}", json={"text": str(i)})
    page = member.get(f"/api/chat/dataset/{ds}?limit=3").get_json()
    assert [m["text"] for m in page["messages"]] == ["4", "5", "6"] and page["more"]
    older = member.get(f"/api/chat/dataset/{ds}?limit=5&before={page['messages'][0]['id']}").get_json()
    assert [m["text"] for m in older["messages"]] == ["0", "1", "2", "3"] and not older["more"]


def test_messages_reach_the_room_only(dataset_directory):
    from webserver import app
    from webserver.sockets import socketio
    import socketio as python_socketio
    owner, member, stranger, ds, _ = _world(dataset_directory, "ch3")

    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s_member = socketio.test_client(app, flask_test_client=member)
        s_stranger = socketio.test_client(app, flask_test_client=stranger)
        assert s_member.emit("watch_chat", {"dataset_id": ds}, callback=True) is True
        assert s_stranger.emit("watch_chat", {"dataset_id": ds}, callback=True) is False
        for s in (s_member, s_stranger):
            s.get_received()
        owner.post(f"/api/chat/dataset/{ds}", json={"text": "大家好"})
        got = lambda s: [m["args"][0]["text"] for m in s.get_received() if m["name"] == "chat"]
        assert got(s_member) == ["大家好"]
        assert got(s_stranger) == []
    finally:
        socketio.server.manager = queue_manager


def test_photos_and_emoji(dataset_directory):
    """Photos from the computer / phone (not the dataset's images) and emoji."""
    import io
    from PIL import Image
    owner, member, stranger, ds, _ = _world(dataset_directory, "ch_ph")

    def upload(client, img=None, fmt="JPEG", raw=None, name="p.jpg", **save):
        buf = io.BytesIO()
        if raw is None:
            img.save(buf, fmt, **save)
        else:
            buf.write(raw)
        buf.seek(0)
        return client.post(f"/api/chat/dataset/{ds}/photo", data={"file": (buf, name)},
                           content_type="multipart/form-data")

    # a phone photo turned sideways by its EXIF, with a place in it
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90
    exif[0x8825] = {1: "N"}  # GPS
    big = Image.new("RGB", (4000, 3000), (200, 30, 30))
    r = upload(member, big, exif=exif.tobytes())
    assert r.status_code == 200, r.data
    photo = r.get_json()
    assert (photo["w"], photo["h"]) == (1920, 2560)  # upright, at most 2560
    png = upload(member, Image.new("RGBA", (50, 40)), "PNG", name="s.png").get_json()
    assert upload(member, raw=b"not an image", name="x.jpg").status_code == 400
    assert upload(stranger, Image.new("RGB", (8, 8))).status_code == 400

    # a message of photos only, and one with emoji
    r = member.post(f"/api/chat/dataset/{ds}", json={"text": "", "photos": [photo["id"], png["id"]]})
    assert r.status_code == 200, r.data
    msg = r.get_json()
    assert [p["id"] for p in msg["photos"]] == [photo["id"], png["id"]] and msg["photos"][0]["w"] == 1920
    assert member.post(f"/api/chat/dataset/{ds}", json={"text": "好的 👍🎉"}).get_json()["text"] == "好的 👍🎉"
    # a photo goes with one message only, and only its uploader sends it
    assert member.post(f"/api/chat/dataset/{ds}", json={"photos": [photo["id"]]}).status_code == 400
    other = upload(owner, Image.new("RGB", (8, 8))).get_json()
    assert member.post(f"/api/chat/dataset/{ds}", json={"photos": [other["id"]]}).status_code == 400

    listed = owner.get(f"/api/chat/dataset/{ds}").get_json()["messages"]
    assert [p["id"] for p in listed[-2]["photos"]] == [photo["id"], png["id"]]

    # members see it (and a small copy); others do not
    got = owner.get(f"/api/chat/photo/{photo['id']}")
    assert got.status_code == 200
    shown = Image.open(io.BytesIO(got.data))
    assert shown.size == (1920, 2560) and not shown.getexif().get(0x8825)  # no place kept
    thumb = Image.open(io.BytesIO(owner.get(f"/api/chat/photo/{photo['id']}?thumb=1").data))
    assert max(thumb.size) == 640
    assert stranger.get(f"/api/chat/photo/{photo['id']}").status_code == 404
    # not sent yet: only its uploader sees it
    assert member.get(f"/api/chat/photo/{other['id']}").status_code == 404
