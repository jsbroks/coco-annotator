import pycocotools.mask as mask
import numpy as np
from shapely.geometry import LineString, Point
import skimage.draw as sd

from database import (
    fix_ids,
    ImageModel,
    DatasetModel,
    CategoryModel,
    AnnotationModel
)
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
    segments_with_area = []
    pts_or_lines = []
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
            
            # Curve or segment with handles
            if len(point) == 4 or len(point) == 3:
                point = point[0]
            
            # Point
            if len(point) == 2:
                x = round(center[0] + point[0], 2)
                y = round(center[1] + point[1], 2)
                segments_to_add.extend([x, y])

        # Make sure shape is not all outside the image
        if sum(segments_to_add) == 0:
            continue

        if len(segments_to_add) == 4 or len(segments_to_add) == 2:
            # len 4 means this is a line with no width; it contributes
            # no area to the mask, and if we include it, coco will treat
            # it instead as a bbox (and throw an error)
            pts_or_lines.append(segments_to_add)
            continue

        num_widths = segments_to_add.count(image_width)
        num_heights = segments_to_add.count(image_height)

        if num_widths + num_heights == len(segments_to_add):
            continue

        segments_with_area.append(segments_to_add)

    if len(segments_with_area) < 1:
        return pts_or_lines, 0, None
    else :
        area, bbox = get_segmentation_area_and_bbox(
        segments_with_area, image_height, image_width)

    return segments_with_area + pts_or_lines, area, bbox

def paperjs_to_coco_cliptobounds(image_width, image_height, paperjs): # todo: there's lots of edge cases to this. It needs a different solution or many many if statements :P
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


        i_start = 0
        inside = False
        # find a point that's inside the canvas
        while(i_start < len(child_segments)):
            point = child_segments[i_start]
            if len(point) == 4: point = point[0] # curve
            if len(point) == 2: # point
                if (abs(point[0]) > image_width/2 or point[1] > image_height/2):
                    i_start += 1
                    continue
                inside = True
                break
            i_start += 1
        
        if inside: # if point is inside the canvas. Otherwise ignore it
            edges = {
                'w_0': np.array([[0,0],[image_width, 0]], np.float),
                'w_1': np.array([[0,image_height],[image_width, image_height]], np.float),
                'h_0': np.array([[0,0],[0, image_height]], np.float),
                'h_1': np.array([[image_width,0],[image_width, image_height]], np.float),
            }
            prev_point = None
            for i in range(i_start, i_start + len(child_segments)):
                p = i % len(child_segments)
                point = child_segments[p]
                
                # Cruve
                if len(point) == 4:
                    point = point[0]
                
                # Point
                if len(point) == 2:
                    x = round(center[0] + point[0], 2)
                    y = round(center[1] + point[1], 2)
                    x_orig, y_orig = x,y
                    point_outside = x > image_width or x < 0 or y > image_height or y < 0
                    # prev_point_outside = prev_point[0] > image_width or prev_point[0] < 0 or prev_point[1] > image_height or prev_point[1] < 0
                    if point_outside: # outside canvas
                        line = LineString([[x,y], prev_point])
                        for _, edge in edges.items():
                            intersect = line.intersection(LineString(edge))
                            if not intersect.is_empty:
                                if intersect.type == 'LineString': intersect = intersect.xy[0]
                                else: intersect = [intersect.x, intersect.y]
                                print(x,y, prev_point)
                                print(intersect, flush=True)
                                x,y = intersect
                                break
                    segments_to_add.extend([x, y])
                    prev_point = [x_orig,y_orig]
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

def get_bin_mask(segmentation, image_height, image_width):
    """
    Computes the binary mask of an annotation in polyfon format.
    It separates segmentations in line and point format (they are not supported by PyCOCOTools)
    :return: binary mask np.array format
    """
    bin_mask = np.zeros((image_height, image_width))
    points = []
    lines = []
    polygons = []
    
    for segment in segmentation :
        if len(segment) == 2:
            points.append(segment)
        elif len(segment) == 4:
            lines.append(segment)
        else :
            polygons.append(segment)
    
    if len(polygons) != 0 :
        # Convert into rle
        rles = mask.frPyObjects(polygons, image_height, image_width)
        rle = mask.merge(rles)
        # Extract the binary mask
        bin_mask = mask.decode(rle)

    for point in points:
        bin_mask[round(point[1])][round(point[0])] = 1

    for line in lines:
        rr, cc = sd.line(round(line[0]), round(line[1]), round(line[2]), round(line[3]))
        bin_mask[cc,rr] = 1

    return bin_mask

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


def get_image_coco(image_id):
    """
    Generates coco for an image

    :param image: ImageModel
    :return: Coco in dictionary format
    """
    image = ImageModel.objects(id=image_id)\
        .only(*ImageModel.COCO_PROPERTIES)
    
    image = fix_ids(image)[0]
    dataset = DatasetModel.objects(id=image.get('dataset_id')).first()

    bulk_categories = CategoryModel.objects(id__in=dataset.categories, deleted=False) \
        .only(*CategoryModel.COCO_PROPERTIES)

    print(bulk_categories)

    db_annotations = AnnotationModel.objects(deleted=False, image_id=image_id)
    categories = []
    annotations = []

    for category in fix_ids(bulk_categories):

        category_annotations = db_annotations\
            .filter(category_id=category.get('id'))\
            .only(*AnnotationModel.COCO_PROPERTIES)
        
        if category_annotations.count() == 0:
            continue
        
        category_annotations = fix_ids(category_annotations)
        for annotation in category_annotations:
            has_polygon_segmentation = len(annotation.get('segmentation', [])) > 0
            has_rle_segmentation = annotation.get('rle', {}) != {}
            has_keypoints = len(annotation.get('keypoints', [])) > 0

            if has_polygon_segmentation or has_keypoints or has_rle_segmentation:

                if has_keypoints:
                    arr = np.array(annotation.get('keypoints', []))
                    arr = arr[2::3]
                    annotation['num_keypoints'] = len(arr[arr > 0])
                if has_rle_segmentation:
                    rle = annotation.get('rle')
                    annotation['segmentation'] = rle
                    annotation.pop('rle')
                annotations.append(annotation)

        if len(category.get('keypoint_labels')) > 0:
            category['keypoints'] = category.pop('keypoint_labels')
            category['skeleton'] = category.pop('keypoint_edges')
        else:
            del category['keypoint_edges']
            del category['keypoint_labels']
        
        categories.append(category)

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
        if len(category.get('keypoint_labels', [])) > 0:
            category['keypoints'] = category.pop('keypoint_labels')
            category['skeleton'] = category.pop('keypoint_edges')
        else:
            del category['keypoint_edges']
            del category['keypoint_labels']

        coco.get('categories').append(category)

    for image in images:
        annotations = all_annotations.filter(image_id=image.id)
        if annotations.count() == 0:
            continue

        annotations = fix_ids(annotations.all())

        for annotation in annotations:

            has_keypoints = len(annotation.get('keypoints', [])) > 0
            has_segmentation = len(annotation.get('segmentation', [])) > 0

            if has_keypoints or has_segmentation:
                del annotation['deleted']

                if not has_keypoints:
                    del annotation['keypoints']
                else:
                    arr = np.array(annotation.get('keypoints', []))
                    arr = arr[2::3]
                    annotation['num_keypoints'] = len(arr[arr > 0])
                
                coco.get('annotations').append(annotation)

        image = fix_ids(image)
        del image['deleted']
        coco.get('images').append(image)

    return coco


def _fit(value, max_value, min_value):
    return max(min(value, max_value), min_value)
