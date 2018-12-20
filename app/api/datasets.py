from flask_restplus import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage
from mongoengine.errors import NotUniqueError
from threading import Thread

from google_images_download import google_images_download as gid

from ..util.pagination_util import Pagination
from ..util import query_util, coco_util
from ..models import *


import datetime
import json
import os

api = Namespace('dataset', description='Dataset related operations')


dataset_create = reqparse.RequestParser()
dataset_create.add_argument('name', required=True)
dataset_create.add_argument('categories', type=list, required=False, location='json',
                            help="List of default categories for sub images")

page_data = reqparse.RequestParser()
page_data.add_argument('page', default=1, type=int)
page_data.add_argument('limit', default=20, type=int)
page_data.add_argument('folder', required=False, default='', help='Folder for data')

delete_data = reqparse.RequestParser()
delete_data.add_argument('fully', default=False, type=bool,
                         help="Fully delete dataset (no undo)")

coco_upload = reqparse.RequestParser()
coco_upload.add_argument('coco', location='files', type=FileStorage, required=True, help='Json coco')


update_dataset = reqparse.RequestParser()
update_dataset.add_argument('categories', location='json', type=list, help="New list of categories")
update_dataset.add_argument('default_annotation_metadata', location='json', type=dict,
                            help="Default annotation metadata")

dataset_generate = reqparse.RequestParser()
dataset_generate.add_argument('keywords', location='json', type=list, default=[],
                              help="Keywords associated with images")
dataset_generate.add_argument('limit', location='json', type=int, default=100, help="Number of images per keyword")


@api.route('/')
class Dataset(Resource):

    def get(self):
        """ Returns all datasets """
        return query_util.fix_ids(DatasetModel.objects(deleted=False).all())

    @api.expect(dataset_create)
    def post(self):
        """ Creates a dataset """
        args = dataset_create.parse_args()
        name = args['name']
        categories = args.get('categories', [])

        category_ids = []

        for category in categories:
            if isinstance(category, int):
                category_ids.append(category)
            else:
                category_model = CategoryModel.objects(name=category).first()

                if category_model is None:
                    new_category = CategoryModel.create_category(name=category)
                    category_ids.append(new_category.id)
                else:
                    category_ids.append(category_model.id)

        try:
            dataset = DatasetModel(name=name, categories=category_ids)
            dataset.save()
        except NotUniqueError:
            return {'message': 'Dataset already exists. Check the undo tab to fully delete the dataset.'}, 400

        return query_util.fix_ids(dataset)


def download_images(output_dir, args):
    for keyword in args['keywords']:
        response = gid.googleimagesdownload()
        response.download({
            "keywords": keyword,
            "limit": args['limit'],
            "output_directory": output_dir,
            "no_numbering": True,
            "format": "jpg",
            "type": "photo",
            "print_urls": False,
            "print_paths": False,
            "print_size": False
        })


