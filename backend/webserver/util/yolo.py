"""Pre-annotation with your own Ultralytics YOLO models.

Put trained ``.pt`` files in the models folder (``MODELS_DIR`` on the host,
``/models`` in the container). Every ``.pt`` file there is offered in the UI.
Detect, OBB (rotated boxes), segment and pose models are supported; their
predictions are converted to this annotator's annotation format:

* detect  -> BBox annotation (4-corner polygon, ``isbbox``)
* obb     -> rotated box (4 corners in order, ``isrbbox`` + ``rbbox``)
* segment -> polygon annotation
* pose    -> BBox annotation with COCO ``keypoints``

Model classes are matched to the dataset's categories by name (ignoring
case). Missing categories can be created and added to the dataset.

Models are loaded lazily, cached, and run one prediction at a time per
server (a single GPU is shared by all users).

MediaPipe models (``.task`` / ``.tflite``) live in the same folder and go
through the same service: see :mod:`webserver.util.mediapipe_models`.
"""
import logging
import os
import threading
import time
from collections import OrderedDict

import numpy as np

from config import Config
from geometry import polygon_to_rbbox
# COCO person keypoints / skeleton (17-keypoint pose models)
from geometry.yolo_format import COCO_KEYPOINTS, COCO_SKELETON
from . import mediapipe_models

logger = logging.getLogger('gunicorn.error')

# Keypoints whose confidence is below this are stored as "not labelled".
KEYPOINT_MIN_CONF = 0.5
# official MediaPipe models: tries per download, and the pauses between them
DOWNLOAD_ATTEMPTS = 4
DOWNLOAD_BACKOFF = (1, 3, 6)


