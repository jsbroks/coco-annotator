"""Trash: what was deleted, grouped per action; restore or delete for good."""
from flask import request, send_file
from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
import io

from database import AnnotationModel, ImageModel
from ..util import trash, activity

api = Namespace('trash', description='Deleted items: list, restore, permanently delete')

list_args = reqparse.RequestParser()
list_args.add_argument('type', location='args', default='all',
                       choices=('all', 'annotation', 'image', 'category', 'dataset'))
list_args.add_argument('dataset_id', location='args', type=int, default=None)
list_args.add_argument('deleted_by', location='args', default='')
list_args.add_argument('q', location='args', default='')
list_args.add_argument('page', location='args', type=int, default=1)
list_args.add_argument('per_page', location='args', type=int, default=20)

items_args = reqparse.RequestParser()
items_args.add_argument('items', location='json', type=list, required=True,
                        help='[{"type": "annotation", "ids": [1, 2]}, ...]')
items_args.add_argument('include_parents', location='json', type=bool, default=False,
                        help='Also restore the trashed image / dataset they belong to')
items_args.add_argument('activity_id', location='json', type=int, default=None,
                        help='The delete line of the activity log these items come from')


def _log(action, args, n):
    """Write the restore / purge itself to the activity log."""
    if not n:
        return
    source = None
    if args.get('activity_id'):
        source = activity.visible(current_user).filter(id=args['activity_id'], action='delete').first()
    kinds = sorted({i.get('type') for i in args['items'] if i.get('type')})
    detail = {'kinds': kinds}
    if source is not None:
        detail.update({k: v for k, v in (source.detail or {}).items()
                       if k in ('kind', 'file_name', 'name', 'dataset_name', 'categories')})
        detail['from'] = source.id
    activity.record(action, current_user, dataset_id=source.dataset_id if source else None,
                    image_id=source.image_id if source else None, counts={'items': n}, detail=detail,
                    text=(source.text if source else ''))


@api.route('/')
class TrashList(Resource):

    @api.expect(list_args)
    @login_required
    def get(self):
        """ Trash entries (one per delete action), newest first """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        args = list_args.parse_args()
        trash.purge_expired()
        return trash.list_groups(current_user, args['type'], args.get('dataset_id'), args.get('deleted_by'),
                                 args.get('q'), args.get('page') or 1, args.get('per_page') or 20)


@api.route('/restore')
class TrashRestore(Resource):

    @api.expect(items_args)
    @login_required
    def post(self):
        """ Restore items; 409 lists trashed parents unless include_parents """
        args = items_args.parse_args()
        try:
            n = trash.restore(current_user, args['items'], include_parents=bool(args.get('include_parents')))
        except trash.NeedsParents as e:
            return {'message': str(e), 'parents': e.parents}, 409
        _log('restore', args, n)
        return {'success': True, 'restored': n}


@api.route('/purge')
class TrashPurge(Resource):

    @api.expect(items_args)
    @login_required
    def post(self):
        """ Permanently delete items (image files and dataset folders too) """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        args = items_args.parse_args()
        n = trash.purge(current_user, args['items'])
        _log('purge', args, n)
        return {'success': True, 'deleted': n}


@api.route('/empty')
class TrashEmpty(Resource):

    @login_required
    def post(self):
        """ Permanently delete everything in the user's trash """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        n = trash.empty(current_user)
        if n:
            activity.record('purge', current_user, counts={'items': n}, detail={'empty': True})
        return {'success': True, 'deleted': n}


@api.route('/preview')
class TrashPreview(Resource):

    @login_required
    def get(self):
        """ Image (or the area around some annotations) with the shapes outlined """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        try:
            image_id = int(request.args.get('image_id'))
            ann_ids = [int(i) for i in request.args.get('annotations', '').split(',') if i]
            size = max(40, min(int(request.args.get('size', 160)), 600))
        except (TypeError, ValueError):
            return {'message': 'image_id, annotations and size must be numbers'}, 400
        crop = request.args.get('crop') in ('1', 'true')

        images = trash.visible(ImageModel, current_user, deleted=False)
        image = images.filter(id=image_id).first()
        if image is None:
            return {'message': 'Invalid image id'}, 400
        annotations = list(AnnotationModel.objects(image_id=image.id, id__in=ann_ids)) if ann_ids else []
        try:
            data = trash.preview(image, annotations, size=size, crop=crop)
        except OSError:
            return {'message': 'Image file not found on the server'}, 404
        response = send_file(io.BytesIO(data), mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'private, max-age=3600'
        return response
