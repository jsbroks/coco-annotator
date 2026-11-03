"""End-to-end smoke test of the REST API: dataset -> scan -> annotate
(including a rotated box) -> export -> import, on the upgraded stack."""
import io
import json
import os

import numpy as np
import pytest
from PIL import Image

from geometry import rbbox_to_polygon

pytestmark = pytest.mark.order(-1)  # run after the original ordered tests

WIDTH, HEIGHT = 320, 200


def _paper_compound(polygon):
    """Paper.js CompoundPath JSON for one polygon (paper coords are centred)."""
    pts = np.array(polygon).reshape(-1, 2) - [WIDTH / 2, HEIGHT / 2]
    path = ["Path", {"applyMatrix": True, "segments": pts.tolist(), "closed": True}]
    return ["CompoundPath", {"applyMatrix": True, "children": [path]}]


# The `world` fixture (a logged-in client with a scanned dataset) is in conftest.py


def test_dataset_pages(world):
    c, d = world["client"], world["dataset"]["id"]
    for url in [f"/api/dataset/{d}/stats", f"/api/dataset/{d}/users", f"/api/dataset/{d}/exports",
                "/api/dataset/data", "/api/dataset/", "/api/category/data", "/api/undo/list/",
                "/api/tasks/", "/api/info/", "/api/model/", "/api/image/", "/api/user/"]:
        r = c.get(url)
        assert r.status_code == 200, (url, r.data)


def test_thumbnail_and_image(world):
    c = world["client"]
    image_id = world["images"][0]["id"]
    for query in ["", "?thumbnail=true&width=100", "?original=true", "?asAttachment=true"]:
        r = c.get(f"/api/image/{image_id}{query}")
        assert r.status_code == 200, (query, r.data[:200])
        assert r.mimetype == "image/jpeg"


def test_annotate_rotated_box_and_export(world):
    c = world["client"]
    image = world["images"][0]
    ship = world["categories"]["ship"]

    r = c.post("/api/annotation/", json={"image_id": image["id"], "category_id": ship})
    assert r.status_code == 200, r.data
    annotation = r.get_json()

    r = c.get(f"/api/annotator/data/{image['id']}")
    assert r.status_code == 200, r.data
    data = r.get_json()

    rbbox = [160, 100, 80, 30, 30]
    polygon = rbbox_to_polygon(rbbox)
    payload = {
        "mode": "segment",
        "user": {},
        "dataset": data["dataset"],
        "image": {"id": image["id"], "metadata": {}, "category_ids": [ship]},
        "categories": [{
            "id": ship,
            "color": "#ff0000",
            "annotations": [{
                "id": annotation["id"],
                "isbbox": False,
                "isrbbox": True,
                "color": "#ff0000",
                "metadata": {},
                "compoundPath": _paper_compound(polygon),
                "sessions": [],
            }],
        }],
    }
    r = c.post("/api/annotator/data", data=json.dumps(payload))
    assert r.status_code == 200, r.data

    r = c.get(f"/api/image/{image['id']}/coco")
    assert r.status_code == 200, r.data
    coco = r.get_json()
    saved = coco["annotations"][0]
    assert saved["isrbbox"] is True
    assert saved["rbbox"] == pytest.approx(rbbox, abs=0.05)
    assert saved["area"] == pytest.approx(80 * 30, rel=0.05)

    # full dataset export through the (eager) Celery task
    d = world["dataset"]["id"]
    r = c.get(f"/api/dataset/{d}/export?categories=")
    assert r.status_code == 200, r.data
    exports = c.get(f"/api/dataset/{d}/exports").get_json()
    assert exports, "export was not created"
    r = c.get(f"/api/export/{exports[0]['id']}/download")
    assert r.status_code == 200, r.data[:200]
    exported = json.loads(r.data)
    rotated = [a for a in exported["annotations"] if a.get("isrbbox")]
    assert len(rotated) == 1
    assert rotated[0]["rbbox"] == pytest.approx(rbbox, abs=0.05)


def test_import_rbbox_without_polygon(world):
    c = world["client"]
    d = world["dataset"]["id"]
    image = world["images"][1]
    coco = {
        "images": [{"id": 1, "file_name": image["file_name"], "width": WIDTH, "height": HEIGHT}],
        "categories": [{"id": 7, "name": "boat"}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 7, "rbbox": [100, 80, 40, 20, -15]}],
    }
    data = {"coco": (io.BytesIO(json.dumps(coco).encode()), "coco.json")}
    r = c.post(f"/api/dataset/{d}/coco", data=data, content_type="multipart/form-data")
    assert r.status_code == 200, r.data

    r = c.get(f"/api/image/{image['id']}/coco")
    annotations = r.get_json()["annotations"]
    assert len(annotations) == 1
    assert annotations[0]["isrbbox"] is True
    assert len(annotations[0]["segmentation"][0]) == 8


