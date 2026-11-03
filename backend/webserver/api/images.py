from flask_restx import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
from flask import send_file
from mongoengine.errors import NotUniqueError

from ..util import query_util, coco_util
from database import (
    ImageModel,
    DatasetModel,
    AnnotationModel,
    CategoryModel
)

from PIL import Image
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
image_upload.add_argument('dataset_id', required=True, type=int, location='form',
                          help='Id of dataset to insert image into')

image_download = reqparse.RequestParser()
image_download.add_argument('asAttachment', type=bool, default=False)
image_download.add_argument('thumbnail', type=bool, default=False)
image_download.add_argument('width', type=int)
image_download.add_argument('height', type=int)
image_download.add_argument('original', type=bool, default=False)

image_class_args = reqparse.RequestParser()
image_class_args.add_argument('category_id', location='json', type=int, default=None,
                              help='Whole-image class (a category of the dataset), null to clear')

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
        """ Uploads an image into a dataset's folder """
        args = image_upload.parse_args()
        upload = args['image']

        dataset = current_user.editable_datasets.filter(id=args['dataset_id'], deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        if not current_user.can_edit(dataset):
            return {'message': 'You do not have permission to add images to this dataset'}, 403

        # keep only the file name (browsers may send "folder/a.jpg"); unicode is fine
        file_name = os.path.basename((upload.filename or '').replace('\\', '/')).strip()
        if not file_name or file_name.startswith('.') or not file_name.endswith(ImageModel.PATTERN):
            return {'message': f'Not a supported image file: {upload.filename}'}, 400

        directory = dataset.directory
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, file_name)

        existing = ImageModel.objects(path=path).first()
        if os.path.exists(path):
            if existing is None:
                existing = ImageModel.create_from_path(path, dataset.id).save()
            elif existing.deleted:
                existing.update(deleted=False)
            return {'id': existing.id, 'file_name': file_name, 'existed': True}

        data = upload.read()
        upload.close()
        try:
            with Image.open(io.BytesIO(data)) as check:
                check.verify()
        except Exception:
            return {'message': f'Not a valid image: {file_name}'}, 400

        # store the original bytes (no re-encoding, EXIF kept)
        with open(path, 'wb') as f:
            f.write(data)

        try:
            db_image = ImageModel.create_from_path(path, dataset.id).save()
        except NotUniqueError:
            db_image = ImageModel.objects.get(path=path)
        from ..util import activity
        activity.images_uploaded(current_user, dataset, db_image)
        return {'id': db_image.id, 'file_name': file_name, 'existed': False}


@api.route('/<int:image_id>')
class ImageId(Resource):

    @api.expect(image_download)
    @login_required
    def get(self, image_id):
        """ Returns category by ID """
        args = image_download.parse_args()
        as_attachment = args.get('asAttachment')
        thumbnail = args.get('thumbnail')
        original = args.get('original')

        image = current_user.images.filter(id=image_id, deleted=False).first()

        if image is None:
            return {'success': False}, 400
        if not os.path.isfile(image.path):
            # e.g. the file was deleted or moved on disk
            return {'success': False, 'message': 'Image file not found on the server'}, 404
        if original:
            return send_file(image.path, download_name=image.file_name, as_attachment=as_attachment)

        width = args.get('width')
        height = args.get('height')

        # the annotator: the file itself when possible (no re-encoding on every
        # open; ETag lets the browser reuse a prefetched copy)
        if not thumbnail and not width and not height and not as_attachment:
            return send_file(image.display_path(), max_age=0, conditional=True, etag=True)

        # small thumbnails (dataset pages) come from a file cache
        if thumbnail and width and width <= 512 and not as_attachment:
            path = image.small_thumbnail(width, height or image.height)
            return send_file(path, mimetype='image/jpeg', max_age=0)

        if not width:
            width = image.width
        if not height:
            height = image.height

        pil_image = image.open_thumbnail() if thumbnail else Image.open(image.path)

        pil_image.thumbnail((width, height), Image.LANCZOS)
        image_io = io.BytesIO()
        pil_image = pil_image.convert("RGB")
        pil_image.save(image_io, "JPEG", quality=90)
        image_io.seek(0)

        return send_file(image_io, download_name=image.file_name, mimetype='image/jpeg', as_attachment=as_attachment)

    @login_required
    def delete(self, image_id):
        """ Deletes an image by ID """
        image = current_user.editable_images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image id"}, 400

        if not current_user.can_delete(image):
            return {"message": "You do not have permission to download the image"}, 403

        from ..util.trash import soft_delete
        soft_delete(image, current_user)
        return {"success": True}


