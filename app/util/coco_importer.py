import threading
import json
import imantics as im
from ..models import (
    ImageModel, AnnotationModel, CategoryModel,
    DatasetModel, CocoImportModel)
from concurrent.futures import wait
from ..config import Config
from .coco_util import get_segmentation_area_and_bbox
from .concurrency_util import ExceptionLoggingThreadPoolExecutor


class CocoImporter:
    executor = ExceptionLoggingThreadPoolExecutor(
        thread_name_prefix=__name__,
        max_workers=Config.COCO_IMPORTER_MAX_WORKERS)
    verbose = Config.COCO_IMPORTER_VERBOSE
    image_batch_size = Config.COCO_IMPORTER_IMAGE_BATCH_SIZE
    annotation_batch_size = Config.COCO_IMPORTER_ANNOTATION_BATCH_SIZE

    @classmethod
    def import_coco(cls, coco_raw, dataset_id, creator):
        """
        Submit a new coco file for import
        """
        db_coco_import = CocoImportModel(creator=creator).save()

        coco_import = CocoImport(
            coco_raw, dataset_id, db_coco_import.id, creator,
            verbose=cls.verbose)

        cls.executor.submit(
            coco_import.perform_import, executor=cls.executor)
        
        return db_coco_import.id


class CocoImport:
    """
    Represents a single import attempt
    """
    def __init__(self, coco_raw, dataset_id, import_id, creator,
                 verbose=False):
        self.coco_json = json.load(coco_raw)
        self.dataset_id = dataset_id
        self.import_id = import_id
        self.creator = creator
        self.verbose = verbose
        self.items_complete = 0
        self.items_total = 1
        self.items_complete_lock = threading.Lock()
        self.errors = list()

    def log(self, msg):
        """
        Log a message from this import instance
        """
        print(f"[{self.__class__.__name__}:{self.import_id}] {msg}",
              flush=True)

    def increment_completion(self, count, update_progress=False):
        """
        Adds 'count' to the total completed items count, and optionally updates
        progress in the db; adding to more than items_total is safely handled
        """
        with self.items_complete_lock:
            self.items_complete = min(
                self.items_complete + count,
                self.items_total)

        if update_progress:
            self.update_progress()

    def update_progress(self):
        """
        Updates progress and errors for this import in the db
        """
        with self.items_complete_lock:
            progress = float(self.items_complete) / float(self.items_total)

        if self.verbose:
            self.log(f"Completed {self.items_complete} / {self.items_total};"
                     f" updating progress to {progress:.04f}")
        coco_import = CocoImportModel.objects(id=self.import_id).first()
        coco_import.update(
            set__progress=progress,
            set__errors=self.errors)

    def perform_import(self, executor):
        """
        Perform the coco import
        """
        if self.verbose:
            self.log("Beginning import")

        dataset = DatasetModel.objects(id=self.dataset_id).first()
        images = ImageModel.objects(dataset_id=self.dataset_id)
        categories = CategoryModel.objects

        coco_images = self.coco_json.get('images')
        coco_annotations = self.coco_json.get('annotations')
        coco_categories = self.coco_json.get('categories')

        if self.verbose:
            self.log(f"Importing {len(coco_categories)} categories, "
                     f"{len(coco_images)} images, and "
                     f"{len(coco_annotations)} annotations")

        self.items_total = 2 * len(coco_images)
        self.items_total += len(coco_annotations)
        self.items_total += len(coco_categories)

        categories_id = {}
        images_id = {}

        # Create any missing categories
        for category in coco_categories:
            category_name = category.get('name')
            if self.verbose:
                self.log("Loading category {category_name}")

            category_id = category.get('id')
            category_model = categories.filter(
                name__exact=category_name).all()

            if not category_model:
                self.errors.append({
                    'category': category_name,
                    'message': 'Creating category ' + category_name + '.'
                })

                new_category = CategoryModel(
                    name=category_name, color=im.Color.random().hex)
                new_category.save()
                categories_id[category_id] = new_category.id
                if self.verbose:
                    self.log("Category not found! (Creating new one)")
                continue

            if len(category_model) > 1:
                self.errors.append({
                    'category': category_name,
                    'message': 'To many categories found with file name.'
                })
                continue

            category_model = category_model[0]
            categories_id[category_id] = category_model.id

        self.increment_completion(len(coco_categories), update_progress=True)

        # Add any new categories to dataset
        for value in categories_id.values():
            if value not in dataset.categories:
                dataset.categories.append(value)

        dataset.update(set__categories=dataset.categories)

        if len(coco_images) > CocoImporter.image_batch_size:
            # split images up into batches, import them in parallel
            imports = list()
            remaining = coco_images
            while remaining:
                if len(remaining) > CocoImporter.image_batch_size:
                    subset = remaining[
                        0:CocoImporter.image_batch_size]
                    remaining = remaining[
                        CocoImporter.image_batch_size:]
                else:
                    subset = remaining
                    remaining = []
                imports.append(
                    executor.submit(self.import_images, coco_images=subset,
                                    images=images, images_id=images_id))
            # process all images before moving on to annotations
            while True:
                _, unfinished = wait(imports, timeout=3)
                self.update_progress()
                if not unfinished:
                    break
        else:
            self.import_images(coco_images, images, images_id)

        self.update_progress()

        if len(coco_annotations) > CocoImporter.annotation_batch_size:
            # split annotations up into batches, import them in parallel
            imports = list()
            remaining = coco_annotations
            while remaining:
                if len(remaining) > CocoImporter.annotation_batch_size:
                    subset = remaining[
                        0:CocoImporter.annotation_batch_size]
                    remaining = remaining[
                        CocoImporter.annotation_batch_size:]
                else:
                    subset = remaining
                    remaining = []

                imports.append(
                    executor.submit(
                        self.import_annotations, coco_annotations=subset,
                        categories_id=categories_id, images_id=images_id))
            while True:
                _, unfinished = wait(imports, timeout=3)
                self.update_progress()
                if not unfinished:
                    break
        else:
            self.import_annotations(coco_annotations, categories_id, images_id)

        images_and_categories = list(images_id.values())
        # update the category ids for the images
        if len(images_and_categories) > CocoImporter.image_batch_size:
            # split images up into batches, import them in parallel
            imports = list()
            remaining = images_and_categories
            while remaining:
                if len(remaining) > CocoImporter.image_batch_size:
                    subset = remaining[
                        0:CocoImporter.image_batch_size]
                    remaining = remaining[
                        CocoImporter.image_batch_size:]
                else:
                    subset = remaining
                    remaining = []
                imports.append(
                    executor.submit(self.update_categories,
                                    images_and_categories=subset))
            # process all images before moving on to annotations
            while True:
                _, unfinished = wait(imports, timeout=3)
                self.update_progress()
                if not unfinished:
                    break
        else:
            self.update_categories(images_and_categories)

        self.increment_completion(count=self.items_total, update_progress=True)
        # release resources
        self.coco_json = None

    def import_images(self, coco_images, images, images_id):
        """
        Import/load all images in the provided subset
        """
        # Find all images
        for image in coco_images:
            image_id = image.get('id')
            image_filename = image.get('file_name')

            if self.verbose:
                self.log(f"Loading image {image_filename}")
            image_model = images.filter(file_name__exact=image_filename).all()

            self.increment_completion(1)

            if not image_model:
                self.errors.append({'file_name': image_filename,
                                    'message': 'Could not find image.'})
                continue

            if len(image_model) > 1:
                self.errors.append({
                    'file_name': image_filename,
                    'message': ('To many images found with '
                                'the same file name.')})
                continue

            image_model = image_model[0]
            if self.verbose:
                self.log(f"Found image {image_filename}")
            images_id[image_id] = (image_model, list())

    def import_annotations(self, coco_annotations, categories_id, images_id):
        """
        Import all annotations in the provided subset
        """
        for annotation in coco_annotations:
            image_id = annotation.get('image_id')
            category_id = annotation.get('category_id')
            segmentation = annotation.get('segmentation', [])
            # is_crowd = annotation.get('iscrowed', False)

            self.increment_completion(1)

            if not segmentation:
                continue

            if self.verbose:
                self.log("Loading annotation data "
                         f"(image:{image_id} category:{category_id})")

            try:
                image_model, image_category_ids = images_id[image_id]
                category_model_id = categories_id[category_id]
            except KeyError:
                continue

            # Check if annotation already exists
            annotation = AnnotationModel.objects(image_id=image_model.id,
                                                 category_id=category_model_id,
                                                 segmentation=segmentation,
                                                 deleted=False).first()
            # Create annotation
            if annotation is None:

                if self.verbose:
                    self.log("Creating Annotation for "
                             f"(image:{image_id} category:{category_id})")
                annotation = AnnotationModel(image_id=image_model.id)
                annotation.category_id = category_model_id
                # annotation.iscrowd = is_crowd
                annotation.segmentation = segmentation

                area, bbox = get_segmentation_area_and_bbox(
                    segmentation, image_model.height, image_model.width)
                annotation.area = area
                annotation.bbox = list(bbox)
                annotation.color = im.Color.random().hex
                annotation.save()

                image_category_ids.append(category_id)

            elif self.verbose:
                self.log("Annotation for "
                         f"(image:{image_id} category:{category_id}) "
                         "already exists")

    def update_categories(self, images_and_categories):
        """
        Updates the categories on the provided set of models
        """
        for image_model, category_ids in images_and_categories:
            all_category_ids = list(image_model.category_ids)
            all_category_ids += category_ids
            image_model.update(
                set__annotated=True,
                set__category_ids=list(set(all_category_ids)))

            self.increment_completion(1)
