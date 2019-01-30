import cv2
import numpy as np


def extract_cropped_patch(img, mask, bbox):
    """
    Creates a copy of img whereever the pixels of mask are non-zero,
    then crops the copy by the provided bbox
    """
    patch = cv2.bitwise_and(img, img, mask=mask)
    x, y, w, h = bbox
    return patch[y:y + h, x:x + w]


def rect_union(a, b):
    x = min(a[0], b[0])
    y = min(a[1], b[1])
    w = max(a[0] + a[2], b[0] + b[2]) - x
    h = max(a[1] + a[3], b[1] + b[3]) - y
    return (x, y, w, h)


def bbox_for_contours(contours):
    bbox = (0, 0, 0, 0)
    for cnt in contours:
        bbox = rect_union(bbox, cv2.boundingRect(cnt))
    return bbox


def segmentation_to_contours(segmentation):
    contours = list()
    for poly in segmentation:
        if len(poly) % 2 != 0:
            raise ValueError(
                "Each polygon should have even number of elements")
        polygon = []
        for i in range(0, len(poly), 2):
            polygon.append([poly[i], poly[i + 1]])
        contours.append(np.array(polygon, dtype=np.int32))
    return contours


def segmentation_equal(seg_a, seg_b):
    """
    Compares 2 segmentations for equality
    """
    if len(seg_a) != len(seg_b):
        return False

    for i, _ in enumerate(seg_a):
        # remove excess points used for closing the loop
        if len(seg_a[i]) >= 4:
            if seg_a[i][0] == seg_a[i][-2] and seg_a[i][1] == seg_a[i][-1]:
                seg_a[i] = seg_a[i][:-2]
        if len(seg_b[i]) >= 4:
            if seg_b[i][0] == seg_b[i][-2] and seg_b[i][1] == seg_b[i][-1]:
                seg_b[i] = seg_b[i][:-2]
        if len(seg_a[i]) != len(seg_b[i]):
            return False
        for j in range(len(seg_a[i])):
            if seg_a[i][j] != seg_b[i][j]:
                return False
    return True