def _polygon_area(flat):
    pts = np.asarray(flat, dtype=float).reshape(-1, 2)
    x, y = pts[:, 0], pts[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def _bbox_of(flat):
    pts = np.asarray(flat, dtype=float).reshape(-1, 2)
    x1, y1 = pts.min(axis=0)
    x2, y2 = pts.max(axis=0)
    return [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]


def _box_polygon(x1, y1, x2, y2):
    return [x1, y1, x2, y1, x2, y2, x1, y2]


def _round(values, digits=2):
    return [round(float(v), digits) for v in values]


def result_to_predictions(result, names):
    """Convert one ultralytics ``Results`` object to annotation dicts."""
    predictions = []

    def base(cls, score):
        cls = int(cls)
        return {"class_id": cls, "class_name": str(names.get(cls, cls)),
                "score": round(float(score), 4)}

    # Rotated boxes
    obb = getattr(result, "obb", None)
    if obb is not None and len(obb):
        corners = obb.xyxyxyxy.cpu().numpy()
        for pts, cls, score in zip(corners, obb.cls.cpu().numpy(), obb.conf.cpu().numpy()):
            polygon = _round(pts.reshape(-1))
            p = base(cls, score)
            p.update({
                "type": "obb",
                "segmentation": [polygon],
                "isrbbox": True,
                "rbbox": [round(v, 2) for v in polygon_to_rbbox(polygon)],
                "bbox": _bbox_of(polygon),
                "area": _polygon_area(polygon),
            })
            predictions.append(p)
        return predictions

    boxes = getattr(result, "boxes", None)
    if boxes is None or not len(boxes):
        return predictions

    xyxy = boxes.xyxy.cpu().numpy()
    classes = boxes.cls.cpu().numpy()
    scores = boxes.conf.cpu().numpy()

    masks = getattr(result, "masks", None)
    mask_polygons = masks.xy if masks is not None else None

    keypoints = getattr(result, "keypoints", None)
    kp_data = keypoints.data.cpu().numpy() if keypoints is not None else None

    for i, ((x1, y1, x2, y2), cls, score) in enumerate(zip(xyxy, classes, scores)):
        p = base(cls, score)
        box = _round(_box_polygon(x1, y1, x2, y2))

        if mask_polygons is not None:
            pts = np.asarray(mask_polygons[i])
            if len(pts) >= 3:
                polygon = _round(pts.reshape(-1))
                p.update({
                    "type": "segment",
                    "segmentation": [polygon],
                    "isbbox": False,
                    "bbox": _bbox_of(polygon),
                    "area": _polygon_area(polygon),
                })
                predictions.append(p)
                continue
            # degenerate mask: fall back to the box

        p.update({
            "type": "pose" if kp_data is not None else "detect",
            "segmentation": [box],
            "isbbox": True,
            "bbox": _bbox_of(box),
            "area": _polygon_area(box),
        })

        if kp_data is not None:
            flat = []
            for kp in kp_data[i]:
                x, y = float(kp[0]), float(kp[1])
                conf = float(kp[2]) if len(kp) > 2 else 1.0
                if conf >= KEYPOINT_MIN_CONF and (x > 0 or y > 0):
                    flat += [round(x, 2), round(y, 2), 2]
                else:
                    flat += [0, 0, 0]
            p["keypoints"] = flat
            p["num_keypoints"] = int(len(kp_data[i]))

        predictions.append(p)

    return predictions


class YoloService:

    def __init__(self, directory, device="auto", cache_size=3):
        self.directory = directory
        self.device = device
        self.cache_size = cache_size
        self._models = OrderedDict()   # name -> (mtime, YOLO)
        self._load_lock = threading.Lock()
        self._predict_lock = threading.Lock()
        self._error = None
        self._info = {}                # name -> (mtime, info): listing must not load every model

    # ------------------------------------------------------------ discovery
    @property
    def ultralytics_installed(self):
        try:
            import ultralytics  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def mediapipe_installed(self):
        return mediapipe_models.installed()

    @property
    def installed(self):
        """Some model support (Ultralytics YOLO or MediaPipe) is there."""
        return self.ultralytics_installed or self.mediapipe_installed

    def model_names(self):
        """Relative paths of all ``.pt`` (YOLO) and ``.task`` / ``.tflite``
        (MediaPipe) files in the models folder."""
        if not os.path.isdir(self.directory):
            return []
        names = []
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                # SAM 2 checkpoints (sam2*.pt) live here too but are not YOLO models
                if f.startswith('.') or f.lower().startswith('sam2'):
                    continue
                if f.lower().endswith(('.pt',) + mediapipe_models.EXTENSIONS):
                    full = os.path.join(root, f)
                    names.append(os.path.relpath(full, self.directory))
        return sorted(names)

    def path_for(self, name):
        """Absolute path of a model, refusing anything outside the folder."""
        if not name or not name.lower().endswith(('.pt',) + mediapipe_models.EXTENSIONS):
            raise ValueError("Unknown model")
        base = os.path.realpath(self.directory)
        path = os.path.realpath(os.path.join(base, name))
        if os.path.commonpath([base, path]) != base or not os.path.isfile(path):
            raise ValueError("Unknown model")
        return path

    # ------------------------------------------------------------ loading
    def _resolve_device(self):
        if self.device != "auto":
            return self.device
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def load(self, name):
        path = self.path_for(name)
        mtime = os.path.getmtime(path)
        with self._load_lock:
            cached = self._models.get(name)
            if cached and cached[0] == mtime:
                self._models.move_to_end(name)
                return cached[1]

            from ultralytics import YOLO
            logger.info(f"Loading YOLO model {name}")
            model = YOLO(path)
            self._models[name] = (mtime, model)
            self._models.move_to_end(name)
            while len(self._models) > self.cache_size:
                self._models.popitem(last=False)
            return model

    def info(self, name):
        if mediapipe_models.is_mediapipe(name):
            if not self.mediapipe_installed:
                raise ValueError("MediaPipe is not installed on this server")
            return mediapipe_models.info(self.path_for(name), name)
        model = self.load(name)
        names = {int(k): str(v) for k, v in dict(model.names).items()}
        kpt_shape = None
        try:
            kpt_shape = list(model.model.yaml.get("kpt_shape") or []) or None
        except Exception:
            pass
        return {
            "name": name,
            "task": model.task,
            "classes": [names[k] for k in sorted(names)],
            "kpt_shape": kpt_shape,
            "framework": "ultralytics",
        }

    def cached_info(self, name):
        """info() remembered per file version."""
        mtime = os.path.getmtime(self.path_for(name))
        cached = self._info.get(name)
        if cached and cached[0] == mtime:
            return cached[1]
        info = self.info(name)
        self._info[name] = (mtime, info)
        return info

    def list(self):
        models = []
        for name in self.model_names():
            entry = {"name": name}
            try:
                entry.update(self.cached_info(name))
                entry["size"] = os.path.getsize(self.path_for(name))
                entry["modified"] = os.path.getmtime(self.path_for(name))
            except Exception as e:
                logger.warning(f"Could not load model {name}: {e}")
                entry["error"] = str(e)
            models.append(entry)
        return models

    def status(self):
        return {
            "installed": self.installed,
            "directory": self.directory,
            "count": len(self.model_names()) if self.installed else 0,
        }

    # ------------------------------------------------------------ manage
    def save_upload(self, file_storage, overwrite=False):
        """Store an uploaded .pt file and check that it loads.

        Returns the model info. Raises ValueError (bad name/file) or
        FileExistsError (name taken and not ``overwrite``).
        """
        from werkzeug.utils import secure_filename

        name = secure_filename(file_storage.filename or "")
        if mediapipe_models.is_mediapipe(name) and os.path.splitext(name)[0]:
            return self._save_mediapipe(file_storage.save, name, overwrite)
        if not name.lower().endswith('.pt') or name.lower() == '.pt':
            raise ValueError("Only .pt (YOLO) or .task / .tflite (MediaPipe) files can be uploaded")
        if not self.ultralytics_installed:
            raise ValueError("YOLO support (Ultralytics) is not installed on this server")

        os.makedirs(self.directory, exist_ok=True)
        path = os.path.join(self.directory, name)
        if os.path.exists(path) and not overwrite:
            raise FileExistsError(name)

        # hidden (not listed) but still a .pt file, so ultralytics loads it now
        tmp = os.path.join(self.directory, f".uploading-{os.getpid()}-{threading.get_ident()}-{name}")
        file_storage.save(tmp)
        try:
            from ultralytics import YOLO
            model = YOLO(tmp)
            dict(model.names)  # make sure the weights really loaded
            if model.task not in ("detect", "obb", "segment", "pose"):
                raise ValueError(f"Unsupported model type: {model.task}")
        except ValueError:
            os.remove(tmp)
            raise
        except Exception as e:
            os.remove(tmp)
            raise ValueError(f"Not a YOLO model that can be loaded: {e}")

        os.replace(tmp, path)
        with self._load_lock:
            self._models.pop(name, None)
        self._info.pop(name, None)
        return self.info(name)

    def _save_mediapipe(self, write, name, overwrite):
        """Store a MediaPipe model (``write(tmp_path)`` puts the file there)
        under ``name`` (may be in a subfolder) once it is known to work."""
        if not self.mediapipe_installed:
            raise ValueError("MediaPipe is not installed on this server")
        path = os.path.join(self.directory, name)
        if os.path.exists(path) and not overwrite:
            raise FileExistsError(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # hidden (not listed) with the same extension, checked before it is used
        tmp = os.path.join(os.path.dirname(path),
                           f".uploading-{os.getpid()}-{threading.get_ident()}-{os.path.basename(name)}")
        try:
            write(tmp)
            mediapipe_models.detect_kind(tmp)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Could not store {name}: {e}")
        os.replace(tmp, path)
        mediapipe_models.runner.forget(path)
        self._info.pop(name, None)
        return self.info(name)

    def install_official(self, key, overwrite=False):
        """Download one of MediaPipe's official models into the folder."""
        import urllib.request
        entry = mediapipe_models.catalog_entry(key)
        if entry is None:
            raise ValueError("Unknown official model")
        name = mediapipe_models.catalog_name(entry)

        def fetch(tmp):
            limit = 100 * 1024 * 1024
            with urllib.request.urlopen(entry["url"], timeout=60) as response, open(tmp, "wb") as out:
                size = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("Download too large")
                    out.write(chunk)

        def write(tmp):
            # flaky networks drop connections now and then: try again
            for attempt in range(DOWNLOAD_ATTEMPTS):
                try:
                    return fetch(tmp)
                except ValueError:
                    raise
                except Exception as e:  # URLError, RemoteDisconnected, timeouts, resets
                    if attempt == DOWNLOAD_ATTEMPTS - 1:
                        raise OSError(f"download failed after {DOWNLOAD_ATTEMPTS} tries: {e}")
                    logger.warning(f"Downloading {key} failed ({e}), trying again")
                    time.sleep(DOWNLOAD_BACKOFF[attempt])
        return self._save_mediapipe(write, name, overwrite)

    def delete(self, name):
        path = self.path_for(name)
        if mediapipe_models.is_mediapipe(name):
            mediapipe_models.runner.forget(path)
        os.remove(path)
        with self._load_lock:
            self._models.pop(name, None)
        self._info.pop(name, None)

    def device_name(self):
        device = self._resolve_device()
        if device.startswith("cuda"):
            try:
                import torch
                return f"{device} ({torch.cuda.get_device_name(0)})"
            except Exception:
                pass
        return device

    # ------------------------------------------------------------ predict
    def predict(self, name, image_path, conf=0.25, iou=0.7, imgsz=None):
        if mediapipe_models.is_mediapipe(name):
            path = self.path_for(name)
            with self._predict_lock:
                return mediapipe_models.runner.predict(path, image_path, conf=conf)
        model = self.load(name)
        names = {int(k): str(v) for k, v in dict(model.names).items()}
        kwargs = {"conf": float(conf), "iou": float(iou), "verbose": False,
                  "device": self._resolve_device()}
        if imgsz:
            kwargs["imgsz"] = int(imgsz)
        with self._predict_lock:
            result = model.predict(image_path, **kwargs)[0]
        return result_to_predictions(result, names)


yolo = YoloService(
    Config.MODELS_DIRECTORY,
    device=Config.YOLO_DEVICE,
)
