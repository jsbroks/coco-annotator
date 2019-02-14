from ..models import ImageModel, CategoryModel, AnnotationModel

import imantics as im
import time
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


def import_coco_func(task, socket, dataset, coco_json):
    task.info("Beginning Import")

    images = ImageModel.objects(dataset_id=dataset.id)
    categories = CategoryModel.objects

    coco_images = coco_json.get('images')
    coco_annotations = coco_json.get('annotations')
    coco_categories = coco_json.get('categories')

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
                name=category_name
            )
            new_category.save()

            category_model = new_category
            dataset.categories.append(value)
        
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

    task.info("===== Import Annotations =====")
    for annotation in coco_annotations:

        image_id = annotation.get('image_id')
        category_id = annotation.get('category_id')
        segmentation = annotation.get('segmentation')
        is_crowd = annotation.get('iscrowed', False)

        progress += 1
        task.set_progress((progress/total_items)*100, socket=socket)

        if len(segmentation) == 0:
            task.warning(f"Annotation {annotation.get('id')} has no segmentation")
            continue
        
        try:
            image_model = images_id[image_id]
            category_model_id = categories_id[category_id]
        except KeyError:
            task.warning(f"Could not find image assoicated with annotation {annotation.get('id')}")
            continue
        
        annotation_model = AnnotationModel.objects(
            image_id=image_model.id,
            category_id=category_model_id,
            segmentation=segmentation,
            delete=False
        ).first()

        if annotation_model is None:
            task.info(f"Creating annotation data ({image_id}, {category_id})")

            annotation_model = AnnotationModel(image_id=image_model.id)
            annotation_model.category_id = category_model_id
            
            annotation_model.color = annotation.get('color')
            annotation_model.metadata = annotation.get('metadata', {})
            annotation_model.segmentation = segmentation
            annotation_model.save()

            image_model.update(set__annotated=True)
        else:
            task.info(f"Annotation already exists (i:{image_id}, c:{category_id})")
 
    task.set_progress(100, socket=socket)


