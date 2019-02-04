import os
import cv2
import json
import datetime
import numpy as np
import imantics as im

from PIL import Image
from flask_mongoengine import MongoEngine
from mongoengine.queryset.visitor import Q
from flask_login import UserMixin, current_user


from .config import Config
from PIL import Image


db = MongoEngine()


class DatasetModel(db.DynamicDocument):
    
    id = db.SequenceField(primary_key=True)
    name = db.StringField(required=True, unique=True)
    directory = db.StringField()
    categories = db.ListField(default=[])

    owner = db.StringField(required=True)
    users = db.ListField(default=[])

    default_annotation_metadata = db.DictField(default={})

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    def save(self, *args, **kwargs):

        directory = os.path.join(Config.DATASET_DIRECTORY, self.name + '/')

        if not os.path.exists(directory):
            os.makedirs(directory)
        else:
            ImageModel.load_images(directory, self.id)

        self.directory = directory
        if current_user:
            self.owner = current_user.username
        else:
            self.owner = 'system'

        return super(DatasetModel, self).save(*args, **kwargs)
    
    def scan(self):

        task = TaskModel(
            name="Scanning {}".format(self.name),
            dataset_id=self.id,
            group="Directory Scan"
        )

        return task


class ImageModel(db.DynamicDocument):
    
    PATTERN = (".gif", ".png", ".jpg", ".jpeg", ".bmp")
    
    id = db.SequenceField(primary_key=True)
    path = db.StringField(required=True, unique=True)

    dataset_id = db.IntField()

    width = db.IntField(required=True)
    height = db.IntField(required=True)
    file_name = db.StringField()

    annotating = db.ListField(default=[])
    annotated = db.BooleanField(default=False)

    image_url = db.StringField()
    thumbnail_url = db.StringField()

    category_ids = db.ListField(default=[])

    metadata = db.DictField()

    license = db.IntField()
    coco_url = db.StringField()

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    @classmethod
    def create_from_path(cls, path, dataset_id=None):

        pil_image = Image.open(path)

        image = cls()
        image.file_name = os.path.basename(path)
        image.path = path
        image.width = pil_image.size[0]
        image.height = pil_image.size[1]

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

    @classmethod
    def load_images(cls, directory, dataset_id=None):
        print("Checking all images in dataset directory (may take a few minutes)")
        for root, dirs, files in os.walk(directory):
            for file in files:
                path = os.path.join(root, file)

                if path.endswith(cls.PATTERN):
                    db_image = cls.objects(path=path).first()

                    if db_image is None:
                        print("New file found: {}".format(path))
                        cls.create_from_path(path, dataset_id).save()

    def thumbnail_path(self):
        folders = self.path.split('/')
        i = folders.index("datasets")
        folders.insert(i+1, "_thumbnails")

        directory = '/'.join(folders[:-1])
        if not os.path.exists(directory):
            os.makedirs(directory)

        return '/'.join(folders)
    
    def thumbnail(self):
        image = self().draw(color_by_category=True, bbox=False)
        return Image.fromarray(image)

    def copy_annotations(self, annotations):
        """
        Creates a copy of the annotations for this image
        :param annotations: QuerySet of annotation models
        :return: number of annotations
        """
        annotations = annotations.filter(width=self.width, height=self.height, area__gt=0)

        for annotation in annotations:
            clone = annotation.clone()

            clone.dataset_id = self.dataset_id
            clone.image_id = self.id

            clone.save(copy=True)

        return annotations.count()

    def __call__(self):

        image = im.Image.from_path(self.path)
        for annotation in AnnotationModel.objects(image_id=self.id, deleted=False).all():
            if not annotation.is_empty():
                image.add(annotation())

        return image


class AnnotationModel(db.DynamicDocument):

    id = db.SequenceField(primary_key=True)
    image_id = db.IntField(required=True)
    category_id = db.IntField(required=True)
    dataset_id = db.IntField()

    segmentation = db.ListField(default=[])
    area = db.IntField(default=0)
    bbox = db.ListField()
    iscrowd = db.BooleanField(default=False)

    creator = db.StringField(required=True)
    width = db.IntField()
    height = db.IntField()

    color = db.StringField()

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

    def save(self, copy=False, *args, **kwargs):

        if not self.dataset_id and not copy:
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


