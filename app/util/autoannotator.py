import threading
import queue
import cv2
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
    def submit(cls, annotation_id):
        if cls.queue is not None:
            cls.queue.put(annotation_id)

    @classmethod
    def start(cls, max_workers=10, max_queue_size=32,
              max_mismatched=10, diff_threshold=0.01, verbose=False):
        cls.queue = queue.Queue(maxsize=max_queue_size)
        cls.executor = ThreadPoolExecutor(
            thread_name_prefix=cls.__name__,
            max_workers=max_workers)
        cls.executor.submit(cls.do_propagate_annotations)
        cls.max_mismatched = max_mismatched
        cls.diff_threshold = diff_threshold
        cls.verbose = verbose
        cls.enabled = True

    @classmethod
    def stop(cls):
        """
        """
        cls.executor.shutdown()

    @classmethod
    def do_propagate_annotations(cls, verbose=False):
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
    def propagate_annotation(cls, annotation_id):
        print(f"Processing annotation id {annotation_id}", flush=True)

        annotation = AnnotationModel.objects(id=annotation_id).first()
        if annotation is None:
            print(f"No annotation matching id {annotation_id}", flush=True)
            return

        image_from = ImageModel.objects(id=annotation.image_id).first()
        img = cv2.imread(image_from.path)
        mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        contours = segmentation_to_contours(annotation.segmentation)
        mask = cv2.drawContours(mask, contours, -1, 1, -1)
        
        patch = cv2.bitwise_and(img, img, mask=mask)
        (x, y, w, h) = bbox_for_contours(contours)
        patch = patch[y:y + h, x:x + w]

        dataset_id = image_from.dataset_id
        images = list(ImageModel.objects(
            dataset_id=dataset_id,
            deleted=False).order_by('file_name').all())
        if cls.verbose:
            print(f"Comparing patch against {len(images)} images in dataset "
                  f"{image_from.dataset_id}...", flush=True)
        # test all other images in the same dataset, ordered by filename
        # stop when we've failed to match MAX_MISMATCHED in a row
        mismatched = 0
        for image_to in images:
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
                print(f"Annotation {annotation_id} vs. "
                      f"image {image_to.file_name} score = {score}",
                      flush=True)
            
            if (1.0 - score) > cls.diff_threshold:
                mismatched += 1
                if mismatched > cls.max_mismatched:
                    if cls.verbose:
                        print(f"Exceeded {cls.max_mismatched} consecutive "
                              f"mismatched images; aborting further attempts")
                    return
                continue
            if cls.verbose:
                print(f"Annotation {annotation_id} matches "
                      f"image {image_to.file_name}; copying...", flush=True)
            mismatched = 0
            image_to.copy_annotations(
                AnnotationModel.objects(id=annotation_id))
