import os
import sys
import json
from flask_mongoengine import MongoEngine
from .util import color_util
from .config import Config
from PIL import Image


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

        directory = os.path.join(Config.DATASET_DIRECTORY, self.name + '/')

        if not os.path.exists(directory):
            os.makedirs(directory)
        else:
            ImageModel.load_images(directory, self.id)

        self.directory = directory
        return super(DatasetModel, self).save(*args, **kwargs)


class ImageModel(db.DynamicDocument):
    
    PATTERN = (".gif", ".png", ".jpg", ".jpeg", ".bmp")
    
    id = db.SequenceField(primary_key=True)
    path = db.StringField(required=True, unique=True)

    dataset_id = db.IntField()

    width = db.IntField(required=True)
    height = db.IntField(required=True)
    file_name = db.StringField()

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


class AnnotationModel(db.DynamicDocument):

    id = db.SequenceField(primary_key=True)
    image_id = db.IntField(required=True)
    category_id = db.IntField(required=True)
    dataset_id = db.IntField()

    segmentation = db.ListField(default=[])
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
    supercategory = db.StringField(default="")
    color = db.StringField(default=None)
    metadata = db.DictField(default={})

    deleted = db.BooleanField(default=False)
    deleted_date = db.DateTimeField()

    @classmethod
    def create_category(cls, name, color=None, metadata=None, supercategory=None):
        category = CategoryModel(name=name, supercategory=supercategory)
        category.metadata = metadata if metadata is not None else {}
        category.color = color_util.random_color_hex() if color is None else color
        category.save()
        return category

    def save(self, *args, **kwargs):

        if not self.color:
            self.color = color_util.random_color_hex()

        return super(CategoryModel, self).save(*args, **kwargs)


class LicenseModel(db.DynamicDocument):
    id = db.SequenceField(primary_key=True)
    name = db.StringField()
    url = db.StringField()


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
                upsert(CategoryModel, query={ "name": name }, update=category)

        for dataset_json in data_json.get('datasets', []):
            name = dataset_json.get('name')
            if name:
                # map category names to ids; create as needed
                category_ids = []
                for category in dataset_json.get('categories', []):
                    category_obj = { "name": category }
                    category_model = upsert(CategoryModel, query=category_obj)
                    category_ids.append(category_model.id)

                dataset_json['categories'] = category_ids
                upsert(DatasetModel, query={ "name": name}, update=dataset_json)

    sys.stdout.flush()
