"""Pre-annotation with MediaPipe models (``.task`` / ``.tflite`` files).

They live in the models folder next to the YOLO ``.pt`` files and go
through the same pre-annotation (one image, a whole dataset); predictions
use the same dicts as :func:`webserver.util.yolo.result_to_predictions`:

* Pose Landmarker (.task)   -> "person": a box + 33 keypoints
* Hand Landmarker (.task)   -> "left_hand" / "right_hand": a box + 21 keypoints
* Object Detector (.tflite) -> a box per object (class names from the model)
* Image Segmenter (.tflite) -> one polygon annotation per class found

Which kind a file is comes from its content: a ``.task`` bundle names the
models inside it, a ``.tflite`` is tried as an object detector and then as a
segmenter (a segmenter also loads a detector's file, not the other way).

MediaPipe runs on the CPU here (its Python GPU support is limited on Linux).
"""
import logging
import os
import threading
import zipfile
from collections import OrderedDict

import numpy as np

logger = logging.getLogger('gunicorn.error')

EXTENSIONS = ('.task', '.tflite')
# official models (Google), offered for download on the Models page
_BASE = "https://storage.googleapis.com/mediapipe-models"
CATALOG = [
    {"key": "pose_landmarker_lite", "task": "pose", "size_mb": 5.6,
     "url": f"{_BASE}/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"},
    {"key": "pose_landmarker_full", "task": "pose", "size_mb": 9.0,
     "url": f"{_BASE}/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"},
    {"key": "pose_landmarker_heavy", "task": "pose", "size_mb": 30,
     "url": f"{_BASE}/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"},
    {"key": "hand_landmarker", "task": "hand", "size_mb": 7.5,
     "url": f"{_BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"},
    {"key": "efficientdet_lite0", "task": "detect", "size_mb": 7.0,
     "url": f"{_BASE}/object_detector/efficientdet_lite0/float16/latest/efficientdet_lite0.tflite"},
    {"key": "efficientdet_lite2", "task": "detect", "size_mb": 12,
     "url": f"{_BASE}/object_detector/efficientdet_lite2/float16/latest/efficientdet_lite2.tflite"},
    {"key": "ssd_mobilenet_v2", "task": "detect", "size_mb": 5.7,
     "url": f"{_BASE}/object_detector/ssd_mobilenet_v2/float16/latest/ssd_mobilenet_v2.tflite"},
    {"key": "selfie_segmenter", "task": "segment", "size_mb": 0.3,
     "url": f"{_BASE}/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"},
    {"key": "selfie_multiclass_256x256", "task": "segment", "size_mb": 16,
     "url": f"{_BASE}/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"},
    {"key": "hair_segmenter", "task": "segment", "size_mb": 0.8,
     "url": f"{_BASE}/image_segmenter/hair_segmenter/float32/latest/hair_segmenter.tflite"},
    {"key": "deeplab_v3", "task": "segment", "size_mb": 2.7,
     "url": f"{_BASE}/image_segmenter/deeplab_v3/float32/latest/deeplab_v3.tflite"},
]
CATALOG_FOLDER = "mediapipe"  # inside the models folder

POSE_KEYPOINTS = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye",
    "right_eye_outer", "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_pinky",
    "right_pinky", "left_index", "right_index", "left_thumb", "right_thumb", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]
# MediaPipe's pose connections, 1-based like COCO's skeleton
POSE_SKELETON = [[a + 1, b + 1] for a, b in (
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10), (11, 12), (11, 13),
    (13, 15), (15, 17), (15, 19), (15, 21), (17, 19), (12, 14), (14, 16), (16, 18), (16, 20),
    (16, 22), (18, 20), (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32))]
HAND_KEYPOINTS = [
    "wrist", "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip", "index_finger_mcp",
    "index_finger_pip", "index_finger_dip", "index_finger_tip", "middle_finger_mcp",
    "middle_finger_pip", "middle_finger_dip", "middle_finger_tip", "ring_finger_mcp",
    "ring_finger_pip", "ring_finger_dip", "ring_finger_tip", "pinky_mcp", "pinky_pip",
    "pinky_dip", "pinky_tip",
]
HAND_SKELETON = [[a + 1, b + 1] for a, b in (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
    (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20))]

