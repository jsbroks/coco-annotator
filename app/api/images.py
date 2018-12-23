from flask_restplus import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from flask import send_file, request

from ..util import query_util, coco_util, thumbnail_util
from ..models import *

import datetime
import os
import io


api = Namespace('image', description='Image related operations')


image_all = reqparse.RequestParser()
image_all.add_argument('fields', required=False, type=str)
image_all.add_argument('page', default=1, type=int)
image_all.add_argument('perPage', default=50, type=int, required=False)


image_upload = reqparse.RequestParser()
image_upload.add_argument('image', location='files',
                          type=FileStorage, required=True,
                          help='PNG or JPG file')
image_upload.add_argument('folder', required=False, default='',
                          help='Folder to insert photo into')

image_download = reqparse.RequestParser()
image_download.add_argument('asAttachment', type=bool, required=False, default=False)
image_download.add_argument('width', type=int, required=False, default=0)
image_download.add_argument('height', type=int, required=False, default=0)

copy_annotations = reqparse.RequestParser()
copy_annotations.add_argument('category_ids', location='json', type=int,
                              required=False, default=None, help='Categories to copy')


@api.route('/')
class Images(Resource):
    @api.expect(image_all)
    def get(self):
        """ Returns all images """
        args = image_all.parse_args()
        per_page = args['perPage']
        page = args['page']-1
        fields = args.get('fields', "").split(',')

        images = ImageModel.objects(deleted=False)
        total = images.count()
        pages = int(total/per_page) + 1

        images = images.skip(page*per_page).limit(per_page)
        if fields:
            images = images.only(*fields)

        return {
            "total": total,
            "pages": pages,
            "page": page,
            "fields": fields,
            "per_page": per_page,
            "images": query_util.fix_ids(images.all())
        }

    @api.expect(image_upload)
    def post(self):
        """ Creates an image """
        args = image_upload.parse_args()
        image = args['image']

        folder = args['folder']
        if len(folder) > 0:
            folder = folder[0].strip('/') + folder[1:]

        directory = os.path.join(Config.DATASET_DIRECTORY, folder)
        path = os.path.join(directory, image.filename)

        if os.path.exists(path):
            return {'message': 'file already exists'}, 400

        if not os.path.exists(directory):
            os.makedirs(directory)

        pil_image = Image.open(io.BytesIO(image.read()))

        image_model = ImageModel(
            file_name=image.filename,
            width=pil_image.size[0],
            height=pil_image.size[1],
            path=path
        )

        image_model.save()
        pil_image.save(path)

        image.close()
        pil_image.close()
        return query_util.fix_ids(image_model)


@api.route('/<int:image_id>')
class ImageId(Resource):

    @api.expect(image_download)
    def get(self, image_id):
        """ Returns category by ID """
        args = image_download.parse_args()
        as_attachment = args['asAttachment']
        width = args['width']
        height = args['height']

        image = ImageModel.objects(id=image_id, deleted=False).first()

        if image is None:
            return {'success': False}, 400

        if width < 1:
            width = image.width

        if height < 1:
            height = image.height

        try:
            pil_image = Image.open(image.path)
        except Exception as e:
            return {'message': str(e)}, 400

        pil_image.thumbnail((width, height), Image.ANTIALIAS)
        image_io = io.BytesIO()
        pil_image = pil_image.convert("RGB")
        pil_image.save(image_io, "JPEG", quality=90)
        image_io.seek(0)

        return send_file(image_io, attachment_filename=image.file_name, as_attachment=as_attachment)

    def delete(self, image_id):
        """ Deletes an image by ID """
        image = ImageModel.objects(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image id"}, 400

        image.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {"success": True}


@api.route('/copy/<int:from_id>/<int:to_id>/annotations')
class ImageCopyAnnotations(Resource):

    @api.expect(copy_annotations)
    def put(self, from_id, to_id):
        args = copy_annotations.parse_args()
        category_ids = args.get('category_ids')

        image_from = ImageModel.objects(id=from_id).first()
        image_to = ImageModel.objects(id=to_id).first()
        limit = 500

        if image_from == image_to:
            return {'success': False, 'message': 'Cannot copy self'}

        if image_from is None or image_to is None:
            return {'success': False, 'message': 'Invalid image ids'}

        if category_ids is None:
            category_ids = DatasetModel.objects(id=image_from.dataset_id).first().categories
        else:
            category_ids = []

        query = AnnotationModel.objects(
            image_id=image_from.id,
            category_id__in=category_ids,
            deleted=False
        )

        return {'annotations_created': image_to.copy_annotations(query)}


@api.route('/<int:image_id>/thumbnail')
class ImageCoco(Resource):

    @api.expect(image_download)
    def get(self, image_id):
        """ Returns coco of image and annotations """
        args = image_download.parse_args()
        as_attachment = args['asAttachment']
        width = args['width']
        height = args['height']

        image = ImageModel.objects(id=image_id, deleted=False).first()

        if image is None:
            return {'success': False}, 400

        if width < 1:
            width = image.width

        if height < 1:
            height = image.height

        pil_image = thumbnail_util.generate_thumbnail(image, save=False)
        pil_image.thumbnail((width, height), Image.ANTIALIAS)

        image_io = io.BytesIO()
        pil_image = pil_image.convert("RGB")
        pil_image.save(image_io, "JPEG", quality=90)
        image_io.seek(0)

        return send_file(image_io, attachment_filename=image.file_name, as_attachment=as_attachment)


@api.route('/<int:image_id>/coco')
class ImageCoco(Resource):
    def get(self, image_id):
        """ Returns coco of image and annotations """
        image = ImageModel.objects(id=image_id).exclude('deleted_date').first()

        if image is None:
            return {"message": "Invalid image ID"}, 400

        return coco_util.get_image_coco(image)

