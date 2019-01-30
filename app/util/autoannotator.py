import threading
import queue
import cv2
import pymongo
import numpy as np
from ..models import ImageModel, AnnotationModel, CategoryModel
from skimage.measure import compare_ssim
from ..util.annotation_util import (
    segmentation_equal, extract_patch, segmentation_to_contours,
    bbox_for_contours)
from concurrent.futures import ThreadPoolExecutor
from ..util.coco_util import get_annotations_iou
import sortedcontainers


class Autoannotator:
    executor = None
    queue = None
    enabled = False
    verbose = False
    image_cache = dict()
    image_cache_lock = threading.Lock()

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
    def images_before_and_after(cls, image_model):
        """
        Returns 2 interators: the first is a reversed iterator
        to images before the provided image (by filename), and
        the second is a forward iterator to images after the
        provided image (by filename)
        """
        images = None
        with cls.image_cache_lock:
            images = cls.image_cache.get(image_model.dataset_id)
            if images is None:
                try:
                    if cls.verbose:
                        cls.log("Adding cached list for dataset id "
                                f"{image_model.dataset_id}")
                    images = sortedcontainers.SortedList(
                        ImageModel.objects(
                            dataset_id=image_model.dataset_id,
                            deleted=False).order_by('+file_name').all(),
                        key=lambda x: x.file_name)
                    cls.image_cache[image_model.dataset_id] = images
                    if cls.verbose:
                        cls.log("Cached list for dataset id "
                                f"{image_model.dataset_id} with {len(images)} "
                                "images")
                except Exception as e:
                    if cls.verbose:
                        cls.log("Error caching list for dataset id "
                                f"{image_model.dataset_id}: {e}")
                    raise e

        try:
            index = images.index(image_model)
            if cls.verbose:
                cls.log(f"Found {image_model.file_name} at index {index}")
            return (
                images.islice(0, index, reverse=True),
                images.islice(index + 1))
        except Exception as e:
            cls.log(f"Error splitting image list: {e}")
            raise e

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
    def compare_and_copy(cls, annotation, category_name, image_from,
                         images, mask, bbox, patch):
        """
        Compares the provided annotation against all images in the
        images iterable and copies the annotation to those images where
        it is a suitable match (and no existing annotation already covers it)
        """
        replaced = 0
        matched = 0
        mismatched = 0
        x, y, w, h = bbox
        for image_to in images:
            if image_to.id == image_from.id:
                continue
            # skip images of different size
            if image_to.width != image_from.width \
                    or image_to.height != image_from.height:
                continue

            if mismatched > cls.max_mismatched:
                if cls.verbose:
                    cls.log(f"Exceeded {cls.max_mismatched} consecutive "
                            f"mismatched images for {category_name}"
                            f"({annotation.id}); stopping match test")
                return

            cvimg = cv2.imread(image_to.path)
            img_patch = cv2.bitwise_and(cvimg, cvimg, mask=mask)
            img_patch = img_patch[y:y + h, x:x + w]
            score, _ = compare_ssim(
                patch, img_patch, full=True, multichannel=True)
            if cls.verbose:
                cls.log(f"Annotation {category_name}({annotation.id}) vs. "
                        f"image {image_to.file_name} score = {score:.5f}")

            if (1.0 - score) > cls.diff_threshold:
                mismatched += 1
                continue

            # look for existing annotations on the same image
            # having the same category; only add this new annotation
            # if it has greater area than any existing
            existing_is_better = False
            existing_replaced = list()
            for existing_ann in AnnotationModel.objects(
                    image_id=image_from.id,
                    category_id=annotation.category_id,
                    deleted=False).all():
                existing_iou = get_annotations_iou(annotation, existing_ann)
                if existing_iou > 0:
                    if existing_ann.area >= annotation.area:
                        if cls.verbose:
                            cls.log("Found existing intersecting annotation "
                                    f"{existing_ann.id} "
                                    "with greater or equal area for "
                                    f"{category_name} on image "
                                    f"{image_to.file_name}; skipping")
                        existing_is_better = True
                        break
                    else:
                        existing_replaced.append(existing_ann)

            if existing_is_better:
                mismatched += 1
                continue

            if cls.verbose:
                cls.log(f"Annotation {category_name}({annotation.id}) matches "
                        f"image {image_to.file_name} with score {score:.5f}; "
                        "copying...")
            mismatched = 0
            matched += 1
            image_to.copy_annotations(
                AnnotationModel.objects(id=annotation.id))

            for to_remove in existing_replaced:
                to_remove.delete()
                replaced += 1

        msg = f"Annotation {annotation.id} was copied to {matched} images"
        if replaced:
            msg += f", replacing {replaced} existing annotations"
        cls.log(msg)

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

        category_name = CategoryModel.objects(
            id=annotation.category_id).first().name

        image_from = ImageModel.objects(id=annotation.image_id).first()
        img = cv2.imread(image_from.path)
        mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        contours = segmentation_to_contours(annotation.segmentation)
        mask = cv2.drawContours(mask, contours, -1, 1, -1)

        patch = cv2.bitwise_and(img, img, mask=mask)
        bbox = bbox_for_contours(contours)
        (x, y, w, h) = bbox
        patch = patch[y:y + h, x:x + w]

        images_before, images_after = cls.images_before_and_after(image_from)
        if cls.verbose:
            cls.log(f"Comparing annotation {category_name}({annotation_id}) "
                    "vs. images before")
        cls.executor.submit(cls.compare_and_copy,
                            annotation=annotation, 
                            category_name=category_name,
                            image_from=image_from,
                            images=images_after,
                            mask=mask, bbox=bbox, patch=patch)
        if cls.verbose:
            cls.log(f"Comparing annotation {category_name}({annotation_id}) "
                    "vs. images after")
        cls.executor.submit(cls.compare_and_copy,
                            annotation=annotation, 
                            category_name=category_name,
                            image_from=image_from,
                            images=images_before,
                            mask=mask, bbox=bbox, patch=patch)