# a pose keypoint whose visibility is below this is stored as "not labelled"
VISIBILITY_MIN = 0.5
# segmenter: pixels of a one-mask model (selfie) above this are the class
MASK_THRESHOLD = 0.5
# segmenter: regions smaller than this share of the image are noise
MIN_REGION = 0.0005


def installed():
    try:
        import mediapipe  # noqa: F401
        return True
    except Exception:  # ImportError, or a missing system library (libEGL)
        return False


def is_mediapipe(name):
    return str(name).lower().endswith(EXTENSIONS)


def catalog_entry(key):
    for entry in CATALOG:
        if entry["key"] == key:
            return entry
    return None


def catalog_name(entry):
    """Where an official model is stored, relative to the models folder."""
    return f"{CATALOG_FOLDER}/{os.path.basename(entry['url'])}"


# ---------------------------------------------------------------- reading

def bundled_files(path):
    """Names inside a .task bundle (or a .tflite with metadata: labels)."""
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return []


def tflite_labels(path):
    """The label map packed into a .tflite (models with metadata)."""
    try:
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name.lower().endswith('.txt') and 'label' in name.lower():
                    lines = zf.read(name).decode('utf-8', 'replace').splitlines()
                    return [line.strip() for line in lines]
    except (zipfile.BadZipFile, OSError):
        pass
    return []


def _vision():
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision
    return mp_tasks, vision


def _create(kind, path, conf=0.5):
    """A MediaPipe task for the file (raises if it is not that kind)."""
    mp_tasks, vision = _vision()
    base = mp_tasks.BaseOptions(model_asset_path=path)
    conf = float(conf)
    if kind == "pose":
        return vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=base, num_poses=20, min_pose_detection_confidence=conf,
            min_pose_presence_confidence=conf))
    if kind == "hand":
        return vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=base, num_hands=20, min_hand_detection_confidence=conf,
            min_hand_presence_confidence=conf))
    if kind == "detect":
        return vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
            base_options=base, score_threshold=conf, max_results=-1))
    if kind == "segment":
        return vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=base, output_confidence_masks=True, output_category_mask=True))
    raise ValueError(f"Unknown MediaPipe task: {kind}")


def detect_kind(path):
    """'pose', 'hand', 'detect' or 'segment'; ValueError if not supported."""
    if path.lower().endswith('.task'):
        names = {os.path.basename(n) for n in bundled_files(path)}
        if 'pose_landmarks_detector.tflite' in names:
            return "pose"
        if 'hand_landmarks_detector.tflite' in names:
            return "hand"  # a gesture recognizer bundle has one too, inside
        if names:
            raise ValueError("Unsupported MediaPipe bundle (pose and hand landmarkers are supported): "
                             + ", ".join(sorted(names))[:200])
        raise ValueError("Not a MediaPipe .task bundle")
    errors = []
    for kind in ("detect", "segment"):  # a segmenter loads a detector's file too
        try:
            task = _create(kind, path)
            task.close()
            return kind
        except Exception as e:
            errors.append(f"{kind}: {e}")
    raise ValueError("Not a MediaPipe object detector or image segmenter (" + "; ".join(errors)[:300] + ")")


def info(path, name):
    kind = detect_kind(path)
    out = {"name": name, "framework": "mediapipe", "kpt_shape": None}
    if kind == "pose":
        out.update(task="pose", classes=["person"], kpt_shape=[len(POSE_KEYPOINTS), 3])
    elif kind == "hand":
        out.update(task="pose", classes=["left_hand", "right_hand"], kpt_shape=[len(HAND_KEYPOINTS), 3])
    elif kind == "detect":
        out.update(task="detect", classes=[c for c in tflite_labels(path) if c and c != '???'])
    else:
        task = _create("segment", path)
        try:
            labels = list(getattr(task, "labels", None) or [])
        finally:
            task.close()
        out.update(task="segment", classes=_segment_classes(labels))
    out["mediapipe_task"] = kind
    return out


