import cv2
import numpy as np


def extract_patch(segmentation, img):
    """
    Creates a copy of img where all pixes outside of the segmentation
    are set to zero 
    """
    mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
    mask = cv2.drawContours(mask, segmentation, -1, 255, -1)
    return cv2.bitwise_and(img, img, mask=mask)


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
    for i in range(len(seg_a)):
        if len(seg_a[i]) != len(seg_b[i]):
            return False
        for j in range(len(seg_a[i])):
            if seg_a[i][j] != seg_b[i][j]:
                return False
    return True
