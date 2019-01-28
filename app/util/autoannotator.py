import threading
import queue
import cv2
import pymongo
import numpy as np
from ..models import ImageModel, AnnotationModel
from skimage.measure import compare_ssim
from ..util.annotation_util import (
    segmentation_equal, extract_patch, segmentation_to_contours,
    bbox_for_contours)
from concurrent.futures import ThreadPoolExecutor


class Autoannotator:
    executor = None
    queue = None
    enabled = False
    verbose = False

    @classmethod
    def log(cls, msg):
        print(f"[{cls.__name__}] {msg}", flush=True)

    @classmethod
    def submit(cls, annotation_id):
        """
        Submit a (changed) annotation to the queue for processing
        """
        if cls.queue is not None:
            cls.queue.put(annotation_id)

    @classmethod
    def start(cls, max_workers=10, max_queue_size=32,
              max_mismatched=10, diff_threshold=0.01, verbose=False):
        """
        Start the autoannotator background process;

        @max_workers: max workers alloted to the thread pool executor
        @max_queue_size: max size of the queue for annotations to be processed
        @max_mismatched: max number of consecutively mismatched images to
            be encountered before matching is aborted for the given annotation
        @diff_threshold: if the ssim score when comparing the annotation patch
            against the same patch in another image is greater than 
            (1.0 - diff_threshold), the patch is considered a match--and the
            annotation is copied
        """
        if cls.executor is not None:
            cls.executor.shutdown()
            del cls.executor
            del cls.queue
        cls.queue = queue.Queue(maxsize=max_queue_size)
        cls.max_mismatched = max_mismatched
        cls.diff_threshold = diff_threshold
        cls.verbose = verbose
        cls.executor = ThreadPoolExecutor(
            thread_name_prefix=cls.__name__,
            max_workers=max_workers)
        cls.executor.submit(cls.do_propagate_annotations)
        cls.enabled = True

    @classmethod
    def do_propagate_annotations(cls):
        """
        Performs automatic propagation of annotations by comparing
        newly added/updated annotations: whenever
        the annotation's patch is sufficiently close to the
        corresponding patch on another image in the dataset, the
        annotation is copied to this other image
        """
        while True:
            annotation_id = cls.queue.get()
            if annotation_id is not None:
                cls.executor.submit(cls.propagate_annotation, *[annotation_id])

    @classmethod
    def compare_and_copy(cls, annotation, image_from,
                         images, mask, bbox, patch):
        if cls.verbose:
            print(f"Comparing {annotation.id} vs. "
                  f"{len(images)} images", flush=True)

        mismatched = 0
        x, y, w, h = bbox
        for image_to in images:
            if image_to.id == image_from.id:
                continue
            # skip images of different size
            if image_to.width != image_from.width \
                    or image_to.height != image_from.height:
                continue
            cvimg = cv2.imread(image_to.path)
            img_patch = cv2.bitwise_and(cvimg, cvimg, mask=mask)
            img_patch = img_patch[y:y + h, x:x + w]
            score, _ = compare_ssim(
                patch, img_patch, full=True, multichannel=True)
            if cls.verbose:
                cls.log(f"Annotation {annotation.id} vs. "
                        f"image {image_to.file_name} score = {score}")

            if (1.0 - score) > cls.diff_threshold:
                mismatched += 1
                if mismatched > cls.max_mismatched:
                    if cls.verbose:
                        cls.log(f"Exceeded {cls.max_mismatched} consecutive "
                                f"mismatched images; aborting further attempts")
                    return
                continue
            if cls.verbose:
                cls.log(f"Annotation {annotation.id} matches "
                        f"image {image_to.file_name}; copying...")
            mismatched = 0
            image_to.copy_annotations(
                AnnotationModel.objects(id=annotation.id))

    @classmethod
    def propagate_annotation(cls, annotation_id):
        """
        Searches consecutive images within the same dataset both before and 
        after the image containing the specified annotation (ordered by 
        file_name), testing the masked patch covered by the specified
        annotation.
        The masked patch is compared between the original image
        and the other image using 'skimage.compare_ssim'; if the score is
        within a configurable tolerance, the patch is condiered a 'match',
        and the annotation is copied to the other image.
        If a configurable number of mismatches occur consecutively, the 
        matching is abandonded for the current annotation.
        """
        if cls.verbose:
            cls.log(f"Processing annotation id {annotation_id}")

        annotation = AnnotationModel.objects(id=annotation_id).first()
        if annotation is None:
            cls.log(f"Error: no annotation matching id {annotation_id}")
            return

        image_from = ImageModel.objects(id=annotation.image_id).first()
        img = cv2.imread(image_from.path)
        mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        contours = segmentation_to_contours(annotation.segmentation)
        mask = cv2.drawContours(mask, contours, -1, 1, -1)

        patch = cv2.bitwise_and(img, img, mask=mask)
        bbox = bbox_for_contours(contours)
        (x, y, w, h) = bbox
        patch = patch[y:y + h, x:x + w]

        dataset_id = image_from.dataset_id

        if cls.verbose:
            cls.log("Searching for images with file_name greater than "
                    f"{image_from.file_name}")
        images_after = list(ImageModel.objects(
            dataset_id=dataset_id,
            file_name__gt=image_from.file_name,
            deleted=False).order_by('+file_name').all())

        cls.executor.submit(cls.compare_and_copy,
                            annotation=annotation, image_from=image_from,
                            images=images_after,
                            mask=mask, bbox=bbox, patch=patch)

        if cls.verbose:
            cls.log("Searching for images with file_name less than "
                    f"{image_from.file_name}")
        images_before = list(ImageModel.objects(
            dataset_id=dataset_id,
            file_name__lt=image_from.file_name,
            deleted=False).order_by('-file_name').all())

        cls.executor.submit(cls.compare_and_copy,
                            annotation=annotation, image_from=image_from,
                            images=images_before,
                            mask=mask, bbox=bbox, patch=patch)
