import queue
import os
import json
from ..models import ImageModel
from ..util.coco_util import get_image_coco
from ..util.concurrency_util import ExceptionLoggingThreadPoolExecutor


class Autoexporter:
    executor = None
    queue = None
    enabled = False
    verbose = False

    @classmethod
    def log(cls, msg):
        print(f"[{cls.__name__}] {msg}", flush=True)

    @classmethod
    def submit(cls, image_model):
        """
        Submit an image for export
        """
        if cls.queue is not None:
            cls.queue.put(image_model)

    @classmethod
    def start(cls, max_workers=1, max_queue_size=32,
              verbose=False, logger=None, extension=".coco.json"):
        """
        Start the autoexporter background progresss.

        @max_workers: max workers alloted to the thread pool executor
        @max_queue_size: max size of the queue for annotations to be processed
        """
        if cls.executor is not None:
            cls.executor.shutdown()
            del cls.executor
            del cls.queue
        cls.queue = queue.Queue(maxsize=max_queue_size)
        cls.verbose = verbose
        cls.executor = ExceptionLoggingThreadPoolExecutor(
            thread_name_prefix=cls.__name__,
            max_workers=max_workers,
            logger=logger)
        cls.executor.submit(cls.do_export_images)
        cls.enabled = True

    @classmethod
    def do_export_images(cls):
        """
        Performs automatic propagation of annotations by comparing
        newly added/updated annotations: whenever
        the annotation's patch is sufficiently close to the
        corresponding patch on another image in the dataset, the
        annotation is copied to this other image
        """
        while True:
            image_model = cls.queue.get()
            if image_model is not None:
                cls.export_image(image_model)

    @classmethod
    def export_image(cls, image_model):
        """
        Exports the specified image to coco.json file, named after
        the image and places it in the same folder as the image path.
        """
        if cls.verbose:
            cls.log(f"Processing image {image_model.file_name}...")

        coco_json = get_image_coco(image_model)
        coco_path = os.path.splitext(image_model.image_path)[0] + '.coco.json'
        json.dump(coco_json, open(coco_path, 'w'))
