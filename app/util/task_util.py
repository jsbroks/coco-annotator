from ..models import ImageModel

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


def import_coco_func(task, socket, dataset):
    pass

