from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import Config
from database import ImageModel

import re


class ImageFolderHandler(FileSystemEventHandler):

    PREFIX = "[File Watcher]"

    def __init__(self, pattern=None):
        self.pattern = pattern or ImageModel.PATTERN

    def on_any_event(self, event):

        path = event.dest_path if event.event_type == "moved" else event.src_path
                
        if (
            event.is_directory
            # check if its a hidden file
            or bool(re.search(r'\/\..*?\/', path))
            or not path.lower().endswith(self.pattern)
        ):
            return
        
        self._log(f'File {path} for {event.event_type}')
        
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
