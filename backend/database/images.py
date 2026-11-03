import os
import threading

import cv2
import numpy as np


from PIL import Image, ImageFile
from mongoengine import *

from .events import Event, SessionEvent
from .datasets import DatasetModel
from .annotations import AnnotationModel
from .categories import CategoryModel


ImageFile.LOAD_TRUNCATED_IMAGES = True


_locks = {}
_locks_guard = threading.Lock()


def _thumbnail_lock(path):
    with _locks_guard:
        if len(_locks) > 10000:
            _locks.clear()
        return _locks.setdefault(path, threading.Lock())


class ImageModel(DynamicDocument):

    # Path lookups happen once per file during scans and in the file watcher;
    # dataset pages filter by dataset and sort by file name.
    meta = {
        'indexes': [
            'path',
            ('dataset_id', 'deleted', 'file_name'),
            'regenerate_thumbnail',
            ('dataset_id', 'deleted', 'status'),
            ('dataset_id', 'deleted', 'assignee'),
        ]
    }

    # Review workflow: unlabeled -> labeled (submitted) -> approved / rejected
    STATUSES = ("unlabeled", "labeled", "approved", "rejected")

    COCO_PROPERTIES = ["id", "width", "height", "file_name", "path", "license",\
                       "flickr_url", "coco_url", "date_captured", "dataset_id"]

    # -- Contants
    THUMBNAIL_DIRECTORY = '.thumbnail'
    PATTERN = (".gif", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".GIF", ".PNG", ".JPG", ".JPEG", ".BMP", ".TIF", ".TIFF")

    # Set maximum thumbnail size (h x w) to use on dataset page
    MAX_THUMBNAIL_DIM = (1024, 1024)

    # -- Private
    _dataset = None

    # -- Database
    id = SequenceField(primary_key=True)
    dataset_id = IntField(required=True)
    category_ids = ListField(default=[])

    # Absolute path to image file
    path = StringField(required=True, unique=True)
    width = IntField(required=True)
    height = IntField(required=True)
    file_name = StringField()
    
    # True if the image is annotated
    annotated = BooleanField(default=False)
    # Poeple currently annotation the image
    annotating = ListField(default=[])
    num_annotations = IntField(default=0)
    
    thumbnail_url = StringField()
    image_url = StringField()
    coco_url = StringField()
    date_captured = DateTimeField()

    metadata = DictField()
    license = IntField()

    # Whole-image class (image classification), a category id
    image_class = IntField()

    # -- Review workflow
    status = StringField(default="unlabeled")
    assignee = StringField()
    labeled_by = StringField()
    labeled_at = DateTimeField()
    reviewed_by = StringField()
    reviewed_at = DateTimeField()
    review_note = StringField()
    #: where the reviewer saw problems when rejecting: [[x, y, w, h], ...]
    review_regions = ListField(ListField(FloatField()), default=[])
    #: the annotator said there is nothing to annotate (a background image)
    confirmed_empty = BooleanField(default=False)

    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    milliseconds = IntField(default=0)
    events = EmbeddedDocumentListField(Event)
    regenerate_thumbnail = BooleanField(default=False)

    @classmethod
    def create_from_path(cls, path, dataset_id=None):

        pil_image = Image.open(path)

        image = cls()
        image.file_name = os.path.basename(path)
        image.path = path
        image.width = pil_image.size[0]
        image.height = pil_image.size[1]
        image.regenerate_thumbnail = True

        if dataset_id is not None:
            image.dataset_id = dataset_id
        else:
            # Get dataset name from path
            folders = path.split('/')
            i = folders.index("datasets")
            dataset_name = folders[i+1]

            dataset = DatasetModel.objects(name=dataset_name).first()
            if dataset is not None:
                image.dataset_id = dataset.id

        pil_image.close()

        return image

    def delete(self, *args, **kwargs):
        self.thumbnail_delete()
        AnnotationModel.objects(image_id=self.id).delete()
        return super(ImageModel, self).delete(*args, **kwargs)

    def thumbnail(self, force=False):
        """
        Generates (if required) thumbnail
        """

        thumbnail_path = self.thumbnail_path()

        if self.regenerate_thumbnail or force:

            pil_image = self.generate_thumbnail()
            pil_image = pil_image.convert("RGB")

            # Resize image to fit in MAX_THUMBNAIL_DIM envelope as necessary
            pil_image.thumbnail((self.MAX_THUMBNAIL_DIM[1], self.MAX_THUMBNAIL_DIM[0]))

            # Save as a jpeg to improve loading time
            # (note file extension will not match but allows for backwards compatibility)
            # Written to a temporary file first: another request may be reading
            # the thumbnail at the same time and must never see half a file.
            tmp = f"{thumbnail_path}.{os.getpid()}.{threading.get_ident()}.tmp"
            pil_image.save(tmp, "JPEG", quality=80, optimize=True, progressive=True)
            os.replace(tmp, thumbnail_path)

            self.update(is_modified=False)
            return pil_image

    def open_thumbnail(self):
        """
        Return thumbnail
        """
        thumbnail_path = self.thumbnail_path()
        if not os.path.isfile(thumbnail_path):
            # Normally made by the Celery worker; build it now if it is not
            # there yet (worker busy or down) instead of failing the request.
            return self.thumbnail(force=True)
        return Image.open(thumbnail_path)

    def small_thumbnail(self, width, height):
        """Path of the thumbnail scaled to fit width x height (cached on disk).

        Dataset pages request many 250 px thumbnails; serving a stored file
        avoids decoding and resizing the 1024 px thumbnail on every request.
        """
        source = self.thumbnail_path()
        # keep the extension: img1.jpg and img1.png need their own files
        path = f"{source}.{int(width)}x{int(height)}.jpg"

        def fresh():
            return os.path.isfile(path) and os.path.isfile(source) \
                and os.path.getmtime(path) >= os.path.getmtime(source)

        if fresh():
            return path
        # many people open the same dataset page at once: build each file once
        with _thumbnail_lock(path):
            if fresh():
                return path
            if not os.path.isfile(source):
                self.thumbnail(force=True)
            with Image.open(source) as pil_image:
                pil_image.thumbnail((width, height), Image.LANCZOS)
                tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
                pil_image.convert("RGB").save(tmp, "JPEG", quality=85)
            os.replace(tmp, path)
        return path

    # formats every browser shows as they are
    BROWSER_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
    BROWSER_MODES = {'RGB', 'RGBA', 'L', 'LA', 'P'}

    def display_path(self):
        """File for the annotator: the original when a browser can show it
        as is (no re-encoding, cacheable), else a JPEG made once and kept.

        Photos with an EXIF rotation are re-encoded too: annotations use the
        stored pixel layout, and browsers would turn the original upright."""
        try:
            with Image.open(self.path) as pil_image:
                orientation = pil_image.getexif().get(0x0112, 1)
                if pil_image.format in self.BROWSER_FORMATS and pil_image.mode in self.BROWSER_MODES \
                        and orientation in (None, 1):
                    return self.path
        except Exception:
            pass

        source = self.path
        path = f"{self.thumbnail_path()}.display.jpg"  # extension kept, as above

        def fresh():
            return os.path.isfile(path) and os.path.getmtime(path) >= os.path.getmtime(source)

        if fresh():
            return path
        with _thumbnail_lock(path):
            if fresh():
                return path
            with Image.open(source) as pil_image:
                tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
                pil_image.convert("RGB").save(tmp, "JPEG", quality=90)
            os.replace(tmp, path)
        return path

    def thumbnail_path(self):
        folders = self.path.split('/')
        folders.insert(len(folders)-1, self.THUMBNAIL_DIRECTORY)

        path = '/' + os.path.join(*folders)
        directory = os.path.dirname(path)

        if not os.path.exists(directory):
            os.makedirs(directory)
        
        return path
    
    def thumbnail_delete(self):
        path = self.thumbnail_path()
        if os.path.isfile(path):
            os.remove(path)

    def generate_thumbnail(self, alpha=0.5):
        """Image with its annotations drawn on top, coloured by category."""
        image = np.array(Image.open(self.path).convert("RGB"))
        overlay = image.copy()

        annotations = AnnotationModel.objects(image_id=self.id, deleted=False)\
            .only('category_id', 'segmentation', 'color')
        colors = {c.id: c.color for c in CategoryModel.objects(
            id__in=list({a.category_id for a in annotations})).only('color')}

        for annotation in annotations:
            if not annotation.segmentation:
                continue
            color = _hex_to_rgb(colors.get(annotation.category_id) or annotation.color)
            polygons = [
                np.array(poly).reshape(-1, 2).round().astype(np.int32)
                for poly in annotation.segmentation if len(poly) >= 6
            ]
            if polygons:
                cv2.fillPoly(overlay, polygons, color)
                cv2.polylines(image, polygons, True, color, 2)

        image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        return Image.fromarray(image)

    def flag_thumbnail(self, flag=True):
        """
        Toggles values to regenerate thumbnail on next thumbnail request
        """
        if self.regenerate_thumbnail != flag:
            self.update(regenerate_thumbnail=flag)

    def copy_annotations(self, annotations, created_ids=None):
        """
        Creates a copy of the annotations for this image
        :param annotations: QuerySet of annotation models
        :param created_ids: a list that receives the ids of the copies
        :return: number of annotations
        """
        annotations = annotations.filter(
            width=self.width, height=self.height).exclude('events')

        created = 0
        for annotation in annotations:
            if annotation.area > 0 or len(annotation.keypoints) > 0:
                clone = annotation.clone()

                clone.dataset_id = self.dataset_id
                clone.image_id = self.id
                # a copy keeps where its shape came from (source / model: a copy
                # of a model's annotation is still "AI") but is not part of
                # that run or import: taking the run back leaves the copy
                if 'import_task' in clone:
                    del clone.import_task
                clone.copied_from = annotation.id

                clone.save(copy=True)
                created += 1
                if created_ids is not None:
                    created_ids.append(clone.id)

        if created:
            self.update(set__annotated=True, set__regenerate_thumbnail=True,
                        inc__num_annotations=created)
        return created

    @property
    def dataset(self):
        if self._dataset is None:
            self._dataset = DatasetModel.objects(id=self.dataset_id).first()
        return self._dataset

    
    def can_delete(self, user):
        return user.can_delete(self.dataset)
    
    def can_download(self, user):
        return user.can_download(self.dataset)
    
    # TODO: Fix why using the functions throws an error
    def permissions(self, user):
        return {
            'delete': True,
            'download': True
        }
    
    def add_event(self, e):
        u = {
            'push__events': e,
        }
        if isinstance(e, SessionEvent):
            u['inc__milliseconds'] = e.milliseconds

        self.update(**u)



def _hex_to_rgb(value, default=(46, 204, 113)):
    try:
        value = (value or "").lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


__all__ = ["ImageModel"]