def _segment_classes(labels):
    if len(labels) <= 1:
        return [_single_mask_name(labels)]
    return [label for label in labels if label.lower() != 'background']


def _single_mask_name(labels):
    name = labels[0] if labels else "foreground"
    return "person" if name.lower() == "selfie" else name


# ---------------------------------------------------------------- predictions

def _load_image(image_path):
    """RGB pixels as stored (no EXIF rotation: annotations use this layout)."""
    import mediapipe as mp
    from PIL import Image
    with Image.open(image_path) as pil_image:
        pixels = np.ascontiguousarray(np.asarray(pil_image.convert("RGB")))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels), pixels.shape[1], pixels.shape[0]


def _box(x1, y1, x2, y2):
    from .yolo import _box_polygon, _round
    return _round(_box_polygon(x1, y1, x2, y2))


def landmarks_to_prediction(landmarks, width, height, class_name, score, use_visibility):
    """Normalised landmarks -> a box around the ones in the image + keypoints."""
    from .yolo import _bbox_of, _polygon_area
    flat, xs, ys = [], [], []
    for lm in landmarks:
        x, y = float(lm.x) * width, float(lm.y) * height
        inside = 0 <= x < width and 0 <= y < height
        visible = not use_visibility or float(getattr(lm, "visibility", 0) or 0) >= VISIBILITY_MIN
        if inside and visible:
            flat += [round(x, 2), round(y, 2), 2]
            xs.append(x)
            ys.append(y)
        else:
            flat += [0, 0, 0]
    if not xs:
        return None
    # a little room around the outermost points
    pad_x, pad_y = (max(xs) - min(xs)) * 0.05 + 2, (max(ys) - min(ys)) * 0.05 + 2
    box = _box(max(min(xs) - pad_x, 0), max(min(ys) - pad_y, 0),
               min(max(xs) + pad_x, width - 1), min(max(ys) + pad_y, height - 1))
    return {"class_id": 0, "class_name": class_name, "score": round(float(score), 4),
            "type": "pose", "segmentation": [box], "isbbox": True, "bbox": _bbox_of(box),
            "area": _polygon_area(box), "keypoints": flat, "num_keypoints": len(landmarks)}


def pose_predictions(result, width, height):
    out = []
    for landmarks in result.pose_landmarks or []:
        score = np.mean([float(getattr(lm, "visibility", 0) or 0) for lm in landmarks]) if landmarks else 0
        p = landmarks_to_prediction(landmarks, width, height, "person", score, use_visibility=True)
        if p:
            p.update(keypoint_labels=POSE_KEYPOINTS, skeleton=POSE_SKELETON)
            out.append(p)
    return out


def hand_predictions(result, width, height):
    out = []
    handedness = result.handedness or []
    for i, landmarks in enumerate(result.hand_landmarks or []):
        best = handedness[i][0] if i < len(handedness) and handedness[i] else None
        # the person's own left / right in an ordinary photo (checked on a
        # picture: no swap needed, whatever older MediaPipe docs said)
        side = {"left": "left_hand", "right": "right_hand"}.get(
            (best.category_name or "").lower() if best else "", "hand")
        p = landmarks_to_prediction(landmarks, width, height, side, best.score if best else 1.0,
                                    use_visibility=False)
        if p:
            p.update(keypoint_labels=HAND_KEYPOINTS, skeleton=HAND_SKELETON)
            out.append(p)
    return out


def detection_predictions(result, width, height):
    from .yolo import _bbox_of, _polygon_area
    out = []
    for det in result.detections or []:
        if not det.categories:
            continue
        cat = det.categories[0]
        b = det.bounding_box
        x1, y1 = max(float(b.origin_x), 0), max(float(b.origin_y), 0)
        x2, y2 = min(float(b.origin_x + b.width), width - 1), min(float(b.origin_y + b.height), height - 1)
        if x2 <= x1 or y2 <= y1:
            continue
        name = cat.category_name or cat.display_name or f"class {cat.index if cat.index is not None else 0}"
        box = _box(x1, y1, x2, y2)
        out.append({"class_id": int(cat.index or 0), "class_name": str(name), "score": round(float(cat.score), 4),
                    "type": "detect", "segmentation": [box], "isbbox": True, "bbox": _bbox_of(box),
                    "area": _polygon_area(box)})
    return out


