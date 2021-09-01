from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
from flask import send_file
import pycocotools.mask as mask
from ..util import query_util, coco_util
from database import (
    fix_ids,
    ImageModel,
    CategoryModel,
    DatasetModel,
    AnnotationModel
)
import numpy as np
from PIL import Image, ImageColor
import datetime
import os
import io

api = Namespace('image', description='Image related operations')

image_all = reqparse.RequestParser()
image_all.add_argument('fields', required=False, type=str)
image_all.add_argument('page', default=1, type=int)
image_all.add_argument('per_page', default=50, type=int, required=False)

image_upload = reqparse.RequestParser()
image_upload.add_argument('image', location='files',
                          type=FileStorage, required=True,
                          help='PNG or JPG file')
image_upload.add_argument('dataset_id', required=True, type=int,
                          help='Id of dataset to insert image into')

image_download = reqparse.RequestParser()
image_download.add_argument('asAttachment', type=bool, default=False)
image_download.add_argument('thumbnail', type=bool, default=False)
image_download.add_argument('width', type=int)
image_download.add_argument('height', type=int)

copy_annotations = reqparse.RequestParser()
copy_annotations.add_argument('category_ids', location='json', type=list,
                              required=False, default=None, help='Categories to copy')


@api.route('/')
class Images(Resource):

    @api.expect(image_all)
    @login_required
    def get(self):
        """ Returns all images """
        args = image_all.parse_args()
        per_page = args['per_page']
        page = args['page']-1
        fields = args.get('fields', '')

        images = current_user.images.filter(deleted=False)
        total = images.count()
        pages = int(total/per_page) + 1

        images = images.skip(page*per_page).limit(per_page)
        if fields:
            images = images.only(*fields.split(','))

        return {
            "total": total,
            "pages": pages,
            "page": page,
            "fields": fields,
            "per_page": per_page,
            "images": query_util.fix_ids(images.all())
        }

    @api.expect(image_upload)
    @login_required
    def post(self):
        """ Creates an image """
        args = image_upload.parse_args()
        image = args['image']

        dataset_id = args['dataset_id']
        try:
            dataset = DatasetModel.objects.get(id=dataset_id)
        except:
            return {'message': 'dataset does not exist'}, 400
        directory = dataset.directory
        path = os.path.join(directory, image.filename)

        if os.path.exists(path):
            return {'message': 'file already exists'}, 400

        pil_image = Image.open(io.BytesIO(image.read()))

        pil_image.save(path)

        image.close()
        pil_image.close()
        db_image = ImageModel.create_from_path(path, dataset_id).save()
        return db_image.id


@api.route('/<int:image_id>')
class ImageId(Resource):

    @api.expect(image_download)
    @login_required
    def get(self, image_id):
        """ Returns category by ID """
        args = image_download.parse_args()
        as_attachment = args.get('asAttachment')
        thumbnail = args.get('thumbnail')

        image = current_user.images.filter(id=image_id, deleted=False).first()

        if image is None:
            return {'success': False}, 400

        width = args.get('width')
        height = args.get('height')
        
        if not width:
            width = image.width
        if not height:
            height = image.height
        
        pil_image = image.open_thumbnail() if thumbnail else Image.open(image.path)

        pil_image.thumbnail((width, height), Image.ANTIALIAS)
        image_io = io.BytesIO()
        pil_image = pil_image.convert("RGB")
        pil_image.save(image_io, "JPEG", quality=90)
        image_io.seek(0)

        return send_file(image_io, attachment_filename=image.file_name, as_attachment=as_attachment)

    @login_required
    def delete(self, image_id):
        """ Deletes an image by ID """
        image = current_user.images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image id"}, 400

        if not current_user.can_delete(image):
            return {"message": "You do not have permission to download the image"}, 403

        image.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {"success": True}


