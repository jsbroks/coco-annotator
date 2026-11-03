"""MediaPipe models: their files are listed like YOLO ones, and their
outputs become the same prediction dicts (no MediaPipe needed here: the
results are stand-ins with the same fields)."""
import io
import os
import zipfile
from types import SimpleNamespace as NS

import numpy as np
import pytest

from webserver.util import mediapipe_models as mpm


def _lm(x, y, visibility=1.0):
    return NS(x=x, y=y, visibility=visibility)


def test_model_files_are_listed_and_resolved(tmp_path):
    from webserver.util.yolo import YoloService
    (tmp_path / "mediapipe").mkdir()
    for name in ("mediapipe/pose_landmarker_lite.task", "det.tflite", "best.pt", "notes.txt", ".hidden.task"):
        (tmp_path / name).write_bytes(b"x")
    service = YoloService(str(tmp_path))
    assert service.model_names() == ["best.pt", "det.tflite", "mediapipe/pose_landmarker_lite.task"]
    assert service.path_for("det.tflite").endswith("det.tflite")
    for bad in ("notes.txt", "../x.task", "missing.tflite"):
        with pytest.raises(ValueError):
            service.path_for(bad)


def test_task_bundles_are_told_apart(tmp_path):
    def bundle(name, files):
        path = tmp_path / name
        with zipfile.ZipFile(path, "w") as zf:
            for f in files:
                zf.writestr(f, b"")
        return str(path)
    assert mpm.detect_kind(bundle("p.task", ["pose_detector.tflite", "pose_landmarks_detector.tflite"])) == "pose"
    assert mpm.detect_kind(bundle("h.task", ["hand_detector.tflite", "hand_landmarks_detector.tflite"])) == "hand"
    with pytest.raises(ValueError, match="Unsupported"):
        mpm.detect_kind(bundle("f.task", ["face_detector.tflite", "face_landmarks_detector.tflite"]))
    (tmp_path / "junk.task").write_bytes(b"not a zip")
    with pytest.raises(ValueError):
        mpm.detect_kind(str(tmp_path / "junk.task"))


def test_labels_packed_in_a_tflite(tmp_path):
    path = tmp_path / "det.tflite"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("labelmap.txt", "person\nbicycle\n???\ncar\n")
    path.write_bytes(b"TFL3-model-bytes" + buffer.getvalue())  # metadata is a zip at the end
    assert mpm.tflite_labels(str(path)) == ["person", "bicycle", "???", "car"]


def test_pose_landmarks_become_a_box_and_33_keypoints():
    landmarks = [_lm(0.5, 0.2 + i * 0.01) for i in range(33)]
    landmarks[5] = _lm(0.6, 0.3, visibility=0.1)   # hidden: not labelled
    landmarks[6] = _lm(1.3, 0.3)                   # outside the picture: not labelled
    result = NS(pose_landmarks=[landmarks])
    (p,) = mpm.pose_predictions(result, 200, 100)
    assert p["class_name"] == "person" and p["type"] == "pose" and p["isbbox"]
    assert p["num_keypoints"] == 33 and len(p["keypoints"]) == 99
    assert p["keypoints"][:3] == [100.0, 20.0, 2]
    assert p["keypoints"][15:21] == [0, 0, 0, 0, 0, 0]
    assert p["keypoint_labels"][0] == "nose" and [12, 13] in p["skeleton"]
    x, y, w, h = p["bbox"]
    assert x < 100 < x + w and y < 20 and y + h > 20 + 32


def test_hands_are_named_for_an_ordinary_photo():
    hand = [_lm(0.1 + i * 0.01, 0.5) for i in range(21)]
    result = NS(hand_landmarks=[hand, hand],
                handedness=[[NS(category_name="Left", score=0.9)], [NS(category_name="Right", score=0.8)]])
    names = [p["class_name"] for p in mpm.hand_predictions(result, 100, 100)]
    # MediaPipe's answer is already the person's own hand (seen on a photo)
    assert names == ["left_hand", "right_hand"]


def test_detections_become_boxes():
    det = NS(categories=[NS(category_name="person", display_name="", index=None, score=0.87)],
             bounding_box=NS(origin_x=10, origin_y=20, width=30, height=40))
    off = NS(categories=[NS(category_name="car", display_name="", index=2, score=0.5)],
             bounding_box=NS(origin_x=500, origin_y=20, width=30, height=40))
    (p,) = mpm.detection_predictions(NS(detections=[det, off]), 100, 100)
    assert p["class_name"] == "person" and p["bbox"] == [10.0, 20.0, 30.0, 40.0] and p["score"] == 0.87


