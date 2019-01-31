import threading
import queue
import cv2
import pymongo
import numpy as np
from ..models import ImageModel, AnnotationModel, CategoryModel
from skimage.measure import compare_ssim
from ..util.annotation_util import (
    segmentation_equal, extract_cropped_patch, segmentation_to_contours,
    bbox_for_contours)
from concurrent.futures import Future, wait
from ..util.coco_util import get_annotations_iou
from ..util.concurrency_util import ExceptionLoggingThreadPoolExecutor
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
    def submit(cls, image_id, annotation_ids, wait_for_next=False,
               wait_for_prev=False):
        """
        Submit a (changed) annotation to the queue for processing;
        if wait_for_next or wait_for_prev is set, the method will not
        return until the next and/or previous images have been processed
        """
        if cls.queue is not None:
            next_complete = Future()
            prev_complete = Future()
            cls.queue.put((image_id, annotation_ids,
                           prev_complete, next_complete))

            if wait_for_next or wait_for_prev:
                awaited = list()
                if wait_for_next:
                    awaited.append(next_complete)
                if wait_for_prev:
                    awaited.append(next_complete)
                wait(awaited, timeout=3)

    @classmethod
    def start(cls, max_workers=10, max_queue_size=32,
              max_mismatched=10, diff_threshold=0.01, verbose=False,
              logger=None):
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
        cls.executor = ExceptionLoggingThreadPoolExecutor(
            thread_name_prefix=cls.__name__,
            max_workers=max_workers,
            logger=logger)
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

        index = images.index(image_model)
        if index == 0:
            return ([], images)
        elif index == len(images) - 1:
            return (list(reversed(images)), [])
        else:
            return (
                list(images.islice(0, index, reverse=True)),
                list(images.islice(index + 1)))

    @classmethod
    def get_cvimg(cls, image_model):
        if '_cv2_img' not in image_model.__dict__:
            image_model._cv2_img = cv2.imread(image_model.path)
        return image_model._cv2_img

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
            (image_id, annotation_ids,
             prev_complete, next_complete) = cls.queue.get()
            if annotation_ids is not None:
                cls.executor.submit(cls.propagate_annotations,
                                    image_id=image_id,
                                    annotation_ids=annotation_ids,
                                    prev_complete=prev_complete,
                                    next_complete=next_complete)

    @classmethod
    def compare_and_copy(cls, annotations, category_names, image_from,
                         images, masks, bboxes, patches, first_complete):
        """
        Compares the provided annotation against all images in the
        images iterable and copies the annotation to those images where
        it is a suitable match (and no existing annotation already covers it)
        """
        replaced = [0] * len(annotations)
        matched = [0] * len(annotations)
        mismatched = [0] * len(annotations)
        finished = [False] * len(annotations)

        if not images:
            first_complete.set_result(True)

        for index, image_to in enumerate(images):
            if index > 0:
                first_complete.set_result(True)

            if np.alltrue(finished):
                break

            if image_to.id == image_from.id:
                continue
            # skip images of different size
            if image_to.width != image_from.width \
                    or image_to.height != image_from.height:
                continue

            to_cvimg = cls.get_cvimg(image_to)

            annotations_ids_to_copy = list()
            existing_annotations_replaced = list()
            for i, annotation in enumerate(annotations):
                if finished[i]:
                    continue

                category_name = category_names[i]
                if mismatched[i] > cls.max_mismatched:
                    if cls.verbose:
                        cls.log(
                            f"Exceeded {cls.max_mismatched} consecutive "
                            f"mismatched images for {category_name}"
                            f"({annotation.id}); stopping match test")
                    finished[i] = True
                    continue

                to_patch = extract_cropped_patch(
                    to_cvimg, masks[i], bboxes[i])

                score, _ = compare_ssim(
                    patches[i], to_patch, full=True, multichannel=True)
                if cls.verbose:
                    msg = (f"Annotation {category_name}({annotation.id}) vs. "
                           f"image {image_to.file_name} score: {score:.5f}: ")

                if (1.0 - score) > cls.diff_threshold:
                    mismatched[i] += 1
                    if cls.verbose:
                        msg += "mismatch"
                        cls.log(msg)
                    continue

                # look for existing annotations on the same image
                # having the same category; only add this new annotation
                # if it has greater area than any existing
                existing_is_better = False
                existing_replaced = list()
                for existing_ann in AnnotationModel.objects(
                        image_id=image_to.id,
                        category_id=annotation.category_id,
                        deleted=False).all():
                    existing_iou = get_annotations_iou(
                        annotation, existing_ann)
                    if existing_iou > 0:
                        if existing_ann.area >= annotation.area:
                            if cls.verbose:
                                cls.log(
                                    "Found existing intersecting annotation "
                                    f"{existing_ann.id} "
                                    "with greater or equal area for "
                                    f"{category_name} on image "
                                    f"{image_to.file_name}; skipping")
                            existing_is_better = True
                            break
                        else:
                            existing_replaced.append(existing_ann)

                if existing_is_better:
                    mismatched[i] += 1
                    if cls.verbose:
                        msg += "match, less coverage than existing"
                        cls.log(msg)
                    continue
                else:
                    if cls.verbose:
                        msg += "match, copying"
                        cls.log(msg)
                    existing_annotations_replaced += existing_replaced
                    replaced[i] += len(existing_replaced)

                mismatched[i] = 0
                matched[i] += 1
                annotations_ids_to_copy.append(annotation.id)

            image_to.copy_annotations(
                AnnotationModel.objects(id__in=annotations_ids_to_copy))

            for to_remove in existing_annotations_replaced:
                to_remove.delete()

        if len(images) == 1:
            first_complete.set_result(True)

        if cls.verbose:
            msg = ""
            for i, annotation in enumerate(annotations):
                msg += (f"\ncopied {category_names[i]}({annotation.id}) "
                        f"to {matched[i]} images")
                if replaced[i]:
                    msg += f", replacing {replaced[i]} existing annotations"
            cls.log(msg)

    @classmethod
    def propagate_annotations(cls, image_id, annotation_ids,
                              prev_complete, next_complete):
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
            cls.log(f"Processing annotation ids {annotation_ids}")

        annotations = AnnotationModel.objects(id__in=annotation_ids).all()
        if annotations is None:
            cls.log(f"Error: no annotations matching ids {annotation_ids}")
            return

        category_names = list()
        masks = list()
        bboxes = list()
        patches = list()

        image_from = ImageModel.objects(id=image_id).first()
        from_cvimg = cls.get_cvimg(image_from)

        for annotation in annotations:
            category_names.append(CategoryModel.objects(
                id=annotation.category_id).first().name)

            contours = segmentation_to_contours(annotation.segmentation)
            mask = np.zeros(
                (from_cvimg.shape[0], from_cvimg.shape[1]),
                dtype=np.uint8)
            mask = cv2.drawContours(mask, contours, -1, 1, -1)
            masks.append(mask)

            bbox = bbox_for_contours(contours)
            bboxes.append(bbox)

            patch = extract_cropped_patch(
                from_cvimg, mask, bbox)
            patches.append(patch)

        images_before, images_after = cls.images_before_and_after(image_from)

        cls.executor.submit(cls.compare_and_copy,
                            annotations=annotations,
                            category_names=category_names,
                            image_from=image_from,
                            images=images_after,
                            masks=masks, bboxes=bboxes, patches=patches,
                            first_complete=next_complete)

        cls.executor.submit(cls.compare_and_copy,
                            annotations=annotations,
                            category_names=category_names,
                            image_from=image_from,
                            images=images_before,
                            masks=masks, bboxes=bboxes, patches=patches,
                            first_complete=prev_complete)
