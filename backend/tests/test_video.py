"""Video import: frames at an interval become dataset images."""
import io
import os

import numpy as np


def _video_bytes(tmp_path, frames=30, fps=10):
    import cv2
    path = str(tmp_path / "clip.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), fps, (160, 120))
    for i in range(frames):
        frame = np.full((120, 160, 3), i * 8, np.uint8)
        writer.write(frame)
    writer.release()
    with open(path, "rb") as f:
        return f.read()


def test_frame_names_sort_in_time():
    from webserver.util.video import frame_name, safe_stem
    assert frame_name("a", 0) == "a_000m00s000.jpg"
    assert frame_name("a", 61500) == "a_001m01s500.jpg"
    assert safe_stem("my clip (1).MP4") == "my_clip_(1)"


def test_video_import(world, dataset_directory, tmp_path):
    from database import ImageModel, TaskModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "video_ds"}).get_json()["id"]
    data = _video_bytes(tmp_path)

    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(b"x"), "notes.txt")},
               content_type="multipart/form-data")
    assert r.status_code == 400
    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "harbour cam.avi"),
                                                "every_seconds": "1", "max_frames": "100"},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body["folder"] == "harbour_cam"
    task = TaskModel.objects(id=body["id"]).first()
    assert task.completed and task.errors == 0, task.logs

    # 3 seconds at 10 fps, one frame per second
    images = ImageModel.objects(dataset_id=ds).order_by("file_name")
    assert [i.file_name for i in images] == [
        "harbour_cam_000m00s000.jpg", "harbour_cam_000m01s000.jpg", "harbour_cam_000m02s000.jpg"]
    assert images[0].width == 160 and images[0].height == 120
    assert os.path.dirname(images[0].path).endswith("video_ds/harbour_cam")
    assert not os.listdir(os.path.join(dataset_directory, "video_ds", ".uploads"))   # video removed

    # the frame limit
    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "short.avi"),
                                                "every_seconds": "0.1", "max_frames": "5"},
               content_type="multipart/form-data")
    task = TaskModel.objects(id=r.get_json()["id"]).first()
    assert ImageModel.objects(dataset_id=ds, file_name__startswith="short_").count() == 5
    assert task.warnings == 1


def test_video_every_n_frames(world, tmp_path):
    from database import ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "video_frames_ds"}).get_json()["id"]
    data = _video_bytes(tmp_path)   # 30 frames at 10 fps

    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "cam.avi"), "every_frames": "0"},
               content_type="multipart/form-data")
    assert r.status_code == 400

    # one every 7 frames: frames 0, 7, 14, 21, 28 -> 0.0, 0.7, 1.4, 2.1, 2.8 s
    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "cam.avi"), "every_frames": "7"},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    names = [i.file_name for i in ImageModel.objects(dataset_id=ds).order_by("file_name")]
    assert names == ["cam_000m00s000.jpg", "cam_000m00s700.jpg", "cam_000m01s400.jpg",
                     "cam_000m02s100.jpg", "cam_000m02s800.jpg"]


def test_video_start_end(world, tmp_path):
    from database import ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "video_trim_ds"}).get_json()["id"]
    data = _video_bytes(tmp_path)   # 30 frames at 10 fps = 3 s

    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "t.avi"),
                                                "start_seconds": "2", "end_seconds": "1"},
               content_type="multipart/form-data")
    assert r.status_code == 400

    # 0.5 s to 2.0 s, one every 0.5 s: 0.5, 1.0, 1.5, 2.0
    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "t.avi"), "every_seconds": "0.5",
                                                "start_seconds": "0.5", "end_seconds": "2"},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    names = [i.file_name for i in ImageModel.objects(dataset_id=ds).order_by("file_name")]
    assert names == ["t_000m00s500.jpg", "t_000m01s000.jpg", "t_000m01s500.jpg", "t_000m02s000.jpg"]

    # from 2.5 s to the end, every 2 frames: frames 25, 27, 29
    r = c.post(f"/api/dataset/{ds}/video", data={"video": (io.BytesIO(data), "u.avi"), "every_frames": "2",
                                                "start_seconds": "2.5"},
               content_type="multipart/form-data")
    names = [i.file_name for i in ImageModel.objects(dataset_id=ds, file_name__startswith="u_").order_by("file_name")]
    assert names == ["u_000m02s500.jpg", "u_000m02s700.jpg", "u_000m02s900.jpg"]