@api.route('/<int:image_id>/class')
class ImageClass(Resource):

    @api.expect(image_class_args)
    @login_required
    def post(self, image_id):
        """ Sets (or clears) the whole-image class used for image classification """
        args = image_class_args.parse_args()
        image = current_user.editable_images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {'message': 'Invalid image id'}, 400
        dataset = current_user.editable_datasets.filter(id=image.dataset_id).first()
        if dataset is None or not current_user.can_edit(dataset):
            return {'message': 'You do not have permission to edit this dataset'}, 403

        category_id = args.get('category_id')
        if category_id is None:
            image.update(unset__image_class=True, set__annotated=(image.num_annotations or 0) > 0)
        else:
            if category_id not in (dataset.categories or []):
                return {'message': 'That category is not part of this dataset'}, 400
            image.update(set__image_class=category_id, set__annotated=True)
        from ..util import activity
        activity.image_class_set(current_user, image,
                                 CategoryModel.objects(id=category_id).first() if category_id is not None else None)
        return {'success': True, 'image_class': category_id}


@api.route('/copy/<int:from_id>/<int:to_id>/annotations')
class ImageCopyAnnotations(Resource):

    @api.expect(copy_annotations)
    @login_required
    def post(self, from_id, to_id):
        args = copy_annotations.parse_args()
        category_ids = args.get('category_ids')

        image_from = current_user.images.filter(id=from_id).first()
        image_to = current_user.editable_images.filter(id=to_id).first()

        if image_from is None or image_to is None:
            return {'success': False, 'message': 'Invalid image ids'}, 400

        if image_from == image_to:
            return {'success': False, 'message': 'Cannot copy self'}, 400

        if image_from.width != image_to.width or image_from.height != image_to.height:
            return {'success': False, 'message': 'Image sizes do not match'}, 400

        if not category_ids:  # none selected: all categories
            category_ids = DatasetModel.objects(id=image_from.dataset_id).first().categories

        query = AnnotationModel.objects(
            image_id=image_from.id,
            category_id__in=category_ids,
            deleted=False
        )

        # older model runs / imports: mark their source before the copy drops the run
        if query.filter(source__exists=False, import_task__exists=True).first() is not None:
            from ..util.activity import mark_sources
            mark_sources(image_from.dataset_id)

        ids = []
        created = image_to.copy_annotations(query, created_ids=ids)
        if created:
            from ..util import activity
            activity.record('copy', current_user, dataset_id=image_to.dataset_id, image_id=image_to.id,
                            counts={'annotations': created},
                            detail={'file_name': image_to.file_name, 'from_file': image_from.file_name},
                            text=f"{image_to.file_name} {image_from.file_name}")
        return {'annotations_created': created, 'ids': ids}


@api.route('/copy/<int:to_id>/annotations/undo')
class ImageCopyUndo(Resource):

    @login_required
    def post(self, to_id):
        """ Take back a copy (Ctrl+Z): removes those copies for good """
        from flask import request
        image = current_user.editable_images.filter(id=to_id).first()
        if image is None:
            return {'message': 'Invalid image id'}, 400
        if not current_user.can_edit(image.dataset):
            return {'message': 'You do not have permission to edit this dataset'}, 403
        try:
            ids = [int(i) for i in (request.get_json(silent=True) or {}).get('ids') or []]
        except (TypeError, ValueError):
            return {'message': 'ids: a list of annotation ids'}, 400
        # only copies this user just made: anything else goes through the trash
        removed = AnnotationModel.objects(id__in=ids, image_id=image.id, copied_from__exists=True,
                                          creator=current_user.username).delete()
        from ..util.trash import refresh_image
        refresh_image(image.id)
        return {'removed': removed}


@api.route('/<int:image_id>/annotations')
class ImageAnnotations(Resource):

    @login_required
    def delete(self, image_id):
        """ Delete all annotations of an image (they can be restored from Undo) """
        image = current_user.editable_images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {'success': False, 'message': 'Invalid image id'}, 400
        if not current_user.can_edit(image.dataset):
            return {'success': False, 'message': 'You do not have permission to edit this dataset'}, 403

        from ..util.trash import soft_delete
        query = AnnotationModel.objects(image_id=image.id, deleted=False)
        deleted = query.count()
        soft_delete(query, current_user)
        image.update(set__annotated=False, set__num_annotations=0, set__category_ids=[])
        image.flag_thumbnail()

        return {'success': True, 'deleted': deleted}


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

