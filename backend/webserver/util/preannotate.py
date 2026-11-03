"""Turn model predictions into annotations (one image or a whole dataset).

With ``in_boxes`` the model runs inside boxes people already drew (a crop per
box, a little larger), keeping per box the prediction that fits it best:
a pose model then needs to find one person per crop (top-down, as keypoint
benchmarks do with ground-truth boxes) and nobody boxed is missed.
"""
import datetime
import logging
import math
import os
import tempfile
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

    def __init__(self, dataset, create_missing=True, user=None, class_map=None):
        self.dataset = dataset
        self.create_missing = create_missing
        self.user = user
        self.by_name = {}
        self.skipped = set()
        self.ignored = set()       # classes the user chose to leave out
        # class name -> category id (None: leave the class out), chosen in the
        # run dialog; other classes go by name
        self.class_map = {str(k).lower(): v for k, v in (class_map or {}).items()}
        self._mapped = {}          # class -> its chosen category (None: left out)
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
        # the user's choice first: a category of the same name must not win over it
        if key in self.class_map:
            if key not in self._mapped:
                target = self.class_map[key]
                category = None
                if target is not None and target in self._dataset_category_ids:
                    category = CategoryModel.objects(id=target, deleted=False).first()
                if category is None:
                    self.ignored.add(name)
                self._mapped[key] = category
            return self._mapped[key]
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


# room around a box for its crop (share of its width / height on each side)
BOX_PADDING = 0.15


def box_annotations(image_id, in_boxes):
    """The boxes to run in: {category_id, source: human|any} -> [[x, y, w, h]]."""
    query = AnnotationModel.objects(image_id=image_id, category_id=int(in_boxes['category_id']), deleted=False)
    if in_boxes.get('source', 'human') == 'human':
        query = query.filter(source__ne='model')
    boxes = []
    for row in query.only('bbox').as_pymongo():
        bbox = row.get('bbox') or []
        if len(bbox) == 4 and bbox[2] > 1 and bbox[3] > 1:
            boxes.append([float(v) for v in bbox])
    return boxes


def shift_prediction(p, dx, dy):
    """A prediction made on a crop, in the whole image's pixels."""
    p = dict(p)
    p["segmentation"] = [[v + (dx if i % 2 == 0 else dy) for i, v in enumerate(poly)] for poly in p["segmentation"]]
    p["bbox"] = [p["bbox"][0] + dx, p["bbox"][1] + dy, p["bbox"][2], p["bbox"][3]]
    if p.get("rbbox"):
        p["rbbox"] = [p["rbbox"][0] + dx, p["rbbox"][1] + dy] + list(p["rbbox"][2:])
    if p.get("keypoints"):
        kp = list(p["keypoints"])
        for i in range(0, len(kp), 3):
            if kp[i + 2]:
                kp[i], kp[i + 1] = round(kp[i] + dx, 2), round(kp[i + 1] + dy, 2)
        p["keypoints"] = kp
    return p


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    w, h = min(ax2, bx2) - max(a[0], b[0]), min(ay2, by2) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def predict_in_boxes(model_name, image_path, boxes, conf=0.25):
    """Run the model on a crop around each box; per box the prediction that
    overlaps it most (then the most confident), in image coordinates."""
    from PIL import Image
    out = []
    with Image.open(image_path) as pil_image, tempfile.TemporaryDirectory() as tmp:
        # as stored, no EXIF rotation: annotations use this layout
        pil_image = pil_image.convert("RGB")
        width, height = pil_image.size
        for n, (x, y, w, h) in enumerate(boxes):
            x0, y0 = max(int(x - w * BOX_PADDING), 0), max(int(y - h * BOX_PADDING), 0)
            x1 = min(int(math.ceil(x + w + w * BOX_PADDING)), width)
            y1 = min(int(math.ceil(y + h + h * BOX_PADDING)), height)
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            path = os.path.join(tmp, f"box{n}.png")
            pil_image.crop((x0, y0, x1, y1)).save(path)
            predictions = [shift_prediction(p, x0, y0) for p in yolo.predict(model_name, path, conf=conf)]
            if predictions:
                out.append(max(predictions, key=lambda p: (round(_iou(p["bbox"], [x, y, w, h]), 3), p["score"])))
    return out


def predict(model_name, image, conf=0.25, in_boxes=None):
    """(predictions, boxes used: None without in_boxes)."""
    if not in_boxes:
        return yolo.predict(model_name, image.path, conf=conf), None
    boxes = box_annotations(image.id, in_boxes)
    return (predict_in_boxes(model_name, image.path, boxes, conf=conf) if boxes else []), len(boxes)


def annotate_image(image, model_name, conf=0.25, create_missing=True, user=None, class_map=None, in_boxes=None):
    dataset = DatasetModel.objects(id=image.dataset_id).first()
    predictions, boxes = predict(model_name, image, conf=conf, in_boxes=in_boxes)
    resolver = CategoryResolver(dataset, create_missing=create_missing, user=user, class_map=class_map)
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
        "ignored_classes": sorted(resolver.ignored),
        "keypoints_mismatch": sorted(resolver.keypoints_mismatch),
        "boxes": boxes,
    }


def _run_dataset(task_id, dataset_id, model_name, conf, skip_annotated,
                 create_missing, user, socket, class_map=None, in_boxes=None):
    task = TaskModel.objects.get(id=task_id)
    dataset = DatasetModel.objects.get(id=dataset_id)
    task.update(status="PROGRESS")

    images = ImageModel.objects(dataset_id=dataset.id, deleted=False).order_by('file_name')
    if in_boxes:
        # the images with such boxes (they are annotated: skip_annotated does not apply)
        boxed = AnnotationModel.objects(dataset_id=dataset.id, category_id=int(in_boxes['category_id']),
                                        deleted=False)
        if in_boxes.get('source', 'human') == 'human':
            boxed = boxed.filter(source__ne='model')
        images = images.filter(id__in=boxed.distinct('image_id'))
        category = CategoryModel.objects(id=int(in_boxes['category_id'])).first()
        task.info(f"Inside the {'people' + chr(39) + 's ' if in_boxes.get('source', 'human') == 'human' else ''}"
                  f"boxes of {category.name if category else '?'}")
    elif skip_annotated:
        images = images.filter(Q(annotated=False) | Q(num_annotations=0))
    images = list(images.only('id', 'path', 'file_name', 'category_ids', 'dataset_id'))

    task.info(f"Model {model_name}, confidence >= {conf}; {len(images)} images to process")
    resolver = CategoryResolver(dataset, create_missing=create_missing, user=user, class_map=class_map)
    if class_map:
        names = {c.id: c.name for c in CategoryModel.objects(id__in=[v for v in class_map.values() if v])}
        task.info("Classes: " + ", ".join(f"{k} -> {names.get(v, '?') if v else '(left out)'}"
                                          for k, v in class_map.items()))
    total_created = 0

    try:
        for i, image in enumerate(images):
            try:
                predictions, _ = predict(model_name, image, conf=conf, in_boxes=in_boxes)
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
            set__updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        task.set_progress(100, socket=socket)


def annotate_dataset(dataset, model_name, conf=0.25, skip_annotated=True,
                     create_missing=True, user=None, socket=None, background=True, class_map=None,
                     in_boxes=None):
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

    args = (task.id, dataset.id, model_name, conf, skip_annotated, create_missing, user, socket, class_map,
            in_boxes)
    if background:
        threading.Thread(target=_run_dataset, args=args, daemon=True).start()
    else:
        _run_dataset(*args)
    return {"id": task.id, "name": task.name}
