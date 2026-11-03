"""What the installed Ultralytics can train: model names (.pt pretrained
weights it can download, .yaml architectures to train from scratch) by
family and task, and the training arguments with their defaults. The
trainer publishes this, so the page offers exactly what it can run."""
import os
import re

# task of a model name (suffix); names with other suffixes are not offered
_SUFFIX_TASK = {"seg": "segment", "pose": "pose", "obb": "obb", "cls": "classify"}
# not trainable here (other model kinds, special datasets / inputs)
_SKIP = re.compile(r"sam|world|yoloe|nas|distill|depth|objv1|ade20k|grayscale|-sem\b|-sem\.|-sem-|semantic")

FAMILIES = [
    # key, label, name pattern
    ("yolo26", "YOLO26", r"^yolo26"),
    ("yolo12", "YOLO12", r"^yolo12"),
    ("yolo11", "YOLO11", r"^yolo11"),
    ("yolov10", "YOLOv10", r"^yolov10"),
    ("yolov9", "YOLOv9", r"^yolov9"),
    ("yolov8", "YOLOv8", r"^yolov8"),
    ("yolov6", "YOLOv6", r"^yolov6"),
    ("yolov5", "YOLOv5u", r"^yolov5"),
    ("yolov3", "YOLOv3u", r"^yolov3"),
    ("rtdetr", "RT-DETR", r"^rtdetr"),
]

#: training arguments the page may not set (the trainer sets them, or they
#: would point outside the run)
BLOCKED_ARGS = {"task", "mode", "model", "data", "project", "name", "exist_ok", "resume", "cfg",
                "source", "tracker", "distill_model", "save_dir", "format"}
#: arguments that are not about training (prediction / export / tracking)
_NOT_TRAINING = {"vid_stride", "stream_buffer", "visualize", "augment", "agnostic_nms", "classes",
                 "retina_masks", "embed", "show", "save_frames", "save_txt", "save_conf", "save_crop",
                 "show_labels", "show_conf", "show_boxes", "line_width", "optimize", "dynamic",
                 "simplify", "opset", "workspace", "dnn", "quantize", "conf", "nms"}


def task_of(name):
    stem = os.path.splitext(os.path.basename(name))[0].lower()
    for part in reversed(stem.split("-")[1:]):
        if part in _SUFFIX_TASK:
            return _SUFFIX_TASK[part]
    return "detect"


def _family(name):
    for key, label, pattern in FAMILIES:
        if re.match(pattern, name):
            return key
    return None


def _scale_of(name, family):
    stem = os.path.splitext(name)[0]
    rest = stem[len(re.match(dict((k, p) for k, _, p in FAMILIES)[family], stem).group(0)):]
    m = re.match(r"([a-z]\d?)(u)?(?:-|$)", rest) if rest else None
    return m.group(1) if m else ""


def _yaml_names(root):
    """Model yaml names Ultralytics accepts: each file, and for files with
    a "scales" section also <base><scale>.yaml (e.g. yolo26n.yaml)."""
    import yaml
    out = []
    for folder, _, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith(".yaml"):
                continue
            try:
                with open(os.path.join(folder, f)) as fp:
                    scales = (yaml.safe_load(fp) or {}).get("scales") or {}
            except Exception:
                scales = {}
            stem = f[:-5]
            # only an unscaled file (yolo26.yaml, yolov8-p2.yaml), not yolov10n.yaml
            m = re.match(r"^(yolov?\d+)((?:-.*)?)$", stem)
            if scales and m:
                out += [f"{m.group(1)}{s}{m.group(2)}.yaml" for s in scales]
            else:
                out.append(f)
    return out


def fitness_weights():
    """How Ultralytics picks the best epoch (best.pt): weights of
    [precision, recall, mAP50, mAP50-95] of each kind of result (boxes,
    masks, keypoints are added up). Older versions used 0.1 / 0.9."""
    try:
        from ultralytics.utils.metrics import Metric
        weights = []
        for i in range(4):
            m = Metric()
            m.mean_results = (lambda i=i: [1.0 if j == i else 0.0 for j in range(4)])
            f = m.fitness
            weights.append(round(float(f() if callable(f) else f), 4))
        return weights
    except Exception:
        return [0.0, 0.0, 0.1, 0.9]


def build():
    try:
        import ultralytics
        from ultralytics.cfg import DEFAULT_CFG_DICT
        from ultralytics.utils.downloads import GITHUB_ASSETS_NAMES
    except ImportError:
        return {"families": [], "args": {}, "version": None}
    names = [n for n in GITHUB_ASSETS_NAMES if n.endswith(".pt")]
    names += _yaml_names(os.path.join(os.path.dirname(ultralytics.__file__), "cfg", "models"))
    fams = {key: {"key": key, "label": label, "items": []} for key, label, _ in FAMILIES}
    seen = set()
    for name in sorted(set(names)):
        if _SKIP.search(name) or name in seen:
            continue
        family = _family(name)
        if family is None:
            continue
        seen.add(name)
        fams[family]["items"].append({
            "name": name, "kind": "pt" if name.endswith(".pt") else "yaml",
            "task": task_of(name), "scale": _scale_of(name, family),
        })
    args = {k: v for k, v in DEFAULT_CFG_DICT.items() if k not in BLOCKED_ARGS and k not in _NOT_TRAINING}
    return {"families": [f for f in fams.values() if f["items"]], "args": args,
            "version": getattr(ultralytics, "__version__", None), "fitness": fitness_weights()}


def names(catalog):
    return {i["name"]: i for f in (catalog or {}).get("families", []) for i in f["items"]}


_FITNESS_PARTS = ("precision", "recall", "mAP50", "mAP50-95")


def fitness_of(row, weights):
    """Ultralytics' fitness of an epoch's results: the weighted [P, R, mAP50,
    mAP50-95] of each kind of result (B boxes, M masks, P keypoints) added
    up; classification: mean of top-1 and top-5. None without metrics."""
    kinds = set()
    for key in row:
        m = re.match(r"^metrics/mAP50-95(?:\((\w)\))?$", key)
        if m:
            kinds.add(m.group(1) or "")
    if kinds:
        total = 0.0
        for kind in kinds:
            for part, w in zip(_FITNESS_PARTS, weights):
                value = row.get(f"metrics/{part}" + (f"({kind})" if kind else ""))
                if w and isinstance(value, (int, float)):
                    total += w * value
        return total
    if isinstance(row.get("metrics/accuracy_top1"), (int, float)):
        return (row["metrics/accuracy_top1"] + (row.get("metrics/accuracy_top5") or 0)) / 2
    if isinstance(row.get("metrics/mIoU"), (int, float)):
        return row["metrics/mIoU"]
    return None


def best_epoch(rows, weights):
    """The epoch best.pt comes from (the first with the highest fitness), or None."""
    best = None
    for i, row in enumerate(rows or []):
        f = fitness_of(row, weights)
        if f is None:
            continue
        if best is None or f > best["fitness"]:
            best = {"epoch": int(row.get("epoch", i + 1)), "fitness": round(f, 5), "row": row}
    if best is not None:
        last = rows[-1]
        best["since"] = int(last.get("epoch", len(rows))) - best["epoch"]
    return best
