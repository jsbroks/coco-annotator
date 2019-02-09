import pycocotools.mask as mask

from .query_util import fix_ids
from ..models import *


def paperjs_to_coco(image_width, image_height, paperjs):
    """
    Given a paperjs CompoundPath, converts path into coco segmentation format based on children paths

    :param image_width: Width of Image
    :param image_height: Height of Image
    :param paperjs: paperjs CompoundPath in dict format
    :return: segmentation, area, bbox
    """
    assert image_width > 0
    assert image_height > 0
    assert len(paperjs) == 2

    # Compute segmentation
    # paperjs points are relative to the center, so we must shift them relative to the top left.
    segments = []
    center = [image_width/2, image_height/2]

    if paperjs[0] == "Path":
        compound_path = {"children": [paperjs]}
    else:
        compound_path = paperjs[1]
    
    children = compound_path.get('children', [])

    for child in children:

        child_segments = child[1].get('segments', [])
        segments_to_add = []

        for point in child_segments:
            
            # Cruve
            if len(point) == 4:
                point = point[0]
            
            # Point
            if len(point) == 2:
                x = _fit(round(center[0] + point[0], 2), image_width, 0)
                y = _fit(round(center[1] + point[1], 2), image_height, 0)
                segments_to_add.extend([x, y])

        # Make sure shape is not all outside the image
        if sum(segments_to_add) == 0:
            continue

        if len(segments_to_add) == 4:
            # len 4 means this is a line with no width; it contributes
            # no area to the mask, and if we include it, coco will treat
            # it instead as a bbox (and throw an error)
            continue

        num_widths = segments_to_add.count(image_width)
        num_heights = segments_to_add.count(image_height)
        if num_widths + num_heights == len(segments_to_add):
            continue

        segments.append(segments_to_add)

    if len(segments) < 1:
        return [], 0, [0, 0, 0, 0]

    area, bbox = get_segmentation_area_and_bbox(
        segments, image_height, image_width)

    return segments, area, bbox


def get_segmentation_area_and_bbox(segmentation, image_height, image_width):
    # Convert into rle
    rles = mask.frPyObjects(segmentation, image_height, image_width)
    rle = mask.merge(rles)

    return mask.area(rle), mask.toBbox(rle)


def get_annotations_iou(annotation_a, annotation_b):
    """
    Computes the IOU between two annotation objects
    """
    seg_a = list([list(part) for part in annotation_a.segmentation])
    seg_b = list([list(part) for part in annotation_b.segmentation])

    rles_a = mask.frPyObjects(
        seg_a, annotation_a.height, annotation_a.width)

    rles_b = mask.frPyObjects(
        seg_b, annotation_b.height, annotation_b.width)

    ious = mask.iou(rles_a, rles_b, [0])
    return ious[0][0]


def get_image_coco(image):
    """
    Generates coco for an image

    :param image: ImageModel
    :return: Coco in dictionary format
    """
    dataset = DatasetModel.objects(id=image.dataset_id).first()
    image = fix_ids(image)

    bulk_categories = CategoryModel.objects(deleted=False) \
        .exclude('deleted_date').in_bulk(dataset.categories).items()

    categories = []
    annotations = []

    for category in bulk_categories:

        category_annotations = AnnotationModel.objects(
            deleted=False, category_id=category[1].id, image_id=image.get('id')
        ).exclude('paper_object', 'deleted_date').all()

        if len(category_annotations) == 0:
            continue

        for annotation in category_annotations:
            annotation = fix_ids(annotation)

            if len(annotation.get('segmentation')) != 0:
                del annotation['deleted']
                del annotation['paper_object']
                annotations.append(annotation)

        category = fix_ids(category[1])
        del category['deleted']
        categories.append(category)

    del image['deleted']

    coco = {
        "images": [image],
        "categories": categories,
        "annotations": annotations
    }

    return coco


def get_dataset_coco(dataset):
    """
    Generates coco for all images in dataset

    :param dataset: DatasetModel
    :return: Coco in dictionary format
    """

    categories = CategoryModel.objects(deleted=False) \
        .exclude('deleted_date').in_bulk(dataset.categories).items()

    dataset = fix_ids(dataset)

    images = ImageModel.objects(deleted=False, dataset_id=dataset.get('id')).exclude('deleted_date')
    all_annotations = AnnotationModel.objects(deleted=False).exclude('deleted_date', 'paper_object')

    coco = {
        'images': [],
        'categories': [],
        'annotations': []
    }

    for category in categories:
        category = fix_ids(category[1])
        del category['deleted']
        coco.get('categories').append(category)

    for image in images:
        annotations = all_annotations.filter(image_id=image.id)
        if annotations.count() == 0:
            continue

        annotations = fix_ids(annotations.all())

        for annotation in annotations:
            if len(annotation.get('segmentation', [])) != 0:
                del annotation['deleted']
                coco.get('annotations').append(annotation)

        image = fix_ids(image)
        del image['deleted']
        coco.get('images').append(image)

    return coco


def _fit(value, max_value, min_value):

    if value > max_value:
        return max_value

    if value < min_value:
        return min_value

    return value