def test_segmentation_masks_become_one_annotation_per_class():
    width, height = 120, 80
    hair = np.zeros((height, width), bool)
    hair[10:30, 10:40] = True
    hair[50:70, 80:110] = True   # a second region of the same class
    noise = np.zeros((height, width), bool)
    noise[0:2, 0:2] = True       # too small to keep
    out = mpm.segmentation_predictions({"hair": (hair, 0.9), "clothes": (noise, 0.6)}, width, height)
    assert [p["class_name"] for p in out] == ["hair"]
    p = out[0]
    assert len(p["segmentation"]) == 2 and not p["isbbox"]
    assert 1000 < p["area"] < 1300
    assert p["bbox"][0] <= 10 and p["bbox"][0] + p["bbox"][2] >= 109


def test_segmenter_outputs_are_split_by_class():
    def mask(values):
        a = np.asarray(values, dtype=np.float32)
        return NS(numpy_view=lambda: a, height=a.shape[0], width=a.shape[1])
    background = mask([[0.9, 0.1], [0.2, 0.8]])
    hair = mask([[0.1, 0.9], [0.8, 0.2]])
    masks = mpm.segment_masks(NS(confidence_masks=[background, hair]), ["background", "hair"])
    assert list(masks) == ["hair"] and masks["hair"][0].tolist() == [[False, True], [True, False]]
    # a one-mask model (selfie): above the threshold is the class, "person"
    single = mpm.segment_masks(NS(confidence_masks=[mask([[0.9, 0.2]])]), ["selfie"])
    assert list(single) == ["person"] and single["person"][0].tolist() == [[True, False]]


def test_categories_take_the_models_keypoint_names(world):
    from database import CategoryModel, DatasetModel
    from webserver.util.preannotate import CategoryResolver
    dataset = DatasetModel.objects(id=world["dataset"]["id"]).first()
    resolver = CategoryResolver(dataset, create_missing=True)
    category = resolver.get("mediapipe-test-hand")
    assert resolver.ensure_keypoints(category, 21, mpm.HAND_KEYPOINTS, mpm.HAND_SKELETON)
    category = CategoryModel.objects(id=category.id).first()
    assert category.keypoint_labels[0] == "wrist" and [1, 2] in category.keypoint_edges
    assert not resolver.ensure_keypoints(category, 33, mpm.POSE_KEYPOINTS, mpm.POSE_SKELETON)
    DatasetModel.objects(id=dataset.id).update(pull__categories=category.id)
    category.delete()


def test_official_models_need_manage_models(world):
    from database import UserModel
    from webserver import app
    from webserver.util.passwords import hash_password
    UserModel.objects(username="mp_plain").delete()
    UserModel(username="mp_plain", password=hash_password("pw"), name="p", is_admin=False).save()
    plain = app.test_client()
    assert plain.post("/api/user/login", json={"username": "mp_plain", "password": "pw"}).status_code == 200
    assert plain.post("/api/model/mediapipe/install/hand_landmarker").status_code == 403
    catalog = world["client"].get("/api/model/mediapipe/catalog")
    if catalog.status_code == 200:
        names = {m["key"]: m["name"] for m in catalog.get_json()["models"]}
        assert names["hand_landmarker"] == "mediapipe/hand_landmarker.task"


def test_official_download_tries_again(tmp_path, monkeypatch):
    import http.client
    import urllib.request
    from webserver.util import yolo as yolo_module
    from webserver.util.yolo import YoloService
    monkeypatch.setattr(yolo_module, "DOWNLOAD_BACKOFF", (0, 0, 0))
    monkeypatch.setattr(mpm, "installed", lambda: True)
    monkeypatch.setattr(mpm, "detect_kind", lambda path: "segment")
    monkeypatch.setattr(mpm, "info", lambda path, name: {"name": name, "task": "segment"})
    calls = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(url, timeout=None):
        calls.append(url)
        if len(calls) < 3:
            raise http.client.RemoteDisconnected("Remote end closed connection without response")
        return Response(b"model-bytes")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    service = YoloService(str(tmp_path))
    assert service.install_official("selfie_segmenter")["name"] == "mediapipe/selfie_segmenter.tflite"
    assert len(calls) == 3
    assert (tmp_path / "mediapipe" / "selfie_segmenter.tflite").read_bytes() == b"model-bytes"
    assert [f for f in os.listdir(tmp_path / "mediapipe") if f.startswith(".")] == []

    # always failing: an error after every try, nothing left behind
    calls.clear()
    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=None: calls.append(url) or (_ for _ in ()).throw(
        http.client.RemoteDisconnected("closed")))
    with pytest.raises(ValueError, match="4 tries"):
        service.install_official("hair_segmenter")
    assert len(calls) == 4 and sorted(os.listdir(tmp_path / "mediapipe")) == ["selfie_segmenter.tflite"]