def test_video_stage_then_import(world, tmp_path):
    from database import ImageModel
    from webserver import app
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "video_stage_ds"}).get_json()["id"]
    data = _video_bytes(tmp_path)   # 30 frames at 10 fps

    r = c.post("/api/dataset/video/stage", data={"video": (io.BytesIO(b"x"), "a.txt")},
               content_type="multipart/form-data")
    assert r.status_code == 400
    r = c.post("/api/dataset/video/stage", data={"video": (io.BytesIO(data), "lane cam.avi")},
               content_type="multipart/form-data")
    info = r.get_json()
    assert r.status_code == 200 and info["frames"] == 30 and info["fps"] == 10 and info["duration"] == 3
    assert info["width"] == 160 and info["name"] == "lane cam.avi"

    # another user cannot use it
    other = app.test_client()
    other.post("/api/user/register", json={"username": "stage_other", "password": "pw", "name": "O"})
    assert other.post(f"/api/dataset/{ds}/video", data={"upload_id": info["upload_id"]},
                      content_type="multipart/form-data").status_code == 400

    r = c.post(f"/api/dataset/{ds}/video", data={"upload_id": info["upload_id"], "every_seconds": "1",
                                                "start_seconds": "1"},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    names = [i.file_name for i in ImageModel.objects(dataset_id=ds).order_by("file_name")]
    assert names == ["lane_cam_000m01s000.jpg", "lane_cam_000m02s000.jpg"]
    # used up
    assert c.post(f"/api/dataset/{ds}/video", data={"upload_id": info["upload_id"]},
                  content_type="multipart/form-data").status_code == 400

    r = c.post("/api/dataset/video/stage", data={"video": (io.BytesIO(data), "b.avi")},
               content_type="multipart/form-data")
    assert c.delete(f"/api/dataset/video/stage/{r.get_json()['upload_id']}").get_json()["success"]


def test_video_chunked_upload(world, tmp_path):
    from database import ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "video_chunk_ds"}).get_json()["id"]
    data = _video_bytes(tmp_path)

    assert c.post("/api/dataset/video/stage/start", json={"name": "x.txt", "size": 10}).status_code == 400
    r = c.post("/api/dataset/video/stage/start", json={"name": "big cam.avi", "size": len(data)})
    uid = r.get_json()["upload_id"]
    piece = 4000
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + piece]
        r = c.put(f"/api/dataset/video/stage/{uid}/chunk?offset={offset}", data=chunk,
                  content_type="application/octet-stream")
        assert r.status_code == 200, r.data
        # a retried piece is not added twice
        r = c.put(f"/api/dataset/video/stage/{uid}/chunk?offset={offset}", data=chunk,
                  content_type="application/octet-stream")
        offset += len(chunk)
        assert r.get_json()["received"] == offset
    # a piece from the wrong place
    assert c.put(f"/api/dataset/video/stage/{uid}/chunk?offset=5", data=b"zz",
                 content_type="application/octet-stream").status_code in (200, 409)
    # not usable before finish
    assert c.post(f"/api/dataset/{ds}/video", data={"upload_id": uid},
                  content_type="multipart/form-data").status_code == 400
    info = c.post(f"/api/dataset/video/stage/{uid}/finish").get_json()
    assert info["frames"] == 30 and info["duration"] == 3

    r = c.post(f"/api/dataset/{ds}/video", data={"upload_id": uid, "every_seconds": "1"},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    assert ImageModel.objects(dataset_id=ds).count() == 3

    # an incomplete upload cannot be finished
    uid = c.post("/api/dataset/video/stage/start", json={"name": "c.avi", "size": 100}).get_json()["upload_id"]
    assert c.post(f"/api/dataset/video/stage/{uid}/finish").status_code == 400
    assert c.delete(f"/api/dataset/video/stage/{uid}").get_json()["success"]
