#!/usr/bin/env python3
"""Convert a coco-annotator COCO export into oriented-box training labels.

    python scripts/export_obb.py coco-export.json out_dir --format dota
    python scripts/export_obb.py coco-export.json out_dir --format yolo-obb

Writes one .txt per image:

  dota      x1 y1 x2 y2 x3 y3 x4 y4 class_name difficult   (pixels)
  yolo-obb  class_index x1 y1 x2 y2 x3 y3 x4 y4             (normalised 0-1)

Rotated boxes (isrbbox) use their 4 ordered corners. Other polygons are
converted with the minimum-area rectangle unless --only-rbbox is given.
YOLO class indices follow the order of "categories" in the export and are
written to classes.txt.
"""
import argparse
import json
import math
import os
from collections import defaultdict


def rbbox_to_polygon(cx, cy, w, h, angle):
    t = math.radians(angle)
    ux, uy, vx, vy = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
    pts = []
    for a, b in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        pts += [cx + a * ux + b * vx, cy + a * uy + b * vy]
    return pts


def min_area_quad(polygon):
    import cv2
    import numpy as np
    pts = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
    return cv2.boxPoints(cv2.minAreaRect(pts)).reshape(-1).tolist()


def corners(annotation, only_rbbox):
    if annotation.get("isrbbox") and len(annotation.get("rbbox", [])) == 5:
        seg = annotation.get("segmentation") or []
        if seg and len(seg[0]) == 8:
            return seg[0]
        return rbbox_to_polygon(*annotation["rbbox"])
    if only_rbbox or not annotation.get("segmentation"):
        return None
    points = [v for poly in annotation["segmentation"] for v in poly]
    return min_area_quad(points) if len(points) >= 6 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("coco_json")
    parser.add_argument("out_dir")
    parser.add_argument("--format", choices=["dota", "yolo-obb"], default="dota")
    parser.add_argument("--only-rbbox", action="store_true", help="skip annotations that are not rotated boxes")
    args = parser.parse_args()

    with open(args.coco_json) as f:
        coco = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    categories = coco.get("categories", [])
    cat_name = {c["id"]: c["name"] for c in categories}
    cat_index = {c["id"]: i for i, c in enumerate(categories)}
    images = {img["id"]: img for img in coco.get("images", [])}

    lines = defaultdict(list)
    skipped = 0
    for ann in coco.get("annotations", []):
        quad = corners(ann, args.only_rbbox)
        image = images.get(ann["image_id"])
        if quad is None or image is None:
            skipped += 1
            continue
        if args.format == "dota":
            coords = " ".join(f"{(round(v, 1) or 0.0):.1f}" for v in quad)
            name = cat_name.get(ann["category_id"], "unknown").replace(" ", "-")
            lines[ann["image_id"]].append(f"{coords} {name} 0")
        else:
            w, h = image["width"], image["height"]
            norm = [min(max(v / (w if i % 2 == 0 else h), 0.0), 1.0) for i, v in enumerate(quad)]
            coords = " ".join(f"{v:.6f}" for v in norm)
            lines[ann["image_id"]].append(f"{cat_index[ann['category_id']]} {coords}")

    for image_id, image in images.items():
        stem = os.path.splitext(os.path.basename(image["file_name"]))[0]
        with open(os.path.join(args.out_dir, stem + ".txt"), "w") as f:
            f.write("\n".join(lines.get(image_id, [])) + ("\n" if lines.get(image_id) else ""))

    if args.format == "yolo-obb":
        with open(os.path.join(args.out_dir, "classes.txt"), "w") as f:
            f.write("\n".join(c["name"] for c in categories) + "\n")

    total = sum(len(v) for v in lines.values())
    print(f"Wrote {total} boxes for {len(images)} images to {args.out_dir} ({skipped} annotations skipped)")


if __name__ == "__main__":
    main()
