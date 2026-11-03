"""COCO <-> YOLO (Ultralytics) label conversion.

Pure functions, no database: used by the export task, the YOLO import API
and ``scripts/coco_yolo.py``.

YOLO label files hold one object per line, coordinates normalised to 0-1:

    detect   class xc yc w h
    segment  class x1 y1 x2 y2 ... xn yn            (one polygon)
    obb      class x1 y1 x2 y2 x3 y3 x4 y4          (4 corners in order)
    pose     class xc yc w h px1 py1 v1 ... pxk pyk vk   (or px py without v)

Class indices follow the order of the ``names`` list (data.yaml / classes.txt).
"""
import math
import os
import re

import numpy as np

from . import polygon_to_rbbox, rbbox_to_polygon

TASKS = ("detect", "segment", "obb", "pose")
# tasks that can only be exported (no label files to import back)
EXPORT_TASKS = TASKS + ("classify", "semantic")
SEMANTIC_BACKGROUND = "background"

# COCO person keypoints (for 17-keypoint data without labels). Skeleton
# edges are 1-based, as in COCO.
COCO_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]
COCO_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13], [6, 12], [7, 13],
    [6, 7], [6, 8], [7, 9], [8, 10], [9, 11], [2, 3], [1, 2], [1, 3],
    [2, 4], [3, 5], [4, 6], [5, 7],
]


def stem(file_name):
    """'images/train/a.b.jpg' -> 'a.b'"""
    return os.path.splitext(os.path.basename(str(file_name).replace("\\", "/")))[0]


def safe_folder(name, default="dataset"):
    """User folder name -> safe zip folder: 'My ships/v1' -> 'My_ships_v1'."""
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", str(name or "")).strip("_.")
    return cleaned[:100] or default


def safe_prefix(name):
    """Dataset name -> file name prefix: 'My ships/2024' -> 'My_ships_2024_'."""
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", str(name or "")).strip("_.")
    return f"{cleaned}_" if cleaned else ""


def _fmt(values):
    return " ".join(f"{min(max(v, 0.0), 1.0):.6f}" for v in values)


def _polygons(annotation):
    seg = annotation.get("segmentation")
    if not isinstance(seg, list):
        return []
    return [p for p in seg if isinstance(p, list) and len(p) >= 6]


def _bbox(annotation):
    """x, y, w, h in pixels from bbox, polygons or visible keypoints."""
    bbox = annotation.get("bbox") or []
    if len(bbox) == 4 and bbox[2] > 0 and bbox[3] > 0:
        return [float(v) for v in bbox]
    pts = [v for p in _polygons(annotation) for v in p]
    if not pts:
        kp = annotation.get("keypoints") or []
        pts = [v for i in range(0, len(kp) - 2, 3) if kp[i + 2] > 0 for v in kp[i:i + 2]]
    if len(pts) < 4:
        return None
    xs, ys = pts[0::2], pts[1::2]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    return [min(xs), min(ys), w, h] if w > 0 and h > 0 else None


def _merge_polygons(polygons):
    """Several polygons -> one, joined by zero-width bridges between their
    nearest points (YOLO segment labels have one polygon per object)."""
    polys = [np.asarray(p, dtype=float).reshape(-1, 2) for p in polygons]
    merged = polys[0]
    for other in polys[1:]:
        d = ((merged[:, None, :] - other[None, :, :]) ** 2).sum(-1)
        i, j = np.unravel_index(int(d.argmin()), d.shape)
        loop = np.concatenate([other[j:], other[:j + 1]])
        merged = np.concatenate([merged[:i + 1], loop, merged[i:]])
    return merged.reshape(-1).tolist()


def _min_area_quad(points):
    import cv2
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    return cv2.boxPoints(cv2.minAreaRect(pts)).reshape(-1).tolist()


