from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
from mongoengine.errors import NotUniqueError
from threading import Thread

from google_images_download import google_images_download as gid

from ..util.pagination_util import Pagination
from ..util import query_util, coco_util
from ..models import *
from ..util.coco_importer import CocoImporter

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

share = reqparse.RequestParser()
share.add_argument('users', location='json', type=list, default=[], help="List of users")


@api.route('/')
class Dataset(Resource):
    @login_required
    def get(self):
        """ Returns all datasets """
        return query_util.fix_ids(current_user.datasets.filter(deleted=False).all())

    @api.expect(dataset_create)
    @login_required
    def post(self):
        """ Creates a dataset """
        args = dataset_create.parse_args()
        name = args['name']
        categories = args.get('categories', [])

        category_ids = CategoryModel.bulk_create(categories)

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
    @api.expect(dataset_generate)
    @login_required
    def post(self, dataset_id):
        """ Adds images found on google to the dataset """
        args = dataset_generate.parse_args()

        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        thread = Thread(target=download_images, args=(dataset.directory, args))
        thread.start()

        return {"success": True}


@api.route('/<int:dataset_id>')
class DatasetId(Resource):
    @login_required
    def delete(self, dataset_id):
        """ Deletes dataset by ID (only owners of datasets can delete them)"""

        datasets = DatasetModel.objects(id=dataset_id, deleted=False)
        if not current_user.is_admin:
            datasets = datasets.filter(owner=current_user.username)

        dataset = datasets.first()

        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        dataset.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {"success": True}

    @api.expect(update_dataset)
    def post(self, dataset_id):
        """ Updates dataset by ID """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        args = update_dataset.parse_args()
        categories = args.get('categories')
        default_annotation_metadata = args.get('default_annotation_metadata')

        if categories is not None:
            dataset.categories = CategoryModel.bulk_create(categories)

        if default_annotation_metadata is not None:
            dataset.default_annotation_metadata = default_annotation_metadata

        dataset.update(
            categories=dataset.categories,
            default_annotation_metadata=dataset.default_annotation_metadata
        )

        return {"success": True}


@api.route('/<int:dataset_id>/share')
class DatasetIdShare(Resource):
    @api.expect(share)
    @login_required
    def post(self, dataset_id):
        args = share.parse_args()

        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        dataset.update(users=args.get('users'))

        return {"success": True}


@api.route('/data')
class Dataset(Resource):
    @api.expect(page_data)
    @login_required
    def get(self):
        """ Endpoint called by dataset viewer client """

        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']
        folder = args['folder']

        datasets = current_user.datasets.filter(deleted=False)
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
            "categories": query_util.fix_ids(current_user.categories.filter(deleted=False).all())
        }


@api.route('/<int:dataset_id>/data')
class DatasetDataId(Resource):

    @api.expect(page_data)
    @login_required
    def get(self, dataset_id):
        """ Endpoint called by image viewer client """

        exec_start = datetime.datetime.now()
        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']
        folder = args['folder']

        # Check if dataset exists
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
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
            .order_by('file_name').only('id', 'file_name', 'annotating')

        pagination = Pagination(images.count(), limit, page)
        images = query_util.fix_ids(images[pagination.start:pagination.end])

        for image in images:
            image_id = image.get('id')
            query = AnnotationModel.objects(image_id=image_id, deleted=False)
            image['annotations'] = query.count()
            category_ids = query.distinct('category_id')
            image['categories'] = query_util.fix_ids(CategoryModel.objects(id__in=category_ids).only('name', 'color'))


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

    @login_required
    def get(self, dataset_id):
        """ Returns coco of images and annotations in the dataset """

        dataset = current_user.datasets.filter(id=dataset_id).first()

        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400

        return coco_util.get_dataset_coco(dataset)

    @api.expect(coco_upload)
    @login_required
    def post(self, dataset_id):
        """ Adds coco formatted annotations to the dataset """
        args = coco_upload.parse_args()
        coco = args['coco']

        dataset = current_user.datasets.filter(id=dataset_id).first()
        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400

        import_id = CocoImporter.import_coco(
            coco, dataset_id, current_user.username)

        return {
            "import_id": import_id
        }


@api.route('/coco/<int:import_id>')
class ImageCocoId(Resource):

    @login_required
    def get(self, import_id):
        """ Returns current progress and errors of a coco import """
        coco_import = CocoImportModel.objects(
            id=import_id, creator=current_user.username).first()

        if not coco_import:
            return {'message': 'No such coco import'}, 400

        return {
            "progress": coco_import.progress,
            "errors": coco_import.errors
        }
