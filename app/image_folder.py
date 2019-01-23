from watchdog.events import FileSystemEventHandler

from .models import ImageModel


class ImageFolderHandler(FileSystemEventHandler):

    def __init__(self, pattern=None):
        self.pattern = pattern or (".gif", ".png", ".jpg", ".jpeg", ".bmp")

    def on_any_event(self, event):

        path = event.dest_path if event.event_type == "moved" else event.src_path

        # Check if thumbnails directory
        folders = path.split('/')
        i = folders.index("datasets")
        if i+1 < len(folders) and folders[i+1] == "_thumbnails":
            return
        
        if not event.is_directory and path.lower().endswith(self.pattern):

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
