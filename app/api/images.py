from flask_restplus import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from flask import send_file

from ..util import query_util, coco_util
from ..config import Config
from ..models import *

import datetime
import os
import io


api = Namespace('image', description='Image related operations')


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


@api.route('/')
class Images(Resource):
    def get(self):
        """ Returns all images """
        return query_util.fix_ids(ImageModel.objects(deteled=False).all())

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

        pil_image = Image.open(image.path)
        pil_image.thumbnail((width, height), Image.ANTIALIAS)
        image_io = io.BytesIO()
        pil_image.save(image_io, 'JPEG', quality=70)
        image_io.seek(0)

        return send_file(image_io, attachment_filename=image.file_name, as_attachment=as_attachment)

    def delete(self, image_id):
        """ Deletes an image by ID """
        image = ImageModel.objects(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image id"}, 400

        image.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {"success": True}


@api.route('/<int:image_id>/coco')
class ImageCoco(Resource):
    def get(self, image_id):
        """ Returns coco of image and annotations """
        image = ImageModel.objects(id=image_id).exclude('deleted_date').first()

        if image is None:
            return {"message": "Invalid image ID"}, 400

        return coco_util.get_image_coco(image)

