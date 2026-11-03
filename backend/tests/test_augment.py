"""Augmentation keeps annotations on the picture."""
import random

import numpy as np

from geometry import augment as A
from geometry import rbbox_to_polygon


def _picture():
    import cv2
    img = np.full((120, 200, 3), 30, np.uint8)
    rect = np.array([[60, 30], [140, 50], [130, 90], [50, 70]], np.int32)  # a tilted box
    cv2.fillPoly(img, [rect], (255, 255, 255))
    return img, rect


def _white_share(img, polygon):
    """How much of the white area is inside the polygon."""
    import cv2
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(np.asarray(polygon).reshape(-1, 2)).astype(np.int32)], 1)
    white = img[..., 0] > 200
    return (white & (mask > 0)).sum() / max(1, white.sum())


def test_every_operation_keeps_rotated_boxes_and_polygons_aligned():
    img, rect = _picture()
    flat = rect.reshape(-1).astype(float).tolist()
    from geometry import polygon_to_rbbox
    rbox = {"id": 1, "image_id": 1, "category_id": 1, "segmentation": [flat], "isrbbox": True,
            "rbbox": list(polygon_to_rbbox(flat))}
    poly = {"id": 2, "image_id": 1, "category_id": 1, "segmentation": [flat]}
    for name in ("hflip", "vflip", "rot90", "rotate", "scale", "color", "blur", "noise",
                 "jpeg", "motion", "exposure", "gray"):
        value = {"rotate": 20, "scale": 0.9}.get(name, True)
        for seed in range(4):
            out, anns, used = A.augment_image(img, [rbox, poly], {name: value}, random.Random(seed), {})
            assert used == [name]
            assert len(anns) == 2, (name, seed)
            r, p = anns
            assert _white_share(out, rbbox_to_polygon(r["rbbox"])) > 0.9, (name, seed)
            assert _white_share(out, p["segmentation"][0]) > 0.9, (name, seed)
            x, y, w, h = p["bbox"]
            assert 0 <= x and 0 <= y and x + w <= out.shape[1] + 0.01 and y + h <= out.shape[0] + 0.01


def test_keypoints_swap_left_and_right_on_horizontal_flip():
    img = np.zeros((50, 100, 3), np.uint8)
    ann = {"id": 1, "image_id": 1, "category_id": 7, "segmentation": [],
           "keypoints": [10, 20, 2, 30, 20, 2, 50, 40, 1]}
    flips = {7: A.flip_map(["左眼", "右眼", "鼻子"])}
    _, anns, _ = A.augment_image(img, [ann], {"hflip": True}, random.Random(0), flips)
    k = anns[0]["keypoints"]
    # the "left eye" is now the mirrored right eye, and the other way round
    assert k[0:3] == [70.0, 20.0, 2] and k[3:6] == [90.0, 20.0, 2] and k[6:9] == [50.0, 40.0, 1]


def test_shapes_mostly_outside_the_crop_are_dropped():
    img = np.zeros((100, 100, 3), np.uint8)
    corner = {"id": 1, "image_id": 1, "category_id": 1, "segmentation": [[0, 0, 6, 0, 6, 6, 0, 6]]}
    kept = sum(bool(A.augment_image(img, [corner], {"scale": 0.5}, random.Random(s), {})[1]) for s in range(30))
    assert kept < 30  # usually cropped away, never left as a sliver


def test_options():
    assert A.parse_options(None) is None
    assert A.parse_options({"copies": 2, "ops": {"hflip": "yes"}}) is None
    assert A.parse_options({"copies": 99, "ops": {"rotate": 200, "scale": 0.1, "blur": True}}) == \
        {"copies": 5, "ops": {"blur": True, "rotate": 45.0, "scale": 0.5}, "scope": "train"}
    assert A.parse_options({"copies": 1, "ops": {"hflip": True}, "scope": "all"})["scope"] == "all"


def test_new_picture_operations_change_only_the_picture():
    img, _ = _picture()
    for name in ("jpeg", "motion", "exposure", "gray"):
        out, _, used = A.augment_image(img, [], {name: True}, random.Random(3), {})
        assert used == [name] and out.shape == img.shape and out.dtype == np.uint8
        assert not np.array_equal(out, img) or name == "gray"  # the picture is grey already
    colour = np.zeros((10, 10, 3), np.uint8)
    colour[..., 2] = 200
    out, _, _ = A.augment_image(colour, [], {"gray": True}, random.Random(0), {})
    assert (out[..., 0] == out[..., 1]).all() and (out[..., 1] == out[..., 2]).all()


def test_cutout_drops_mostly_hidden_shapes_only():
    img = np.full((100, 100, 3), 30, np.uint8)
    small = {"id": 1, "image_id": 1, "category_id": 1, "segmentation": [[40, 40, 44, 40, 44, 44, 40, 44]]}
    big = {"id": 2, "image_id": 1, "category_id": 1, "segmentation": [[0, 0, 100, 0, 100, 100, 0, 100]]}
    dropped = 0
    for seed in range(40):
        out, anns, used = A.augment_image(img, [small, big], {"cutout": True}, random.Random(seed), {})
        assert used == ["cutout"] and (out == 114).any()
        assert any(a["id"] == 2 for a in anns)  # patches never hide most of the picture
        if not any(a["id"] == 1 for a in anns):
            dropped += 1
            # a patch is really over it
            assert (out[40:44, 40:44] == 114).mean() > 0.6
    assert dropped > 0


def test_new_options_parse():
    o = A.parse_options({"copies": 1, "ops": {"cutout": True, "jpeg": True, "motion": True,
                                              "exposure": True, "gray": True}})
    assert set(o["ops"]) == {"cutout", "jpeg", "motion", "exposure", "gray"}