def mask_polygons(mask, min_area):
    """Outer outlines of the regions of a boolean mask (flat [x, y, ...])."""
    import cv2
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polygons = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        epsilon = max(1.0, 0.002 * cv2.arcLength(contour, True))
        points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        if len(points) >= 3:
            polygons.append([round(float(v), 2) for v in points.reshape(-1)])
    return polygons


def segmentation_predictions(class_masks, width, height):
    """{class name: (boolean mask, score)} -> one annotation per class."""
    from .yolo import _polygon_area
    min_area = max(16.0, MIN_REGION * width * height)
    out = []
    for i, (name, (mask, score)) in enumerate(class_masks.items()):
        polygons = mask_polygons(mask, min_area)
        if not polygons:
            continue
        xs = [v for poly in polygons for v in poly[0::2]]
        ys = [v for poly in polygons for v in poly[1::2]]
        bbox = [round(min(xs), 2), round(min(ys), 2), round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)]
        out.append({"class_id": i, "class_name": name, "score": round(float(score), 4), "type": "segment",
                    "segmentation": polygons, "isbbox": False, "bbox": bbox,
                    "area": sum(_polygon_area(p) for p in polygons)})
    return out


def segment_masks(result, labels):
    """The segmenter's output as {class name: (mask, mean confidence)}."""
    confidence = [m.numpy_view().reshape(m.height, m.width) for m in (result.confidence_masks or [])]
    if not confidence:
        return {}
    if len(confidence) == 1:
        mask = confidence[0] > MASK_THRESHOLD
        score = float(confidence[0][mask].mean()) if mask.any() else 0.0
        return {_single_mask_name(labels): (mask, score)}
    stack = np.stack(confidence)
    winner = stack.argmax(axis=0)
    out = {}
    for i in range(len(confidence)):
        name = labels[i] if i < len(labels) and labels[i] else f"class {i}"
        if name.lower() == 'background':
            continue
        mask = winner == i
        if mask.any():
            out[name] = (mask, float(stack[i][mask].mean()))
    return out


class MediaPipeRunner:
    """Loaded MediaPipe tasks (per file version and confidence), LRU."""

    def __init__(self, cache_size=4):
        self.cache_size = cache_size
        self._tasks = OrderedDict()
        self._kinds = {}
        self._lock = threading.Lock()

    def kind(self, path):
        mtime = os.path.getmtime(path)
        cached = self._kinds.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        kind = detect_kind(path)
        self._kinds[path] = (mtime, kind)
        return kind

    def _task(self, path, kind, conf):
        key = (path, os.path.getmtime(path), kind, round(float(conf), 3))
        with self._lock:
            if key in self._tasks:
                self._tasks.move_to_end(key)
                return self._tasks[key]
            # an older version of the file: drop it
            for old in [k for k in self._tasks if k[0] == path and k[1] != key[1]]:
                self._tasks.pop(old).close()
            task = _create(kind, path, conf)
            self._tasks[key] = task
            while len(self._tasks) > self.cache_size:
                self._tasks.popitem(last=False)[1].close()
            return task

    def forget(self, path):
        with self._lock:
            for key in [k for k in self._tasks if k[0] == path]:
                self._tasks.pop(key).close()
        self._kinds.pop(path, None)

    def predict(self, path, image_path, conf=0.25):
        kind = self.kind(path)
        image, width, height = _load_image(image_path)
        if kind == "segment":
            task = self._task(path, kind, 0.5)  # confidence does not change a segmenter
            result = task.segment(image)
            labels = list(getattr(task, "labels", None) or [])
            return segmentation_predictions(segment_masks(result, labels), width, height)
        task = self._task(path, kind, conf)
        if kind == "pose":
            return pose_predictions(task.detect(image), width, height)
        if kind == "hand":
            return hand_predictions(task.detect(image), width, height)
        return detection_predictions(task.detect(image), width, height)


runner = MediaPipeRunner()