def _obb_corners(annotation):
    rbbox = annotation.get("rbbox") or []
    if annotation.get("isrbbox") and len(rbbox) == 5:
        polys = _polygons(annotation)
        return polys[0][:8] if polys and len(polys[0]) == 8 else rbbox_to_polygon(rbbox)
    polys = _polygons(annotation)
    if annotation.get("isbbox") and len(polys) == 1 and len(polys[0]) == 8:
        return polys[0]  # axis-aligned box: keep its corner order (angle 0)
    points = [v for p in polys for v in p]
    if len(points) >= 6:
        return _min_area_quad(points)
    bbox = _bbox(annotation)
    if bbox is None:
        return None
    x, y, w, h = bbox
    return [x, y, x + w, y, x + w, y + h, x, y + h]


# ------------------------------------------------------------- COCO -> YOLO

def coco_to_yolo(coco, task="detect", only_rbbox=False):
    """COCO dict -> YOLO labels.

    Returns ``{"names", "labels": {image_id: [line, ...]}, "kpt_shape",
    "flip_idx", "written", "skipped"}``. ``only_rbbox`` (obb) skips
    annotations that are not rotated boxes instead of fitting a rectangle.
    """
    if task not in TASKS:
        raise ValueError(f"Unknown YOLO task: {task}")

    categories = coco.get("categories", [])
    names = [c["name"] for c in categories]
    index = {c["id"]: i for i, c in enumerate(categories)}
    images = {img["id"]: img for img in coco.get("images", [])}

    num_kpts = 0
    if task == "pose":
        num_kpts = max([len(c.get("keypoints") or c.get("keypoint_labels") or []) for c in categories] +
                       [len(a.get("keypoints") or []) // 3 for a in coco.get("annotations", [])] + [0])

    labels = {image_id: [] for image_id in images}
    skipped = 0
    for ann in coco.get("annotations", []):
        image = images.get(ann.get("image_id"))
        cls = index.get(ann.get("category_id"))
        if image is None or cls is None or not image.get("width") or not image.get("height"):
            skipped += 1
            continue
        W, H = float(image["width"]), float(image["height"])

        def norm(points):
            return [v / (W if k % 2 == 0 else H) for k, v in enumerate(points)]

        line = None
        if task == "detect":
            bbox = _bbox(ann)
            if bbox:
                x, y, w, h = bbox
                line = _fmt([(x + w / 2) / W, (y + h / 2) / H, w / W, h / H])
        elif task == "segment":
            polys = _polygons(ann)
            if polys:
                line = _fmt(norm(polys[0] if len(polys) == 1 else _merge_polygons(polys)))
        elif task == "obb":
            if not (only_rbbox and not ann.get("isrbbox")):
                quad = _obb_corners(ann)
                if quad:
                    line = _fmt(norm(quad))
        else:  # pose
            kp = list(ann.get("keypoints") or [])
            bbox = _bbox(ann)
            if kp and bbox:
                kp += [0] * (num_kpts * 3 - len(kp))
                values = []
                for k in range(num_kpts):
                    px, py, v = kp[3 * k:3 * k + 3]
                    values += [px / W, py / H, int(v)] if v > 0 else [0.0, 0.0, 0]
                x, y, w, h = bbox
                head = _fmt([(x + w / 2) / W, (y + h / 2) / H, w / W, h / H])
                kps = " ".join(f"{min(max(v, 0.0), 1.0):.6f}" if k % 3 != 2 else str(v)
                               for k, v in enumerate(values))
                line = f"{head} {kps}"

        if line is None:
            skipped += 1
            continue
        labels[image["id"]].append(f"{cls} {line}")

    flip_idx = None
    if task == "pose" and num_kpts:
        flip_idx = _flip_idx(categories, num_kpts)
    return {
        "names": names,
        "labels": labels,
        "kpt_shape": [num_kpts, 3] if task == "pose" else None,
        "flip_idx": flip_idx,
        "written": sum(len(v) for v in labels.values()),
        "skipped": skipped,
    }


def _flip_idx(categories, num_kpts):
    """Left/right keypoint swap for horizontal-flip augmentation, from names."""
    labels = next((c.get("keypoints") or c.get("keypoint_labels") for c in categories
                   if len(c.get("keypoints") or c.get("keypoint_labels") or []) == num_kpts), None)
    if not labels:
        return list(range(num_kpts))
    lookup = {name.lower(): i for i, name in enumerate(labels)}
    flip = []
    for i, name in enumerate(labels):
        lower = name.lower()
        swapped = (lower.replace("left", "\0").replace("right", "left").replace("\0", "right"))
        flip.append(lookup.get(swapped, i))
    return flip


SUBSETS = ("train", "val", "test")


def parse_split(text):
    """'80,10,10' (train, val, test percentages) -> {"train": 80, "val": 10, "test": 10}.

    Empty / None -> None (no split). Raises ValueError when invalid.
    """
    if text in (None, "", "none"):
        return None
    try:
        values = [float(v) for v in str(text).replace("/", ",").replace(":", ",").split(",")]
    except ValueError:
        raise ValueError("split must look like 80,10,10")
    values += [0.0] * (3 - len(values))
    if len(values) != 3 or any(v < 0 for v in values) or abs(sum(values) - 100) > 0.01 or values[0] <= 0:
        raise ValueError("split: train, val and test percentages must add up to 100, with train above 0")
    return {name: (int(v) if float(v).is_integer() else v) for name, v in zip(SUBSETS, values)}


def split_images(image_ids, ratios, seed=42):
    """Randomly (but reproducibly for the same seed) assign images to subsets.

    Returns {image_id: "train" | "val" | "test"}. Every subset with a
    percentage above 0 gets at least one image when there are enough.
    """
    import random
    ids = sorted(image_ids)
    random.Random(seed).shuffle(ids)
    n = len(ids)
    sizes = {name: int(round(n * ratios.get(name, 0) / 100.0)) for name in ("val", "test")}
    for name in ("val", "test"):
        if ratios.get(name, 0) > 0 and sizes[name] == 0 and n - sum(sizes.values()) > 1:
            sizes[name] = 1
    while n and n - sum(sizes.values()) < 1:  # train keeps at least one image
        largest = max(sizes, key=sizes.get)
        sizes[largest] -= 1
    assignment = {}
    val_end = sizes["val"]
    test_end = val_end + sizes["test"]
    for i, image_id in enumerate(ids):
        assignment[image_id] = "val" if i < val_end else "test" if i < test_end else "train"
    return assignment


def data_yaml(names, task="detect", kpt_shape=None, flip_idx=None, split=None, root="", masks_dir=None):
    """Ultralytics dataset YAML for the train/images, train/labels layout.

    Without ``split`` every image is in train/ and val also points there.
    With a split ({"train": 80, "val": 10, "test": 10}) val and test point
    at val/images and test/images. No ``path:`` key, so Ultralytics
    resolves the folders next to this file. ``root`` is the folder the
    subsets are in (``<root>/train/images``).
    """
    base = f"{root}/" if root else ""
    lines = [f"# YOLO {task} dataset exported from COCO Annotator"]
    if split:
        lines += [
            "# split " + " / ".join(f"{k} {split.get(k, 0)}%" for k in SUBSETS),
            f"train: {base}train/images",
            f"val: {base}val/images" if split.get("val") else f"val: {base}train/images  # no validation split",
        ]
        if split.get("test"):
            lines.append(f"test: {base}test/images")
        lines.append("")
    else:
        lines += [
            "# not split: val also uses all images, split them before training for real",
            f"train: {base}train/images",
            f"val: {base}train/images",
            "",
        ]
    if masks_dir:
        lines.append(f"masks_dir: {masks_dir}  # PNG masks: pixel value = class index")
        lines.append("")
    if kpt_shape:
        lines.append(f"kpt_shape: [{kpt_shape[0]}, {kpt_shape[1]}]")
        if flip_idx is not None:
            lines.append(f"flip_idx: [{', '.join(str(i) for i in flip_idx)}]")
        lines.append("")
    lines.append("names:")
    for i, name in enumerate(names):
        quoted = "'" + str(name).replace("'", "''") + "'"
        lines.append(f"  {i}: {quoted}")
    return "\n".join(lines) + "\n"


# ------------------------------------------------- classify / semantic export

def image_classes(coco, explicit=None):
    """classify: each image's class.

    ``explicit`` ({image id: category id}) is the whole-image class set in
    the annotator; it wins. Other images get the class of their
    annotations when they are all one category.

    Returns ``(single, mixed, empty)``: ``single`` maps image id -> class
    index; ``mixed`` and ``empty`` list the images with several categories /
    no class at all.
    """
    explicit = explicit or {}
    index = {c["id"]: i for i, c in enumerate(coco.get("categories", []))}
    per_image = {}
    for a in coco.get("annotations", []):
        if a.get("category_id") in index:
            per_image.setdefault(a.get("image_id"), set()).add(index[a["category_id"]])
    single, mixed, empty = {}, [], []
    for image in coco.get("images", []):
        if explicit.get(image["id"]) in index:
            single[image["id"]] = index[explicit[image["id"]]]
            continue
        classes = per_image.get(image["id"], set())
        if len(classes) == 1:
            single[image["id"]] = next(iter(classes))
        elif classes:
            mixed.append(image)
        else:
            empty.append(image)
    return single, mixed, empty


def semantic_mask(image, annotations, category_index):
    """Single-channel mask: 0 = background, category index + 1 elsewhere.

    Larger shapes are drawn first so small objects on top of them stay
    visible. Boxes, rotated boxes and polygons all count; keypoint-only
    annotations do not.
    """
    import cv2
    mask = np.zeros((int(image["height"]), int(image["width"])), dtype=np.uint8)
    shapes = []
    for a in annotations:
        cls = category_index.get(a.get("category_id"))
        polys = _polygons(a)
        if cls is None or not polys:
            continue
        area = a.get("area") or sum(
            abs(np.dot(p[0::2], np.roll(p[1::2], 1)) - np.dot(p[1::2], np.roll(p[0::2], 1))) / 2
            for p in (np.asarray(q, dtype=float) for q in polys))
        shapes.append((float(area), cls, polys))
    for _, cls, polys in sorted(shapes, key=lambda s: -s[0]):
        pts = [np.round(np.asarray(p, dtype=float).reshape(-1, 2)).astype(np.int32) for p in polys]
        cv2.fillPoly(mask, pts, int(cls) + 1)
    return mask


# ------------------------------------------------------------- YOLO -> COCO

def parse_names(text, file_name=""):
    """Class names and kpt_shape from data.yaml (list or dict form) or classes.txt."""
    if file_name.lower().endswith((".yaml", ".yml")):
        import yaml
        data = yaml.safe_load(text) or {}
        names = data.get("names") or []
        if isinstance(names, dict):
            names = [str(names[k]) for k in sorted(names, key=lambda k: int(k))]
        kpt_shape = data.get("kpt_shape")
        return [str(n) for n in names], (list(kpt_shape) if kpt_shape else None)
    return [line.strip() for line in text.splitlines() if line.strip()], None


def _rows(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            rows.append([int(float(parts[0]))] + [float(v) for v in parts[1:]])
        except ValueError:
            continue
    return rows


def detect_task(label_texts, kpt_shape=None):
    """Guess the YOLO task from the number of values per line."""
    if kpt_shape:
        return "pose"
    rows = [r for text in label_texts for r in _rows(text)]
    lengths = {len(r) for r in rows}
    if not lengths:
        return "detect"
    if lengths == {5}:
        return "detect"
    polygon_like = {n for n in lengths if n != 5}
    if len(lengths) == 1:
        n = next(iter(lengths))
        # pose without data.yaml: box + (x, y, visibility) triples, visibility 0/1/2
        if n > 8 and (n - 5) % 3 == 0 and all(r[k] in (0.0, 1.0, 2.0) for r in rows for k in range(7, n, 3)):
            return "pose"
    if polygon_like == {9} and 5 not in lengths:  # OBB sets have no plain boxes
        return "obb"
    if all(n % 2 == 1 and n >= 7 for n in polygon_like):
        return "segment"
    if all(n > 5 and (n - 5) % 3 == 0 for n in lengths):
        return "pose"
    return "segment"


def yolo_to_coco(label_texts, images, names=None, task=None, kpt_shape=None, prefixes=()):
    """YOLO labels -> COCO dict.

    ``label_texts``: {stem or file name: text of the .txt}
    ``images``: [{"id", "file_name", "width", "height"}] matched by stem.
    ``task`` None or "auto" guesses from the lines.
    ``prefixes``: file name prefixes to ignore when a label has no exact
    match (e.g. "ships_" from an export that prefixed the dataset name).

    Returns ``(coco, stats)``; stats has ``task``, ``matched``,
    ``unmatched`` (label files without an image), ``ambiguous``,
    ``annotations`` and ``invalid`` (lines that could not be read).
    """
    names = list(names or [])
    texts = {stem(k): v for k, v in label_texts.items()}
    if task in (None, "", "auto"):
        task = detect_task(texts.values(), kpt_shape)
    if task not in TASKS:
        raise ValueError(f"Unknown YOLO task: {task}")

    by_stem = {}
    for image in images:
        by_stem.setdefault(stem(image["file_name"]), []).append(image)

    annotations, used_classes = [], set()
    stats = {"task": task, "matched": 0, "unmatched": [], "ambiguous": [], "annotations": 0, "invalid": 0}
    coco_images = []
    num_kpts = 0

    for key, text in sorted(texts.items()):
        candidates = by_stem.get(key, [])
        for prefix in prefixes:
            if candidates:
                break
            if prefix and key.startswith(prefix):
                candidates = by_stem.get(key[len(prefix):], [])
        if not candidates:
            stats["unmatched"].append(key)
            continue
        if len(candidates) > 1:
            stats["ambiguous"].append(key)
            continue
        image = candidates[0]
        W, H = float(image["width"]), float(image["height"])
        stats["matched"] += 1
        coco_images.append({k: image[k] for k in ("id", "file_name", "width", "height")})

        for row in _rows(text):
            cls, v = row[0], row[1:]
            ann = {"id": len(annotations) + 1, "image_id": image["id"], "category_id": cls + 1, "iscrowd": 0}

            # plain boxes are also accepted in segment / obb label files
            if task in ("detect", "pose") or len(v) == 4:
                if len(v) < 4:
                    stats["invalid"] += 1
                    continue
                xc, yc, w, h = v[0] * W, v[1] * H, v[2] * W, v[3] * H
                x, y = xc - w / 2, yc - h / 2
                ann["bbox"] = [round(x, 2), round(y, 2), round(w, 2), round(h, 2)]
                ann["area"] = round(w * h, 2)
                if task == "pose":
                    kv = v[4:]
                    dims = 3 if kpt_shape is None or kpt_shape[1] == 3 else 2
                    if kpt_shape is None and len(kv) % 3 != 0 and len(kv) % 2 == 0:
                        dims = 2
                    keypoints = []
                    for k in range(0, len(kv) - dims + 1, dims):
                        px, py = kv[k] * W, kv[k + 1] * H
                        vis = int(kv[k + 2]) if dims == 3 else (2 if px > 0 or py > 0 else 0)
                        keypoints += [round(px, 2), round(py, 2), vis] if vis > 0 else [0, 0, 0]
                    num_kpts = max(num_kpts, len(keypoints) // 3)
                    ann["keypoints"] = keypoints
                    ann["num_keypoints"] = sum(1 for k in range(2, len(keypoints), 3) if keypoints[k] > 0)
                    ann["segmentation"] = [[round(x, 2), round(y, 2), round(x + w, 2), round(y, 2),
                                            round(x + w, 2), round(y + h, 2), round(x, 2), round(y + h, 2)]]
                    ann["isbbox"] = True
                else:
                    ann["segmentation"] = []
            else:
                if len(v) < 6 or len(v) % 2:
                    stats["invalid"] += 1
                    continue
                poly = [round(val * (W if k % 2 == 0 else H), 2) for k, val in enumerate(v)]
                if task == "obb":
                    if len(poly) != 8:
                        stats["invalid"] += 1
                        continue
                    rbbox = [round(float(r), 3) for r in polygon_to_rbbox(poly)]
                    ann["rbbox"] = rbbox
                    ann["isrbbox"] = True
                    ann["area"] = round(abs(rbbox[2] * rbbox[3]), 2)
                else:
                    pts = np.asarray(poly).reshape(-1, 2)
                    x, y = pts[:, 0], pts[:, 1]
                    ann["area"] = round(float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2), 2)
                xs, ys = poly[0::2], poly[1::2]
                ann["segmentation"] = [poly]
                ann["bbox"] = [min(xs), min(ys), round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)]

            used_classes.add(cls)
            annotations.append(ann)

    stats["annotations"] = len(annotations)
    top = max(used_classes | {len(names) - 1}) if (used_classes or names) else -1
    categories = []
    for cls in range(top + 1):
        if cls >= len(names) and cls not in used_classes:
            continue
        category = {"id": cls + 1, "name": names[cls] if cls < len(names) else f"class_{cls}",
                    "supercategory": ""}
        if task == "pose" and num_kpts:
            if num_kpts == len(COCO_KEYPOINTS):
                category["keypoints"], category["skeleton"] = list(COCO_KEYPOINTS), [list(e) for e in COCO_SKELETON]
            else:
                category["keypoints"], category["skeleton"] = [str(k + 1) for k in range(num_kpts)], []
        categories.append(category)

    return {"images": coco_images, "categories": categories, "annotations": annotations}, stats


def read_zip(file_obj):
    """A YOLO dataset zip -> (label_texts, names, kpt_shape).

    Takes every ``*.txt`` that is not classes.txt as a label file (any
    folder layout: labels/train/a.txt, a.txt, ...), and the class names from
    data.yaml / *.yaml or classes.txt / obj.names.
    """
    import zipfile
    label_texts, names, kpt_shape = {}, None, None
    with zipfile.ZipFile(file_obj) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()
                   and not re.search(r"(^|/)(__MACOSX|\.)", m.filename)]
        name_files = sorted(
            (m for m in members if re.search(r"(\.ya?ml|(^|/)(classes\.txt|obj\.names|\w+\.names))$", m.filename, re.I)),
            key=lambda m: (os.path.basename(m.filename).lower() not in ("data.yaml", "data.yml"),
                           not m.filename.lower().endswith((".yaml", ".yml")), m.filename.count("/")))
        for m in name_files:
            try:
                found, shape = parse_names(zf.read(m).decode("utf-8-sig"), m.filename)
            except Exception:
                continue
            if found:
                names, kpt_shape = found, shape
                break
        for m in members:
            low = m.filename.lower()
            if low.endswith(".txt") and not re.search(r"(^|/)(classes|readme[^/]*)\.txt$", low):
                key = stem(m.filename)
                if key in label_texts:
                    label_texts[key] += "\n" + zf.read(m).decode("utf-8-sig", "replace")
                else:
                    label_texts[key] = zf.read(m).decode("utf-8-sig", "replace")
    return label_texts, names, kpt_shape
