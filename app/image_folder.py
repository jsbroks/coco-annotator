from watchdog.events import FileSystemEventHandler

from .models import ImageModel

import os


PATTERN = (".gif", ".png", ".jpg", ".jpeg", ".bmp")


def load_images(directory):
    print("Checking all images in dataset directory (may take a few minutes)")
    for root, dirs, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)

            if path.endswith(PATTERN):
                db_image = ImageModel.objects(path=path).first()

                if db_image is None:
                    print("New file found: {}".format(path))
                    ImageModel.create_from_path(path).save()


class ImageFolderHandler(FileSystemEventHandler):

    def __init__(self, pattern=None):
        self.pattern = pattern or (".gif", ".png", ".jpg", ".jpeg", ".bmp")

    def on_any_event(self, event):

        path = event.dest_path if event.event_type == "moved" else event.src_path
        if not event.is_directory and path.endswith(self.pattern):

            if event.is_directory:
                return None

            image = ImageModel.objects(path=event.src_path).first()

            if image is None and event.event_type != 'deleted':
                print("Adding new file to database: {}".format(path), flush=True)
                ImageModel.create_from_path(path).save()

            elif event.event_type == 'moved':
                print("Moving image from {} to {}".format(event.src_path, path), flush=True)
                image.update(path=path)

            elif event.event_type == 'deleted':
                print("Deleting image from  database: {}".format(path), flush=True)
                ImageModel.objects(path=path).delete()
