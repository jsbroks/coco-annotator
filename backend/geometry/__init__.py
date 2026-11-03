"""Rotated (oriented) bounding box helpers.

Convention used throughout coco-annotator:

    rbbox = [cx, cy, w, h, angle]

* ``cx, cy``  centre in image pixels
* ``w``       length of the first edge (corner 0 -> corner 1)
* ``h``       length of the second edge (corner 1 -> corner 2)
* ``angle``   direction of the first edge in degrees, measured clockwise
              from the +x axis in image coordinates (y points down),
              normalised to (-180, 180]

The annotation's ``segmentation`` holds the same box as one polygon whose
four corners are in that order, i.e. it is directly a DOTA-style
``x1 y1 x2 y2 x3 y3 x4 y4`` quadrilateral.
"""
import math

import numpy as np


def _normalise_angle(angle):
    angle = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if angle == -180.0 else angle


def rbbox_to_polygon(rbbox):
    """[cx, cy, w, h, angle] -> [x0, y0, x1, y1, x2, y2, x3, y3]"""
    cx, cy, w, h, angle = rbbox
    theta = math.radians(angle)
    ux, uy = math.cos(theta), math.sin(theta)    # along the first edge
    vx, vy = -uy, ux                             # along the second edge
    hw, hh = w / 2.0, h / 2.0
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    poly = []
    for a, b in corners:
        poly.extend([round(cx + a * ux + b * vx, 2), round(cy + a * uy + b * vy, 2)])
    return poly


def polygon_to_rbbox(polygon):
    """Flat polygon -> [cx, cy, w, h, angle].

    Four ordered corners keep their orientation (the first edge defines the
    angle). Any other polygon falls back to the minimum-area rectangle.
    """
    pts = np.asarray(polygon, dtype=np.float64).reshape(-1, 2)
    if len(pts) == 5 and np.allclose(pts[0], pts[-1]):
        pts = pts[:4]

    if len(pts) == 4:
        p0, p1, p2 = pts[0], pts[1], pts[2]
        w = float(np.linalg.norm(p1 - p0))
        h = float(np.linalg.norm(p2 - p1))
        angle = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        cx, cy = pts.mean(axis=0)
    else:
        import cv2
        (cx, cy), (w, h), angle = cv2.minAreaRect(pts.astype(np.float32))

    return [round(float(cx), 2), round(float(cy), 2),
            round(float(w), 2), round(float(h), 2),
            round(_normalise_angle(float(angle)), 2)]


def rbbox_area(rbbox):
    return float(rbbox[2]) * float(rbbox[3])