@api.route('/<int:dataset_id>/generate')
class DatasetGenerate(Resource):
    def post(self, dataset_id):
        """ Adds images found on google to the dataset """
        args = dataset_generate.parse_args()

        dataset = DatasetModel.objects(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        thread = Thread(target=download_images, args=(dataset.directory, args))
        thread.start()

        return {"success": True}


@api.route('/<int:dataset_id>')
class DatasetId(Resource):

    def delete(self, dataset_id):
        """ Deletes dataset by ID"""
        dataset = DatasetModel.objects(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        dataset.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {"success": True}

    @api.expect(update_dataset)
    def post(self, dataset_id):
        """ Updates dataset by ID """
        dataset = DatasetModel.objects(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        args = update_dataset.parse_args()
        categories = args.get('categories')
        default_annotation_metadata = args.get('default_annotation_metadata')

        if categories is not None:
            dataset.categories = categories

        if default_annotation_metadata is not None:
            dataset.default_annotation_metadata = default_annotation_metadata

        dataset.update(
            set__categories=dataset.categories,
            default_annotation_metadata=dataset.default_annotation_metadata
        )

        return {"success": True}


@api.route('/data')
class Dataset(Resource):
    @api.expect(page_data)
    def get(self):
        """ Endpoint called by dataset viewer client """
        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']
        folder = args['folder']

        datasets = DatasetModel.objects(deleted=False)

        pagination = Pagination(datasets.count(), limit, page)

        datasets = query_util.fix_ids(datasets[pagination.start:pagination.end])

        for dataset in datasets:
            images = ImageModel.objects(dataset_id=dataset.get('id'), deleted=False)

            dataset['numberImages'] = images.count()
            dataset['numberAnnotated'] = images.filter(annotated=True).count()

            first = images.first()
            if first is not None:
                dataset['first_image_id'] = images.first().id

        return {
            "pagination": pagination.export(),
            "folder": folder,
            "datasets": datasets,
            "categories": query_util.fix_ids(CategoryModel.objects(deleted=False).all())
        }


@api.route('/<int:dataset_id>/data')
class DatasetDataId(Resource):

    @api.expect(page_data)
    def get(self, dataset_id):
        """ Endpoint called by image viewer client """

        exec_start = datetime.datetime.now()
        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']
        folder = args['folder']

        # Check if dataset exists
        dataset = DatasetModel.objects(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message', 'Invalid dataset id'}, 400

        # Make sure folder starts with is in proper format
        if len(folder) > 0:
            folder = folder[0].strip('/') + folder[1:]
            if folder[-1] != '/':
                folder = folder + '/'

        # Get directory
        directory = os.path.join(dataset.directory, folder)
        if not os.path.exists(directory):
            return {'message': 'Directory does not exist.'}, 400

        images = ImageModel.objects(dataset_id=dataset_id, path__startswith=directory, deleted=False) \
            .order_by('file_name').only('id', 'file_name')

        pagination = Pagination(images.count(), limit, page)
        images = query_util.fix_ids(images[pagination.start:pagination.end])

        for image in images:
            image_id = image.get('id')
            image['annotations'] = AnnotationModel.objects(image_id=image_id, deleted=False).count()

        subdirectories = [f for f in sorted(os.listdir(directory))
                          if os.path.isdir(directory + f)]

        delta = datetime.datetime.now() - exec_start
        return {
            "time_ms": int(delta.total_seconds() * 1000),
            "pagination": pagination.export(),
            "images": images,
            "folder": folder,
            "directory": directory,
            "dataset": query_util.fix_ids(dataset),
            "subdirectories": subdirectories
        }


@api.route('/<int:dataset_id>/coco')
class ImageCoco(Resource):

    def get(self, dataset_id):
        """ Returns coco of images and annotations in the dataset """

        dataset = DatasetModel.objects(id=dataset_id).first()

        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400

        return coco_util.get_dataset_coco(dataset)

    @api.expect(coco_upload)
    def post(self, dataset_id):
        """ Adds coco formatted annotations to the dataset """
        args = coco_upload.parse_args()
        coco = args['coco']

        dataset = DatasetModel.objects(id=dataset_id).first()
        images = ImageModel.objects(dataset_id=dataset_id)
        categories = CategoryModel.objects

        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400

        coco_json = json.load(coco)
        coco_images = coco_json.get('images')
        coco_annotations = coco_json.get('annotations')
        coco_categories = coco_json.get('categories')

        errors = []

        categories_id = {}
        images_id = {}

        # Create any missing categories
        for category in coco_categories:
            category_name = category.get('name')
            print("Loading category {}".format(category_name), flush=True)

            category_id = category.get('id')
            category_model = categories.filter(name__exact=category_name).all()

            if len(category_model) == 0:
                errors.append({'category': category_name,
                               'message': 'Creating category ' + category_name + '.'})

                new_category = CategoryModel(name=category_name, color=color_util.random_color_hex())
                new_category.save()
                categories_id[category_id] = new_category.id
                print("Category not found! (Creating new one)", flush=True)
                continue

            if len(category_model) > 1:
                errors.append({'category': category_name,
                               'message': 'To many categories found with file name.'})
                continue

            category_model = category_model[0]
            categories_id[category_id] = category_model.id

        # Add any new categories to dataset
        for key, value in categories_id.items():
            if value not in dataset.categories:
                dataset.categories.append(value)

        dataset.update(set__categories=dataset.categories)

        # Find all images
        for image in coco_images:
            image_id = image.get('id')
            image_filename = image.get('file_name')

            print("Loading image {}".format(image_filename), flush=True)
            image_model = images.filter(file_name__exact=image_filename).all()

            if len(image_model) == 0:
                errors.append({'file_name': image_filename,
                               'message': 'Could not find image.'})
                continue

            if len(image_model) > 1:
                errors.append({'file_name': image_filename,
                               'message': 'To many images found with the same file name.'})
                continue

            image_model = image_model[0]
            print("Image found", flush=True)
            images_id[image_id] = image_model

        # Generate annotations
        for annotation in coco_annotations:
            image_id = annotation.get('image_id')
            category_id = annotation.get('category_id')
            segmentation = annotation.get('segmentation', [])
            is_crowd = annotation.get('iscrowed', False)

            if len(segmentation) == 0:
                continue

            print("Loading annotation data (image:{} category:{})".format(image_id, category_id), flush=True)

            try:
                image_model = images_id[image_id]
                category_model_id = categories_id[category_id]
            except KeyError:
                continue

            # Check if annotation already exists
            annotation = AnnotationModel.objects(image_id=image_model.id,
                                                 category_id=category_model_id,
                                                 segmentation=segmentation, delete=False).first()
            # Create annotation
            if annotation is None:
                print("Creating annotation", flush=True)
                annotation = AnnotationModel(image_id=image_model.id)
                annotation.category_id = category_model_id
                # annotation.iscrowd = is_crowd
                annotation.segmentation = segmentation
                annotation.color = color_util.random_color_hex()
                annotation.save()

                image_model.update(set__annotated=True)
            else:
                print("Annotation already exists", flush=True)

        return {
            'errors': errors
        }

