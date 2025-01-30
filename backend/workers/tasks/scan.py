from database import (
    ImageModel,
    TaskModel,
    DatasetModel
)

from celery import shared_task
from ..socket import create_socket
from .thumbnails import thumbnail_generate_single_image
from pathlib import PurePath
import os


@shared_task
def scan_dataset(task_id, dataset_id):

    task = TaskModel.objects.get(id=task_id)
    dataset = DatasetModel.objects.get(id=dataset_id)

    task.update(status="PROGRESS")
    socket = create_socket()
    
    directory = dataset.directory
    toplevel = list(os.listdir(directory))
    task.info(f"Scanning {directory} ")

    count = 0
    for root, dirs, files in os.walk(directory):
        task.info(f"Scanning {directory} at {root}")
        try:
            if root in toplevel:
                youarehere = toplevel.index(root.split('/')[-1])
                progress = int(((youarehere)/len(toplevel))*100)
            else:
                progress = len(toplevel)/100
                youarehere = root
            task.set_progress(progress, socket=socket)
        except Exception as ee:
            task.warning(f"Could not set progress {youarehere} because of {ee}")

        if root.split('/')[-1].startswith('.'):
            task.debug(f"Ignoring hidden root: {root}")
            continue
        
        for file in files:
            path = os.path.join(root, file)
            relpath = str(PurePath(path).relative_to(directory))
            if path.endswith(ImageModel.PATTERN):
                db_image = ImageModel.objects(relpath=relpath).first()

                if db_image is not None:
                    task.debug(f"File already exists: {relpath}")
                    continue

                try:
                    ImageModel.create_from_path(path, dataset.id).save()
                    count += 1
                    task.info(f"New file found: {path}")
                except Exception as e:
                    task.warning(f"Could not read {path} because of {e}")

    [thumbnail_generate_single_image.delay(image.id) for image in ImageModel.objects(regenerate_thumbnail=True).all()]

    task.info(f"Created {count} new image(s)")
    task.set_progress(100, socket=socket)


__all__ = ["scan_dataset"]