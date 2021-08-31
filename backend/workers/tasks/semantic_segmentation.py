from database import (
    fix_ids,
    ImageModel,
    CategoryModel,
    AnnotationModel,
    DatasetModel,
    TaskModel,
    ExportModel
)
import io
import os
import time
import numpy as np
import pycocotools.mask as mask

import zipfile
from PIL import Image
from celery import shared_task
from ..socket import create_socket

@shared_task
def export_semantic_segmentation(task_id, dataset_id, categories):
    # Initiate a task and its socket
    task = TaskModel.objects.get(id=task_id)
    task.info(f"Beginning Export Semantic Segmentation")
    task.update(status="PROGRESS")
    socket = create_socket()
    
    # Get the needed items from the database
    dataset = DatasetModel.objects.get(id=dataset_id)
    db_categories = CategoryModel.objects(id__in=categories, deleted=False) \
        .only(*CategoryModel.COCO_PROPERTIES)
    db_images = ImageModel.objects(
        deleted=False, dataset_id=dataset.id).only(
        *ImageModel.COCO_PROPERTIES)
    db_annotations = AnnotationModel.objects(
        deleted=False, category_id__in=categories)

    # Iterate through all categories to pick a color for each one
    category_names = []
    label_colors = [(0, 0, 0)]
    for category in fix_ids(db_categories):
        category_names.append(category.get('name'))
        label_colors.append( tuple(np.random.random(size=3) * 255))

    # Get the path
    # Generate a unique name for the zip 
    timestamp = time.time()
    directory = f"{dataset.directory}.exports/"
    zip_path = f"{directory}SemanticSeg-{timestamp}.zip"

    if not os.path.exists(directory):
        os.makedirs(directory)

    # Initiate progress counter
    progress = 0
    total_images = len(db_images)

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        # Iterate through each image and
        # save its corresponding semantic segmentation
        for image in db_images:
            image = fix_ids(image)
            width = image.get('width')
            height = image.get('height')

            img_annotations = db_annotations.filter(image_id=image.get('id'))\
            .only(*AnnotationModel.COCO_PROPERTIES)

            final_image_array = np.zeros((height, width))
            category_index = 1
            found_categories = []

            for category in fix_ids(db_categories):
                category_annotations = img_annotations\
                    .filter(category_id=category.get('id'))\
                    .only(*AnnotationModel.COCO_PROPERTIES)
        
                if category_annotations.count() == 0:
                    category_index += 1

                    continue
                found_categories.append(category_index)
                category_annotations = fix_ids(category_annotations)

                for annotation in category_annotations:
                    has_segmentation = len(annotation.get('segmentation', [])) > 0
                    has_rle_segmentation = annotation.get('rle', {}) != {}

                    if has_rle_segmentation:
                        # Convert uncompressed RLE to encoded RLE mask
                        rles = mask.frPyObjects(dict(annotation.get('rle', {})), height, width)
                        rle = mask.merge([rles])
                        # Extract the binary mask
                        bin_mask = mask.decode(rle)
                        idx = bin_mask == 1
                        final_image_array[idx] = category_index
                    elif has_segmentation:
                        # Convert into rle
                        rles = mask.frPyObjects(list(annotation.get('segmentation')), height, width)
                        rle = mask.merge(rles)
                        # Extract the binary mask
                        bin_mask = mask.decode(rle)
                        idx = bin_mask == 1
                        final_image_array[idx] = category_index
                category_index += 1
            # Generate a RGB image to be saved in the zip
            r = np.zeros_like(final_image_array).astype(np.uint8)
            g = np.zeros_like(final_image_array).astype(np.uint8)
            b = np.zeros_like(final_image_array).astype(np.uint8)
            for l in found_categories:
                idx = final_image_array == l
                x, y, z = label_colors[l]
                r[idx] = x
                g[idx] = y
                b[idx] = z
            rgb = np.stack([r, g, b], axis=2)
            image_io = io.BytesIO()
            Image.fromarray(rgb.astype('uint8')).save(image_io, "PNG", quality=95)

            # Write the image to the zip
            task.info(f"Writing image {image.get('id')} to the zipfile")
            zip_file.writestr(image.get('file_name'), image_io.getvalue())

            # Update progress
            progress+=1
            task.set_progress((progress / total_images) * 100, socket=socket)

        zip_file.close()

    task.info("Finished Generating Image segmentation... Sending the zipfile")

    export = ExportModel(dataset_id=dataset.id, path=zip_path, 
                tags=["SemanticSeg", *category_names])
    export.save()

__all__ = ["export_semantic_segmentation"]
