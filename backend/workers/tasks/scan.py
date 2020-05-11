from database import (
    ImageModel,
    TaskModel,
    DatasetModel
)

from celery import shared_task
from ..socket import create_socket
from .thumbnails import thumbnail_generate_single_image

import os


@shared_task
def scan_dataset(task_id, dataset_id):

    task = TaskModel.objects.get(id=task_id)
    dataset = DatasetModel.objects.get(id=dataset_id)

    task.update(status="PROGRESS")
    socket = create_socket()
    
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

        if root.split('/')[-1].startswith('.'):
            continue
        
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

    [thumbnail_generate_single_image.delay(image.id) for image in ImageModel.objects(regenerate_thumbnail=True).all()]

    task.info(f"Created {count} new image(s)")
    task.set_progress(100, socket=socket)


__all__ = ["scan_dataset"]