class CategoryModel(db.DynamicDocument):

    id = db.SequenceField(primary_key=True)
    name = db.StringField(required=True, unique_with=['creator'])
    supercategory = db.StringField(default="")
    color = db.StringField(default=None)
    metadata = db.DictField(default={})

    creator = db.StringField(default="unknown")
    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    @classmethod
    def bulk_create(cls, categories):

        if not categories:
            return []

        category_ids = []
        for category in categories:
            category_model = CategoryModel.objects(name=category).first()

            if category_model is None:
                new_category = CategoryModel(name=category)
                new_category.save()
                category_ids.append(new_category.id)
            else:
                category_ids.append(category_model.id)

        return category_ids

    def save(self, *args, **kwargs):

        if not self.color:
            self.color = im.Color.random().hex

        if current_user:
            self.creator = current_user.username
        else:
            self.creator = 'system'
      
        return super(CategoryModel, self).save(*args, **kwargs)

    def __call__(self):
        """ Generates imantics category object """
        data = {
            'name': self.name,
            'color': self.color,
            'parent': self.supercategory,
            'metadata': self.metadata,
            'id': self.id
        }
        return im.Category(**data)


class LicenseModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    name = db.StringField()
    url = db.StringField()


class TaskModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    
    # Type of task: Importer, Exporter, Scanner, etc.
    group = db.StringField(required=True)
    name = db.StringField(required=True) 
    desciption = db.StringField()

    creator = db.StringField()

    #: Start date of the executor 
    start_date = db.DateTimeField()
    #: End date of the executor 
    end_date = db.DateTimeField()
    completed = db.BooleanField(default=False)
    failed = db.BooleanField(default=False)
    
    # If any of the information is relevant to the task
    # it should be added
    dataset_id = db.IntField()
    image_id = db.IntField()
    category_id = db.IntField()

    progress = db.FloatField(default=0.0, min_value=0.0, max_value=1.0)

    logs = db.ListField(default=[])
    errors = db.ListField(default=[])

    priority = db.IntField()

    metadata = db.DictField(default={})


class CocoImportModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    creator = db.StringField(required=True)
    progress = db.FloatField(default=0.0, min_value=0.0, max_value=1.0)
    errors = db.ListField(default=[])


class UserModel(db.DynamicDocument, UserMixin):
    password = db.StringField(required=True)
    username = db.StringField(max_length=25, required=True, unique=True)
    email = db.StringField(max_length=30)

    name = db.StringField()
    last_seen = db.DateTimeField()

    is_admin = db.BooleanField(default=False)

    preferences = db.DictField(default={})

    def save(self, *args, **kwargs):

        self.last_seen = datetime.datetime.now()

        return super(UserModel, self).save(*args, **kwargs)

    @property
    def datasets(self):
        self._update_last_seen()

        if self.is_admin:
            return DatasetModel.objects

        return DatasetModel.objects(Q(owner=self.username) | Q(users__contains=self.username))

    @property
    def categories(self):
        self._update_last_seen()

        if self.is_admin:
            return CategoryModel.objects

        dataset_ids = self.datasets.distinct('categories')
        return CategoryModel.objects(Q(id__in=dataset_ids) | Q(creator=self.username))

    @property
    def images(self):
        self._update_last_seen()

        if self.is_admin:
            return ImageModel.objects

        dataset_ids = self.datasets.distinct('id')
        return ImageModel.objects(dataset_id__in=dataset_ids)

    @property
    def annotations(self):
        self._update_last_seen()

        if self.is_admin:
            return AnnotationModel.objects

        image_ids = self.images.distinct('id')
        return AnnotationModel.objects(image_id__in=image_ids)

    def _update_last_seen(self):
        self.update(last_seen=datetime.datetime.now())


# https://github.com/MongoEngine/mongoengine/issues/1171
# Use this methods until a solution is found
def upsert(model, query=None, update=None):

    if not update:
        update = query

    if not query:
        return None

    found = model.objects(**query)

    if found.first():
        return found.modify(new=True, **update)

    new_model = model(**update)
    new_model.save()

    return new_model


def create_from_json(json_file):

    with open(json_file) as file:

        data_json = json.load(file)
        for category in data_json.get('categories', []):
            name = category.get('name')
            if name is not None:
                upsert(CategoryModel, query={"name": name}, update=category)

        for dataset_json in data_json.get('datasets', []):
            name = dataset_json.get('name')
            if name:
                # map category names to ids; create as needed
                category_ids = []
                for category in dataset_json.get('categories', []):
                    category_obj = {"name": category}

                    category_model = upsert(CategoryModel, query=category_obj)
                    category_ids.append(category_model.id)

                dataset_json['categories'] = category_ids
                upsert(DatasetModel, query={ "name": name}, update=dataset_json)