@api.route('/copy/<int:from_id>/<int:to_id>/annotations')
class ImageCopyAnnotations(Resource):

    @api.expect(copy_annotations)
    @login_required
    def post(self, from_id, to_id):
        args = copy_annotations.parse_args()
        category_ids = args.get('category_ids')

        image_from = current_user.images.filter(id=from_id).first()
        image_to = current_user.images.filter(id=to_id).first()

        if image_from is None or image_to is None:
            return {'success': False, 'message': 'Invalid image ids'}, 400

        if image_from == image_to:
            return {'success': False, 'message': 'Cannot copy self'}, 400

        if image_from.width != image_to.width or image_from.height != image_to.height:
            return {'success': False, 'message': 'Image sizes do not match'}, 400

        if category_ids is None:
            category_ids = DatasetModel.objects(id=image_from.dataset_id).first().categories

        query = AnnotationModel.objects(
            image_id=image_from.id,
            category_id__in=category_ids,
            deleted=False
        )

        return {'annotations_created': image_to.copy_annotations(query)}


@api.route('/<int:image_id>/coco')
class ImageCoco(Resource):

    @login_required
    def get(self, image_id):
        """ Returns coco of image and annotations """
        image = current_user.images.filter(id=image_id).exclude('deleted_date').first()
        
        if image is None:
            return {"message": "Invalid image ID"}, 400

        if not current_user.can_download(image):
            return {"message": "You do not have permission to download the images's annotations"}, 403

        return coco_util.get_image_coco(image_id)

@api.route('/semanticSegmentation/<int:image_id>')
class ImageSemanticSegmentation(Resource):
    @api.expect(image_download)
    @login_required
    def get(self, image_id):
        """ Returns semantic segmentation image by image's ID """
        args = image_download.parse_args()
        as_attachment = args.get('asAttachment')
        
        image = ImageModel.objects(id=image_id)\
        .only(*ImageModel.COCO_PROPERTIES)

        if image is None:
            return {'success': False}, 400

        image = fix_ids(image)[0]
        # Image dimensions
        width = image.get('width')
        height = image.get('height')

        dataset = DatasetModel.objects(id=image.get('dataset_id')).first()

        bulk_categories = CategoryModel.objects(id__in=dataset.categories, deleted=False) \
            .only(*CategoryModel.COCO_PROPERTIES)

        db_annotations = AnnotationModel.objects(deleted=False, image_id=image_id)

        final_image_array = np.zeros((height, width))
        category_index = 1
        # category_colors = [black, color1, color2, ...] , found_categories = [1, 3]
        # if found annotations belong to the 1st and third categories in bulk_categories
        category_colors = [(0, 0, 0)]
        found_categories = []
        # Loop to generate semantic segmentation mask: 
        # example: pixels belonging to the category of index 2, will have the value 2
        for category in fix_ids(bulk_categories):
            category_colors.append(ImageColor.getcolor(category.get('color'), 'RGB')) 
            category_annotations = db_annotations\
                .filter(category_id=category.get('id'))\
                .only(*AnnotationModel.COCO_PROPERTIES)
        
            if category_annotations.count() == 0:
                category_index += 1
                continue
            found_categories.append(category_index)
            category_annotations = fix_ids(category_annotations)
            for annotation in category_annotations:
                
                has_polygon_segmentation = len(annotation.get('segmentation', [])) > 0
                has_rle_segmentation = annotation.get('rle', {}) != {}
                if has_rle_segmentation:
                    CompressedRle = annotation.get('rle')
                    bin_mask = mask.decode(CompressedRle)
                    idx = bin_mask == 1
                    final_image_array[idx] = category_index
                elif has_polygon_segmentation:
                    bin_mask = coco_util.get_bin_mask(list(annotation.get('segmentation')), height, width)
                    idx = bin_mask == 1
                    final_image_array[idx] = category_index
            category_index += 1
        # Transfom the 2D array to an RGB image
        r = np.zeros_like(final_image_array).astype(np.uint8)
        g = np.zeros_like(final_image_array).astype(np.uint8)
        b = np.zeros_like(final_image_array).astype(np.uint8)

        for l in found_categories:
            idx = final_image_array == l
            x, y, z = category_colors[l]
            r[idx] = x
            g[idx] = y
            b[idx] = z
    
        rgb = np.stack([r, g, b], axis=2)
        
        image_io = io.BytesIO()
        Image.fromarray(rgb.astype('uint8')).save(image_io, "PNG", quality=95)
        image_io.seek(0)
        return send_file(image_io, attachment_filename=image.get('file_name'), as_attachment=as_attachment)