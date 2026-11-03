"""Segment Anything (SAM 2.1, or SAM 1) integration.

SAM 2.1 checkpoints (sam2.1_*.pt) run through Ultralytics, the original SAM
checkpoints (sam_vit_*.pth) through Meta's segment-anything package. When
the configured checkpoint is missing the best one in the models folder is
used, so older installs keep working until SAM 2.1 is downloaded.

The model is loaded lazily on first use so the webserver starts quickly and
still runs when PyTorch / the checkpoint are not installed.  Image embeddings
are the expensive part of SAM, so the embeddings of the most recently used
images are cached: once an image is embedded, every extra click is cheap.
"""
import logging
import os
import threading
from collections import OrderedDict

import cv2
import numpy as np
from PIL import Image

from config import Config

logger = logging.getLogger('gunicorn.error')


def mask_to_polygons(mask, min_area=10, epsilon=1.0):
    """Convert a binary mask into COCO polygon segmentation lists."""
    mask = np.ascontiguousarray(mask.astype(np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    polygons = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        if epsilon > 0:
            contour = cv2.approxPolyDP(contour, epsilon, True)
        if len(contour) < 3:
            continue
        polygons.append(contour.reshape(-1).astype(float).tolist())
    return polygons


# Checkpoints looked for in the models folder when the configured one is
# missing, best first. SAM 2.1 runs through Ultralytics, SAM 1 through
# Meta's segment-anything package.
KNOWN_CHECKPOINTS = [
    "sam2.1_b.pt", "sam2.1_l.pt", "sam2.1_s.pt", "sam2.1_t.pt",
    "sam2_b.pt", "sam2_l.pt", "sam2_s.pt", "sam2_t.pt",
    "sam_vit_b_01ec64.pth", "sam_vit_l_0b3195.pth", "sam_vit_h_4b8939.pth",
]
SAM1_TYPES = {"sam_vit_b": "vit_b", "sam_vit_l": "vit_l", "sam_vit_h": "vit_h"}


def is_sam2(path):
    return os.path.basename(path or "").lower().startswith("sam2")


class SamService:

    def __init__(self, checkpoint, model_type, device, cache_size=4, models_dir=None):
        self.configured = checkpoint
        self.model_type = model_type
        self.device = device
        self.cache_size = cache_size
        self.models_dir = models_dir or os.path.dirname(checkpoint or "") or "/models"

        self._lock = threading.Lock()
        self._predictor = None
        self._backend = None
        self._error = None
        self._cache = OrderedDict()  # image_id -> features
        self._current = None         # image_id currently set on predictor

    @property
    def checkpoint(self):
        """The configured checkpoint, or the best one found in the models folder."""
        if self.configured and os.path.isfile(self.configured):
            return self.configured
        for name in KNOWN_CHECKPOINTS:
            path = os.path.join(self.models_dir, name)
            if os.path.isfile(path):
                return path
        return self.configured

    @property
    def model_name(self):
        name = os.path.basename(self.checkpoint or "")
        if is_sam2(name):
            return "SAM " + name.split("_")[0][3:] + " " + os.path.splitext(name)[0].split("_")[-1]
        for prefix, kind in SAM1_TYPES.items():
            if name.startswith(prefix):
                return f"SAM {kind}"
        return name

    @property
    def available(self):
        checkpoint = self.checkpoint
        if not checkpoint or not os.path.isfile(checkpoint):
            return False
        try:
            import torch  # noqa: F401
            if is_sam2(checkpoint):
                import ultralytics  # noqa: F401
            else:
                import segment_anything  # noqa: F401
        except ImportError:
            return False
        return self._error is None

    def status(self):
        return {
            "available": self.available,
            "loaded": self._predictor is not None,
            "model_type": self.model_name,
            "checkpoint": os.path.basename(self.checkpoint or ""),
            "error": self._error,
        }

    def _device(self):
        import torch
        device = self.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def _load(self):
        if self._predictor is not None:
            return self._predictor

        checkpoint = self.checkpoint
        device = self._device()
        logger.info(f"Loading {self.model_name} from {checkpoint} on {device}")
        try:
            if is_sam2(checkpoint):
                from ultralytics.models.sam import SAM2Predictor
                self._predictor = SAM2Predictor(overrides=dict(
                    conf=0.0, task="segment", mode="predict", imgsz=1024, model=checkpoint,
                    device="0" if device == "cuda" else device, verbose=False, save=False))
                self._predictor.setup_model()
                self._backend = "sam2"
            else:
                from segment_anything import sam_model_registry, SamPredictor
                name = os.path.basename(checkpoint)
                model_type = next((t for p, t in SAM1_TYPES.items() if name.startswith(p)), self.model_type)
                model = sam_model_registry[model_type](checkpoint=checkpoint)
                model.to(device=device)
                self._predictor = SamPredictor(model)
                self._backend = "sam1"
        except Exception as e:  # pragma: no cover - depends on weights
            self._error = str(e)
            raise
        return self._predictor

    @staticmethod
    def _to(features, device):
        if isinstance(features, dict):
            return {k: SamService._to(v, device) for k, v in features.items()}
        if isinstance(features, (list, tuple)):
            return [SamService._to(v, device) for v in features]
        return features.to(device) if hasattr(features, "to") else features

    def _set_image(self, predictor, image_id, path):
        if self._current == image_id:
            return

        cached = self._cache.get(image_id)
        if self._backend == "sam2":
            image = cv2.imread(path)
            if image is None:  # formats OpenCV cannot read
                image = np.ascontiguousarray(np.array(Image.open(path).convert("RGB"))[..., ::-1])
            if cached is not None:
                self._cache.move_to_end(image_id)
                predictor.setup_source(image)
                predictor.features = self._to(cached, predictor.device)
            else:
                predictor.set_image(image)
                # kept on the CPU: SAM 2 features are ~16 MB per image
                self._cache[image_id] = self._to(predictor.features, "cpu")
        elif cached is not None:
            self._cache.move_to_end(image_id)
            (predictor.features, predictor.original_size,
             predictor.input_size) = cached
            predictor.is_image_set = True
        else:
            image = np.array(Image.open(path).convert("RGB"))
            predictor.set_image(image)
            self._cache[image_id] = (
                predictor.features, predictor.original_size, predictor.input_size
            )
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        self._current = image_id

    def prepare(self, image_id, path):
        """Compute (and cache) the image embedding ahead of the first click."""
        with self._lock:
            predictor = self._load()
            self._set_image(predictor, image_id, path)

    def prepare_async(self, image_id, path):
        def run():
            try:
                self.prepare(image_id, path)
            except Exception:  # pragma: no cover - logged for the operator
                logger.exception("SAM prepare failed")
        threading.Thread(target=run, daemon=True).start()

    def predict(self, image_id, path, points=None, labels=None, box=None,
                multimask=False):
        """Return (polygons, score, area) for the given prompts.

        points: [[x, y], ...] in image pixel coordinates
        labels: [1|0, ...]  1 = foreground, 0 = background
        box:    [x1, y1, x2, y2] in image pixel coordinates
        """
        with self._lock:
            predictor = self._load()
            self._set_image(predictor, image_id, path)

            labels = list(labels) if labels else [1] * len(points or [])
            # With a single point SAM is ambiguous; ask for 3 masks and keep best
            multimask = multimask or (box is None and points is not None and len(points) == 1)

            if self._backend == "sam2":
                kwargs = {"multimask_output": multimask}
                if points:
                    kwargs["points"] = [[list(map(float, p)) for p in points]]
                    kwargs["labels"] = [[int(v) for v in labels]]
                if box:
                    kwargs["bboxes"] = [list(map(float, box))]
                result = predictor(**kwargs)[0]
                if result.masks is None or not len(result.masks):
                    return [], 0.0, 0
                scores = result.boxes.conf.cpu().numpy()
                masks = result.masks.data.cpu().numpy() > 0.5
            else:
                point_coords = np.array(points, dtype=np.float32) if points else None
                point_labels = np.array(labels, dtype=np.int32) if points else None
                box_arr = np.array(box, dtype=np.float32) if box else None
                masks, scores, _ = predictor.predict(
                    point_coords=point_coords,
                    point_labels=point_labels,
                    box=box_arr,
                    multimask_output=multimask,
                )

        best = int(np.argmax(scores))
        mask = masks[best]
        return mask_to_polygons(mask), float(scores[best]), int(mask.sum())


sam = SamService(
    checkpoint=Config.SAM_CHECKPOINT,
    model_type=Config.SAM_MODEL_TYPE,
    device=Config.SAM_DEVICE,
    cache_size=Config.SAM_CACHE_SIZE,
    models_dir=Config.MODELS_DIRECTORY,
)
