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
        path = event.src_path
        if not event.is_directory and path.endswith(self.pattern):

            if event.is_directory:
                return None

            print("{} {}".format(event.event_type, path), flush=True)

            if event.event_type == 'created':
                if ImageModel.objects(path=path).first() is None:
                    ImageModel.create_from_path(path).save()

            elif event.event_type == 'moved':
                image = ImageModel.objects(path=path).first()
                image.update(path=event.dest_path)

            elif event.event_type == 'deleted':
                ImageModel.objects(path=path).delete()
