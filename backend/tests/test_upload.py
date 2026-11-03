import io
import os

import pytest
from PIL import Image

pytestmark = pytest.mark.order(-1)


def _png(color=(10, 20, 30), size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


def _upload(client, dataset_id, name, data):
    return client.post("/api/image/", data={"image": (data, name), "dataset_id": str(dataset_id)},
                       content_type="multipart/form-data")


def test_upload_images(world, dataset_directory):
    from database import ImageModel
    c = world["client"]
    ds = world["dataset"]["id"]

    r = _upload(c, ds, "上傳 測試.png", _png())
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body["existed"] is False and body["file_name"] == "上傳 測試.png"
    img = ImageModel.objects(id=body["id"]).first()
    assert img.width == 40 and os.path.isfile(img.path)
    assert os.path.dirname(img.path).endswith("smoke")

    # same name again: skipped, not overwritten
    r = _upload(c, ds, "上傳 測試.png", _png((200, 0, 0)))
    assert r.get_json() == {"id": body["id"], "file_name": "上傳 測試.png", "existed": True}

    # folders in the name are dropped (no writing outside the dataset folder)
    r = _upload(c, ds, "../../evil.png", _png())
    assert r.status_code == 200 and r.get_json()["file_name"] == "evil.png"
    assert not os.path.exists(os.path.join(dataset_directory, "..", "evil.png"))

    assert _upload(c, ds, "notes.txt", io.BytesIO(b"hello")).status_code == 400
    assert _upload(c, ds, "fake.jpg", io.BytesIO(b"not an image")).status_code == 400


def test_upload_needs_access(world):
    from webserver import app
    from webserver.util.passwords import hash_password
    from database import UserModel
    if UserModel.objects(username="outsider").first() is None:
        UserModel(username="outsider", password=hash_password("pw"), name="O", is_admin=False).save()
    m = app.test_client()
    assert m.post("/api/user/login", json={"username": "outsider", "password": "pw"}).status_code == 200
    r = _upload(m, world["dataset"]["id"], "x.png", _png())
    assert r.status_code == 400


def test_dataset_name_cannot_escape_folder(world):
    c = world["client"]
    for bad in ["../x", "a/b", ".hidden", "", "  "]:
        assert c.post("/api/dataset/", json={"name": bad}).status_code == 400, bad


def test_small_thumbnails_are_cached(world):
    import io as _io
    import os
    from PIL import Image as PILImage
    from database import ImageModel
    c = world["client"]
    image = ImageModel.objects(id=world["images"][0]["id"]).first()
    r = c.get(f"/api/image/{image.id}?width=250&thumbnail=true")
    assert r.status_code == 200 and r.mimetype == "image/jpeg"
    with PILImage.open(_io.BytesIO(r.data)) as im:
        assert im.width <= 250
    cached = [f for f in os.listdir(os.path.dirname(image.thumbnail_path())) if ".250x" in f]
    assert cached, "small thumbnail not cached"
    assert c.get(f"/api/image/{image.id}?width=250&thumbnail=true").data == r.data