def test_annotation_lifecycle(world):
    c = world["client"]
    image = world["images"][1]
    boat = world["categories"]["boat"]
    r = c.post("/api/annotation/", json={
        "image_id": image["id"], "category_id": boat,
        "segmentation": [[10, 10, 50, 10, 50, 40, 10, 40]],
    })
    assert r.status_code == 200, r.data
    aid = r.get_json()["id"]

    assert c.put(f"/api/annotation/{aid}", json={"category_id": world["categories"]["ship"]}).status_code == 200
    assert c.delete(f"/api/annotation/{aid}").status_code == 200
    r = c.post("/api/undo/", json={"id": aid, "instance": "annotation"})
    assert r.status_code == 200, r.data

    src, dst = world["images"][1]["id"], world["images"][0]["id"]
    r = c.post(f"/api/image/copy/{src}/{dst}/annotations", json={"category_ids": []})
    assert r.status_code == 200, r.data


def test_sam_disabled_without_checkpoint(world):
    c = world["client"]
    image_id = world["images"][0]["id"]
    assert c.get("/api/model/").get_json()["sam"]["available"] is False
    r = c.post(f"/api/model/sam/{image_id}", json={"points": [[10, 10]], "labels": [1]})
    assert r.status_code == 400


def test_missing_thumbnail_is_generated_on_request(world):
    from database import ImageModel
    c = world["client"]
    image_id = world["images"][1]["id"]
    image = ImageModel.objects(id=image_id).first()
    image.thumbnail_delete()
    assert not os.path.isfile(image.thumbnail_path())

    r = c.get(f"/api/image/{image_id}?thumbnail=true&width=250")
    assert r.status_code == 200, r.data[:200]
    assert r.mimetype == "image/jpeg"
    assert os.path.isfile(image.thumbnail_path())


def test_thumbnail_task_ignores_missing_image(world):
    from workers.tasks import thumbnail_generate_single_image
    thumbnail_generate_single_image(999999)  # must not raise


def test_missing_image_file_returns_404(world):
    from database import ImageModel
    c = world["client"]
    image = ImageModel.objects(id=world["images"][0]["id"]).first()
    moved = image.path + ".moved"
    os.rename(image.path, moved)
    try:
        for query in ["", "?thumbnail=true&width=100", "?original=true"]:
            r = c.get(f"/api/image/{image.id}{query}")
            assert r.status_code == 404, (query, r.status_code)
        from workers.tasks import thumbnail_generate_single_image
        thumbnail_generate_single_image(image.id)  # must not raise
    finally:
        os.rename(moved, image.path)


def test_registration_can_be_disabled(world, monkeypatch):
    from config import Config
    from webserver import app

    client = app.test_client()  # not logged in
    monkeypatch.setattr(Config, "ALLOW_REGISTRATION", False)
    info = client.get("/api/info/").get_json()
    assert info["allow_registration"] is False
    assert info["total_users"] >= 1

    r = client.post("/api/user/register", json={"username": "intruder", "password": "pw", "name": "X"})
    assert r.status_code == 400
    assert "disabled" in r.get_json()["message"]


def test_socket_payload_limit_raised():
    """Long-polling sends queued messages in one payload: more than 16 must be accepted."""
    from engineio.payload import Payload
    import webserver.sockets  # noqa: F401  (sets the limit)
    assert Payload.max_decode_packets >= 1000
    packets = "".join(f"4{i}\x1e" for i in range(100)).rstrip("\x1e")
    assert len(Payload(encoded_payload=packets).packets) == 100


def test_copy_returns_ids_and_undo(world):
    from database import AnnotationModel, ImageModel
    c = world["client"]
    images = list(ImageModel.objects(dataset_id=world["dataset"]["id"], deleted=False).order_by("id"))
    src, dst = images[0], images[1]
    cat = world["dataset"]["categories"][0]
    c.post("/api/annotation/", json={"image_id": src.id, "category_id": cat,
                                     "segmentation": [[1, 1, 30, 1, 30, 30, 1, 30]]})
    AnnotationModel.objects(image_id=src.id).update(set__area=841)
    before = AnnotationModel.objects(image_id=dst.id, deleted=False).count()
    r = c.post(f"/api/image/copy/{src.id}/{dst.id}/annotations", json={"category_ids": []}).get_json()
    assert r["annotations_created"] == len(r["ids"]) >= 1
    assert AnnotationModel.objects(image_id=dst.id, deleted=False).count() == before + len(r["ids"])
    r2 = c.post(f"/api/image/copy/{dst.id}/annotations/undo", json={"ids": r["ids"]}).get_json()
    assert r2["removed"] == len(r["ids"])
    assert AnnotationModel.objects(image_id=dst.id, deleted=False).count() == before
