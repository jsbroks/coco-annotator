from flask_mongoengine import MongoEngine
from .util import color_util
from config import Config
from PIL import Image

import datetime

import os
import sys

db = MongoEngine()


class DatasetModel(db.DynamicDocument):

    id = db.SequenceField(primary_key=True)
    name = db.StringField(required=True, unique=True)
    directory = db.StringField()
    categories = db.ListField(default=[])

    default_annotation_metadata = db.DictField(default={})

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    def save(self, *args, **kwargs):

        directory = os.path.join(Config.DATASET_DIRECTORY, self.name.replace(' ', '_') + '/')

        if not os.path.exists(directory):
            os.makedirs(directory)

        self.directory = directory

        return super(DatasetModel, self).save(*args, **kwargs)


class ImageModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    path = db.StringField(required=True, unique=True)

    dataset_id = db.IntField()

    width = db.IntField(required=True)
    height = db.IntField(required=True)
    file_name = db.StringField()

    image_url = db.StringField()
    thumbnail_url = db.StringField()

    metadata = db.DictField()

    license = db.IntField()
    coco_url = db.StringField()

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    @classmethod
    def create_from_path(cls, path):

        pil_image = Image.open(path)

        image = cls()
        image.file_name = os.path.basename(path)
        image.path = path
        image.width = pil_image.size[0]
        image.height = pil_image.size[1]

        # TODO: Make more general
        # Get dataset name from path
        dataset_name = path.split('/')[3].replace('_', ' ')

        dataset = DatasetModel.objects(name=dataset_name).first()
        if dataset is not None:
            image.dataset_id = dataset.id

        pil_image.close()

        return image


class AnnotationModel(db.DynamicDocument):

    id = db.SequenceField(primary_key=True)
    image_id = db.IntField(required=True)
    category_id = db.IntField(required=True)
    dataset_id = db.IntField()

    segmentation = db.ListField()
    area = db.IntField(default=0)
    bbox = db.ListField()
    iscrowd = db.BooleanField(default=False)

    width = db.IntField()
    height = db.IntField()

    color = db.StringField(default=color_util.random_color_hex())

    metadata = db.DictField(default={})
    paper_object = db.ListField(default=[])

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    def __init__(self, image_id=None, **data):

        image = ImageModel.objects(id=image_id).first()

        if image is not None:
            data['image_id'] = image_id
            data['width'] = image.width
            data['height'] = image.height
            data['dataset_id'] = image.dataset_id
        else:
            raise ValueError("Invalid image id.")

        super(AnnotationModel, self).__init__(**data)

    def save(self, *args, **kwargs):

        if self.dataset_id is not None:
            dataset = DatasetModel.objects(id=self.dataset_id).first()

            if dataset is not None:
                metadata = dataset.default_annotation_metadata.copy()
                metadata.update(self.metadata)
                self.metadata = metadata

        return super(AnnotationModel, self).save(*args, **kwargs)

    def is_empty(self):
        return len(self.segmentation) == 0 or self.area == 0


class CategoryModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    name = db.StringField(required=True, unique=True)
    supercategory = db.StringField()
    color = db.StringField(default=color_util.random_color_hex())
    metadata = db.DictField()

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()


class LicenseModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    name = db.StringField()
    url = db.StringField()

