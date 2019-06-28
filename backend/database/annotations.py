import imantics as im
import json

from mongoengine import *

from .datasets import DatasetModel
from .categories import CategoryModel
from .events import Event
from flask_login import current_user


class AnnotationModel(DynamicDocument):

    COCO_PROPERTIES = ["id", "image_id", "category_id", "segmentation",
                       "iscrowd", "color", "area", "bbox", "metadata",
                       "keypoints", "isbbox"]

    id = SequenceField(primary_key=True)
    image_id = IntField(required=True)
    category_id = IntField(required=True)
    dataset_id = IntField()

    segmentation = ListField(default=[])
    area = IntField(default=0)
    bbox = ListField(default=[0, 0, 0, 0])
    iscrowd = BooleanField(default=False)
    isbbox = BooleanField(default=False)

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
            self.color = im.Color.random().hex

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
        """ Creates a clone """
        create = json.loads(self.to_json())
        del create['_id']

        return AnnotationModel(**create)

    def __call__(self):

        category = CategoryModel.objects(id=self.category_id).first()
        if category:
            category = category()

        data = {
            'image': None,
            'category': category,
            'color': self.color,
            'polygons': self.segmentation,
            'width': self.width,
            'height': self.height,
            'metadata': self.metadata
        }

        return im.Annotation(**data)

    def add_event(self, e):
        self.update(push__events=e)


__all__ = ["AnnotationModel"]
