from ..models import ImageModel, CategoryModel, AnnotationModel
from .coco_util import get_segmentation_area_and_bbox
from .query_util import fix_ids

import numpy as np
import json
import os


def scan_func(task, socket, dataset):

    directory = dataset.directory
    toplevel = list(os.listdir(directory))
    task.info(f"Scanning {directory}")

    count = 0
    for root, dirs, files in os.walk(directory):

        try:
            youarehere = toplevel.index(root.split('/')[-1])
            progress = int(((youarehere)/len(toplevel))*100)
            task.set_progress(progress, socket=socket)
        except:
            pass

        for file in files:
            path = os.path.join(root, file)

            if path.endswith(ImageModel.PATTERN):
                db_image = ImageModel.objects(path=path).first()

                if db_image is not None:
                    continue

                try:
                    ImageModel.create_from_path(path, dataset.id).save()
                    count += 1
                    task.info(f"New file found: {path}")
                except:
                    task.warning(f"Could not read {path}")

    task.info(f"Created {count} new image(s)")
    task.set_progress(100, socket=socket)


def export_coco_func(task, socket, dataset):

    task.info("Beginning Export (COCO Format)")

    categories = CategoryModel.objects(deleted=False) \
        .exclude('deleted_date').in_bulk(dataset.categories).items()
    
    total_items = len(dataset.categories)
    dataset = fix_ids(dataset)

    images = ImageModel.objects(deleted=False, annotated=True, dataset_id=dataset.get('id')).exclude('deleted_date')
    all_annotations = AnnotationModel.objects(deleted=False).exclude('deleted_date', 'paper_object')

    coco = {
        'images': [],
        'categories': [],
        'annotations': []
    }

    total_items += images.count()
    progress = 0
    for category in categories:
        category = fix_ids(category[1])

        del category['deleted']
        if len(category.get('keypoint_labels', [])) > 0:
            category['keypoints'] = category.pop('keypoint_labels')
            category['skeleton'] = category.pop('keypoint_edges')
        else:
            del category['keypoint_edges']
            del category['keypoint_labels']

        task.info(f"Adding category: {category.get('name')}")
        coco.get('categories').append(category)
        
        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)

    for image in images:
        annotations = all_annotations.filter(image_id=image.id)
        if annotations.count() == 0:
            continue

        annotations = fix_ids(annotations.all())
        num_annotations = 0
        for annotation in annotations:

            has_keypoints = len(annotation.get('keypoints', [])) > 0
            has_segmentation = len(annotation.get('segmentation', [])) > 0

            if has_keypoints or has_segmentation:
                del annotation['deleted']

                if not has_keypoints:
                    pass
                    # del annotation['keypoints']
                else:
                    arr = np.array(annotation.get('keypoints', []))
                    arr = arr[2::3]
                    annotation['num_keypoints'] = len(arr[arr > 0])
                
                num_annotations += 1
                coco.get('annotations').append(annotation)
        
        task.info(f'Exporting {num_annotations} annotations for image {image.id}')

        image = fix_ids(image)
        del image['deleted']
        coco.get('images').append(image)
        
        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)  
    
    file_path = dataset.get('directory') + '/coco.json'
    with open(file_path, 'w') as fp:
        json.dump(coco, fp)

    task.info(f"Done export {dataset.get('name')}")
    task.set_progress(100, socket=socket)


def import_coco_func(task, socket, dataset, coco_json):
    task.info("Beginning Import")

    images = ImageModel.objects(dataset_id=dataset.id)
    categories = CategoryModel.objects

    coco_images = coco_json.get('images', [])
    coco_annotations = coco_json.get('annotations', [])
    coco_categories = coco_json.get('categories', [])

    task.info(f"Importing {len(coco_categories)} categories, "
              f"{len(coco_images)} images, and "
              f"{len(coco_annotations)} annotations")

    total_items = sum([
        len(coco_categories),
        len(coco_annotations),
        len(coco_images)
    ])
    progress = 0

    task.info("===== Importing Categories =====")
    # category id mapping  ( file : database )
    categories_id = {}

    # Create any missing categories
    for category in coco_categories:

        category_name = category.get('name')
        category_id = category.get('id')
        category_model = categories.filter(name__iexact=category_name).first()

        if category_model is None:
            task.warning(f"{category_name} category not found (creating a new one)")
            
            new_category = CategoryModel(
                name=category_name,
                keypoint_edges=category.get('skeleton', []),
                keypoint_labels=category.get('keypoints', [])
            )
            new_category.save()

            category_model = new_category
            dataset.categories.append(new_category.id)

        task.info(f"{category_name} category found")
        # map category ids
        categories_id[category_id] = category_model.id

        # update progress
        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)

    dataset.update(set__categories=dataset.categories)

    task.info("===== Loading Images =====")
    # image id mapping ( file: database )
    images_id = {}
    categories_by_image = {}

    # Find all images
    for image in coco_images:
        image_id = image.get('id')
        image_filename = image.get('file_name')

        # update progress
        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)

        image_model = images.filter(file_name__exact=image_filename).all()

        if len(image_model) == 0:
            task.warning(f"Could not find image {image_filename}")
            continue

        if len(image_model) > 1:
            task.error(f"To many images found with the same file name: {image_filename}")
            continue

        task.info(f"Image {image_filename} found")
        image_model = image_model[0]
        images_id[image_id] = image_model
        categories_by_image[image_id] = list()

    task.info("===== Import Annotations =====")
    for annotation in coco_annotations:

        image_id = annotation.get('image_id')
        category_id = annotation.get('category_id')
        segmentation = annotation.get('segmentation', [])
        keypoints = annotation.get('keypoints', [])
        is_crowd = annotation.get('iscrowed', False)

        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)

        if len(segmentation) == 0 and len(keypoints) == 0:
            task.warning(f"Annotation {annotation.get('id')} has no segmentation or keypoints")
            continue

        try:
            image_model = images_id[image_id]
            category_model_id = categories_id[category_id]
            image_categories = categories_by_image[image_id]
        except KeyError:
            task.warning(f"Could not find image assoicated with annotation {annotation.get('id')}")
            continue

        annotation_model = AnnotationModel.objects(
            image_id=image_model.id,
            category_id=category_model_id,
            segmentation=segmentation,
            keypoints=keypoints
        ).first()

        if annotation_model is None:
            task.info(f"Creating annotation data ({image_id}, {category_id})")

            annotation_model = AnnotationModel(image_id=image_model.id)
            annotation_model.category_id = category_model_id

            annotation_model.color = annotation.get('color')
            annotation_model.metadata = annotation.get('metadata', {})
            annotation_model.segmentation = segmentation
            area, bbox = get_segmentation_area_and_bbox(
                segmentation, image_model.height, image_model.width)
            annotation_model.area = area
            annotation_model.bbox = list(bbox)
            annotation_model.keypoints = keypoints
            annotation_model.save()

            image_categories.append(category_id)
        else:
            task.info(f"Annotation already exists (i:{image_id}, c:{category_id})")

    for image_id in images_id:
        image_model = images_id[image_id]
        category_ids = categories_by_image[image_id]
        all_category_ids = list(image_model.category_ids)
        all_category_ids += category_ids
        image_model.update(
            set__annotated=True,
            set__category_ids=list(set(all_category_ids)))

    task.set_progress(100, socket=socket)
