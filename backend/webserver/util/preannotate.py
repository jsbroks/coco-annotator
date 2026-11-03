"""Turn model predictions into annotations (one image or a whole dataset)."""
import datetime
import logging
import threading

from mongoengine import Q

from database import (
    ActivityModel,
    AnnotationModel,
    CategoryModel,
    DatasetModel,
    ImageModel,
    TaskModel,
)
from .yolo import COCO_KEYPOINTS, COCO_SKELETON, yolo

logger = logging.getLogger('gunicorn.error')


class CategoryResolver:
    """Maps model class names to dataset categories (case-insensitive).

    With ``create_missing`` a class without a category gets one, which is
    also added to the dataset. Pose categories without keypoint labels get
    them from the model (COCO names/skeleton for 17 keypoints).
    """

    def __init__(self, dataset, create_missing=True, user=None):
        self.dataset = dataset
        self.create_missing = create_missing
        self.user = user
        self.by_name = {}
        self.skipped = set()
        self.keypoints_mismatch = set()
        self._dataset_category_ids = list(dataset.categories or [])
        for category in CategoryModel.objects(id__in=self._dataset_category_ids, deleted=False):
            self.by_name.setdefault(category.name.lower(), category)

    def _find_visible(self, name):
        """An existing category with this name the user can use."""
        query = CategoryModel.objects(name__iexact=name, deleted=False)
        if self.user is not None and not self.user.is_admin:
            query = query.filter(Q(creator=self.user.username) | Q(id__in=self._dataset_category_ids))
        return query.first()

    def get(self, name):
        key = name.lower()
        if key in self.by_name:
            return self.by_name[key]
        if not self.create_missing:
            self.skipped.add(name)
            return None

        category = self._find_visible(name)
        if category is None:
            category = CategoryModel(name=name)
            category.save()
            if self.user is not None:
                category.update(creator=self.user.username)
        if category.id not in self._dataset_category_ids:
            self._dataset_category_ids.append(category.id)
            self.dataset.update(add_to_set__categories=category.id)
        self.by_name[key] = category
        return category

    def ensure_keypoints(self, category, count, model_labels=None, model_edges=None):
        """True if keypoints of length ``count`` can be stored for it. A
        category without keypoints takes the model's names and skeleton
        (MediaPipe gives them), else COCO's for 17, else numbers."""
        labels = list(category.keypoint_labels or [])
        if not labels:
            if model_labels and len(model_labels) == count:
                labels, edges = list(model_labels), [list(e) for e in (model_edges or [])]
            elif count == len(COCO_KEYPOINTS):
                labels, edges = list(COCO_KEYPOINTS), [list(e) for e in COCO_SKELETON]
            else:
                labels, edges = [str(i + 1) for i in range(count)], []
            category.update(keypoint_labels=labels, keypoint_edges=edges)
            category.reload()
            return True
        if len(labels) != count:
            self.keypoints_mismatch.add(category.name)
            return False
        return True


def apply_predictions(image, predictions, resolver, username=None, task_id=None, model_name=None):
    """Save predictions as annotations of ``image``. Returns how many."""
    created = 0
    category_ids = set(image.category_ids or [])

    for p in predictions:
        category = resolver.get(p["class_name"])
        if category is None:
            continue

        annotation = AnnotationModel(image_id=image.id)
        annotation.category_id = category.id
        annotation.segmentation = p["segmentation"]
        annotation.bbox = p["bbox"]
        annotation.area = int(round(p["area"]))
        annotation.isbbox = bool(p.get("isbbox"))
        if p.get("isrbbox"):
            annotation.isrbbox = True
            annotation.rbbox = p["rbbox"]
        if p.get("keypoints") and resolver.ensure_keypoints(category, p["num_keypoints"],
                                                            p.get("keypoint_labels"), p.get("skeleton")):
            annotation.keypoints = p["keypoints"]
        if task_id is not None:
            annotation.import_task = task_id  # the activity log can take the run back
        annotation.source = 'model'           # statistics count these apart from people
        if model_name:
            annotation.model = model_name
        annotation.save()
        if username:
            annotation.update(creator=username)

        category_ids.add(category.id)
        created += 1

    if created:
        num_annotations = AnnotationModel.objects(
            Q(image_id=image.id) & Q(deleted=False) &
            (Q(area__gt=0) | Q(keypoints__0__exists=True))
        ).count()
        image.update(
            set__annotated=True,
            set__category_ids=sorted(category_ids),
            set__num_annotations=num_annotations,
        )
    return created


