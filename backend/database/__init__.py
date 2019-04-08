from mongoengine import connect
from config import Config

from .annotations import *
from .categories import *
from .datasets import *
from .lisence import *
from .exports import *
from .images import *
from .events import *
from .users import *
from .tasks import *

import json


def connect_mongo(name, host=None):
    if host is None:
        host = Config.MONGODB_HOST
    connect(name, host=host)


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


def fix_ids(q):
    json_obj = json.loads(q.to_json().replace('\"_id\"', '\"id\"'))
    return json_obj


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


