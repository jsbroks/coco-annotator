#!/usr/bin/env python3
"""Convert between COCO JSON and YOLO (Ultralytics) labels, outside the web UI.

COCO -> YOLO (writes out_dir/train/labels/*.txt, data.yaml, classes.txt):

    python scripts/coco_yolo.py coco2yolo export.json out_dir --task detect
    python scripts/coco_yolo.py coco2yolo export.json out_dir --task obb --images /data/my_dataset

  --task     detect | segment | obb | pose
  --images   also copy the images (looked up by file_name in this folder) to out_dir/train/images

YOLO -> COCO (image sizes are read from the image files):

    python scripts/coco_yolo.py yolo2coco labels_dir images_dir out.json --names data.yaml

  labels_dir  folder with the .txt label files (searched recursively), or a .zip
  images_dir  folder with the images (searched recursively)
  --names     data.yaml, classes.txt or obj.names (else found in labels_dir / zip)
  --task      auto (default) | detect | segment | obb | pose

Requires numpy, Pillow, PyYAML (and opencv for --task obb from polygons).
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from geometry.yolo_format import (  # noqa: E402
    TASKS, coco_to_yolo, data_yaml, parse_names, read_zip, stem, yolo_to_coco)

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp")


def walk(folder, extensions):
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if not name.startswith(".") and name.lower().endswith(extensions):
                yield os.path.join(root, name)


def coco2yolo(args):
    with open(args.coco_json, encoding="utf-8") as f:
        coco = json.load(f)
    result = coco_to_yolo(coco, args.task, only_rbbox=args.only_rbbox)

    labels_dir = os.path.join(args.out_dir, "train", "labels")
    os.makedirs(labels_dir, exist_ok=True)
    found = {stem(p): p for p in walk(args.images, IMAGE_EXT)} if args.images else {}
    if args.images:
        os.makedirs(os.path.join(args.out_dir, "train", "images"), exist_ok=True)

    used, missing = set(), 0
    for image in coco.get("images", []):
        name = stem(image["file_name"])
        if name in used:
            name = f"{name}_{image['id']}"
        used.add(name)
        lines = result["labels"].get(image["id"], [])
        with open(os.path.join(labels_dir, name + ".txt"), "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        if args.images:
            source = found.get(stem(image["file_name"]))
            if source:
                shutil.copy2(source, os.path.join(args.out_dir, "train", "images", name + os.path.splitext(source)[1]))
            else:
                missing += 1

    with open(os.path.join(args.out_dir, "data.yaml"), "w", encoding="utf-8") as f:
        f.write(data_yaml(result["names"], args.task, result["kpt_shape"], result["flip_idx"]))
    with open(os.path.join(args.out_dir, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(result["names"]) + "\n")

    print(f"Wrote {result['written']} {args.task} labels for {len(used)} images to {args.out_dir} "
          f"({result['skipped']} annotations could not be converted)")
    if missing:
        print(f"Warning: {missing} images not found in {args.images}")


def yolo2coco(args):
    from PIL import Image

    names, kpt_shape = None, None
    if args.labels.lower().endswith(".zip"):
        with open(args.labels, "rb") as f:
            texts, names, kpt_shape = read_zip(f)
    else:
        texts = {}
        for path in walk(args.labels, (".txt",)):
            base = os.path.basename(path).lower()
            if base == "classes.txt" or base.startswith("readme"):
                continue
            with open(path, encoding="utf-8-sig") as f:
                texts[stem(path)] = texts.get(stem(path), "") + f.read()
        for candidate in ("data.yaml", "data.yml", "classes.txt", "obj.names"):
            for path in walk(args.labels, (candidate,)):
                with open(path, encoding="utf-8-sig") as f:
                    names, kpt_shape = parse_names(f.read(), path)
                break
            if names:
                break
    if args.names:
        with open(args.names, encoding="utf-8-sig") as f:
            names, kpt_shape = parse_names(f.read(), args.names)

    images = []
    for i, path in enumerate(sorted(walk(args.images, IMAGE_EXT)), start=1):
        with Image.open(path) as im:
            width, height = im.size
        images.append({"id": i, "file_name": os.path.relpath(path, args.images).replace(os.sep, "/"),
                       "width": width, "height": height})

    coco, stats = yolo_to_coco(texts, images, names=names, task=args.task, kpt_shape=kpt_shape)
    if args.all_images:
        coco["images"] = images
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(coco, f, ensure_ascii=False)

    print(f"Task {stats['task']}: {stats['annotations']} annotations from {stats['matched']} label files "
          f"-> {args.out_json}")
    if not names:
        print("Warning: no class names (data.yaml / classes.txt); classes are named class_0, class_1, ...")
    if stats["unmatched"]:
        print(f"Warning: {len(stats['unmatched'])} label files without an image, e.g. {stats['unmatched'][:5]}")
    if stats["ambiguous"]:
        print(f"Warning: several images share the name of {stats['ambiguous'][:5]}; skipped")
    if stats["invalid"]:
        print(f"Warning: {stats['invalid']} label lines could not be read")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("coco2yolo", help="COCO JSON -> YOLO labels")
    a.add_argument("coco_json")
    a.add_argument("out_dir")
    a.add_argument("--task", choices=TASKS, default="detect")
    a.add_argument("--images", help="folder with the images, to copy them into out_dir/train/images")
    a.add_argument("--only-rbbox", action="store_true", help="obb: skip annotations that are not rotated boxes")
    a.set_defaults(func=coco2yolo)

    b = sub.add_parser("yolo2coco", help="YOLO labels -> COCO JSON")
    b.add_argument("labels", help="folder with .txt labels, or a .zip")
    b.add_argument("images", help="folder with the images")
    b.add_argument("out_json")
    b.add_argument("--names", help="data.yaml, classes.txt or obj.names")
    b.add_argument("--task", choices=("auto",) + TASKS, default="auto")
    b.add_argument("--all-images", action="store_true", help="also list images without labels")
    b.set_defaults(func=yolo2coco)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