def annotate_image(image, model_name, conf=0.25, create_missing=True, user=None):
    dataset = DatasetModel.objects(id=image.dataset_id).first()
    predictions = yolo.predict(model_name, image.path, conf=conf)
    resolver = CategoryResolver(dataset, create_missing=create_missing, user=user)
    created = apply_predictions(image, predictions, resolver,
                                username=user.username if user else None, model_name=model_name)
    if created:
        from . import activity
        activity.record('auto_annotate', user, dataset_id=image.dataset_id, image_id=image.id,
                        counts={'annotations': created},
                        detail={'model': model_name, 'file_name': image.file_name},
                        text=f"{model_name} {image.file_name}")
    return {
        "predictions": len(predictions),
        "created": created,
        "skipped_classes": sorted(resolver.skipped),
        "keypoints_mismatch": sorted(resolver.keypoints_mismatch),
    }


def _run_dataset(task_id, dataset_id, model_name, conf, skip_annotated,
                 create_missing, user, socket):
    task = TaskModel.objects.get(id=task_id)
    dataset = DatasetModel.objects.get(id=dataset_id)
    task.update(status="PROGRESS")

    images = ImageModel.objects(dataset_id=dataset.id, deleted=False).order_by('file_name')
    if skip_annotated:
        images = images.filter(Q(annotated=False) | Q(num_annotations=0))
    images = list(images.only('id', 'path', 'file_name', 'category_ids', 'dataset_id'))

    task.info(f"Model {model_name}, confidence >= {conf}; {len(images)} images to process")
    resolver = CategoryResolver(dataset, create_missing=create_missing, user=user)
    total_created = 0

    try:
        for i, image in enumerate(images):
            try:
                predictions = yolo.predict(model_name, image.path, conf=conf)
                created = apply_predictions(image, predictions, resolver,
                                            username=user.username if user else None, task_id=task_id,
                                            model_name=model_name)
                total_created += created
                if created:
                    task.info(f"{image.file_name}: {created} annotations")
            except Exception as e:
                logger.exception(f"Model prediction failed for image {image.id}")
                task.error(f"{image.file_name}: {e}")
            task.set_progress((i + 1) * 100 / max(len(images), 1), socket=socket)
    finally:
        if resolver.skipped:
            task.warning("No category for classes (skipped): " + ", ".join(sorted(resolver.skipped)))
        if resolver.keypoints_mismatch:
            task.warning("Keypoint count differs from the category, keypoints not added: "
                         + ", ".join(sorted(resolver.keypoints_mismatch)))
        task.info(f"Done: {total_created} annotations created")
        ActivityModel.objects(task_id=task_id, action='auto_annotate').update(
            set__counts={'annotations': total_created, 'images': len(images)},
            set__updated_at=datetime.datetime.utcnow())
        task.set_progress(100, socket=socket)


def annotate_dataset(dataset, model_name, conf=0.25, skip_annotated=True,
                     create_missing=True, user=None, socket=None, background=True):
    """Start a task that runs the model over the dataset's images."""
    task = TaskModel(
        name=f"Pre-annotating {dataset.name} with {model_name}",
        dataset_id=dataset.id,
        group="Model Pre-annotation",
    )
    if user is not None:
        task.creator = user.username
    task.save()
    from . import activity
    activity.record('auto_annotate', user, dataset_id=dataset.id, task_id=task.id,
                    detail={'model': model_name, 'whole_dataset': True}, text=model_name)

    args = (task.id, dataset.id, model_name, conf, skip_annotated, create_missing, user, socket)
    if background:
        threading.Thread(target=_run_dataset, args=args, daemon=True).start()
    else:
        _run_dataset(*args)
    return {"id": task.id, "name": task.name}
