from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config
from .models import ImageModel

import time
import threading


class ImageFolderHandler(FileSystemEventHandler):

    PREFIX = "[File Watcher]"

    def __init__(self, pattern=None):
        self.pattern = pattern or (".gif", ".png", ".jpg", ".jpeg", ".bmp")

    def on_any_event(self, event):

        path = event.dest_path if event.event_type == "moved" else event.src_path
        self._log(f'File {path} for {event.event_type}')
        
        # Check if thumbnails directory
        folders = path.split('/')
        i = folders.index("datasets")
        if i+1 < len(folders) and folders[i+1] == "_thumbnails":
            return
        
        if not event.is_directory and path.lower().endswith(self.pattern):

            image = ImageModel.objects(path=event.src_path).first()

            if image is None and event.event_type != 'deleted':
                self._log(f'Adding new file to database: {path}')
                ImageModel.create_from_path(path).save()

            elif event.event_type == 'moved':
                self._log(f'Moving image from {event.src_path} to {path}')
                image.update(path=path)

            elif event.event_type == 'deleted':
                self._log(f'Deleting image from database {path}')
                ImageModel.objects(path=path).delete()

    def _log(self, message):
        print(f'{self.PREFIX} {message}', flush=True)

def run_watcher():
    observer = Observer()
    observer.schedule(ImageFolderHandler(), Config.DATASET_DIRECTORY, recursive=True)
    observer.start()
