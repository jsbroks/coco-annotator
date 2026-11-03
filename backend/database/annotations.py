import json

import cv2
import numpy as np

from mongoengine import *

from .datasets import DatasetModel
from .categories import CategoryModel
from .events import Event
from .colors import random_color
from flask_login import current_user


class AnnotationModel(DynamicDocument):

    # Annotations are always loaded per image, per dataset or per category.
    meta = {
        'indexes': [
            ('image_id', 'deleted'),
            ('dataset_id', 'deleted'),
            'category_id',
        ]
    }

    COCO_PROPERTIES = ["id", "image_id", "category_id", "segmentation",
                       "iscrowd", "color", "area", "bbox", "metadata",
                       "keypoints", "isbbox", "isrbbox", "rbbox"]

    id = SequenceField(primary_key=True)
    image_id = IntField(required=True)
    category_id = IntField(required=True)
    dataset_id = IntField()

    segmentation = ListField(default=[])
    area = IntField(default=0)
    bbox = ListField(default=[0, 0, 0, 0])
    iscrowd = BooleanField(default=False)
    isbbox = BooleanField(default=False)
    # Rotated bounding box: [cx, cy, w, h, angle_degrees] (see geometry/)
    isrbbox = BooleanField(default=False)
    rbbox = ListField(default=[])

    creator = StringField(required=True)
    width = IntField()
    height = IntField()

    color = StringField()

    keypoints = ListField(default=[])

    metadata = DictField(default={})
    paper_object = ListField(default=[])

    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    milliseconds = IntField(default=0)
    events = EmbeddedDocumentListField(Event)

    def __init__(self, image_id=None, **data):

        from .images import ImageModel

        if image_id is not None:
            image = ImageModel.objects(id=image_id).first()

            if image is not None:
                data['image_id'] = image_id
                data['width'] = image.width
                data['height'] = image.height
                data['dataset_id'] = image.dataset_id

        super(AnnotationModel, self).__init__(**data)

    def save(self, copy=False, *args, **kwargs):

        if self.dataset_id and not copy:
            dataset = DatasetModel.objects(id=self.dataset_id).first()

            if dataset is not None:
                self.metadata = dataset.default_annotation_metadata.copy()

        if self.color is None:
            self.color = random_color()

        if current_user:
            self.creator = current_user.username
        else:
            self.creator = 'system'

        return super(AnnotationModel, self).save(*args, **kwargs)

    def is_empty(self):
        return len(self.segmentation) == 0 or self.area == 0

    def mask(self):
        """ Returns binary mask of annotation """
        mask = np.zeros((self.height, self.width))
        pts = [
            np.array(anno).reshape(-1, 2).round().astype(int)
            for anno in self.segmentation
        ]
        mask = cv2.fillPoly(mask, pts, 1)
        return mask

    def clone(self):
        """ Creates an unsaved copy (new id, not deleted, no history) """
        # to_mongo keeps dates as datetimes (to_json turned them into
        # {"$date": ...} dicts that cannot be read back)
        create = self.to_mongo().to_dict()
        for key in ('_id', 'id', 'events', 'milliseconds', 'deleted', 'deleted_date'):
            create.pop(key, None)

        return AnnotationModel(**create)

    def add_event(self, e):
        self.update(push__events=e)


__all__ = ["AnnotationModel"]
