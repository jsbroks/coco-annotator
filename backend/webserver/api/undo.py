"""Older undo endpoints, kept for compatibility (the annotator's undo uses
POST /api/undo/). They use the same logic as the trash (/api/trash)."""
from flask_restx import Namespace, Resource, reqparse
from flask_login import login_required, current_user

from ..util import trash

api = Namespace('undo', description='Undo related operations (see /api/trash)')

model_list = reqparse.RequestParser()
model_list.add_argument('type', type=str, location='args', default="all")
model_list.add_argument('limit', type=int, location='args', default=50)

model_data = reqparse.RequestParser()
model_data.add_argument('id', type=int, required=True)
model_data.add_argument('instance', required=True)


@api.route('/list/')
class UndoList(Resource):

    @api.expect(model_list)
    @login_required
    def get(self):
        """ Trashed items, newest first (one row per item) """
        args = model_list.parse_args()
        n = max(1, min(args['limit'], 1000))
        data = []
        for name, model in trash.TYPES.items():
            if args['type'] not in ("all", name):
                continue
            for doc in trash.visible(model, current_user).order_by('-deleted_date').limit(n):
                if doc.deleted_date is None:
                    continue
                label = getattr(doc, 'name', None) or getattr(doc, 'file_name', None) or '-'
                data.append({'id': doc.id, 'name': label, 'instance': name,
                             'date': doc.deleted_date, 'deleted_by': getattr(doc, 'deleted_by', None)})
        data.sort(key=lambda item: item['date'], reverse=True)
        for item in data:
            item['date'] = str(item['date'])
        return data[:n]


@api.route('/')
class Undo(Resource):

    @api.expect(model_data)
    @login_required
    def post(self):
        """ Restore an item (and its trashed image / dataset) """
        args = model_data.parse_args()
        if args['instance'] not in trash.TYPES:
            return {"message": "Instance not found"}, 400
        n = trash.restore(current_user, [{"type": args['instance'], "ids": [args['id']]}], include_parents=True)
        if not n:
            return {"message": "Invalid id"}, 400
        return {"success": True}

    @api.expect(model_data)
    @login_required
    def delete(self):
        """ Permanently delete an item (same rules as /api/trash/purge) """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        args = model_data.parse_args()
        if args['instance'] not in trash.TYPES:
            return {"message": "Instance not found"}, 400
        if not trash.purge(current_user, [{"type": args['instance'], "ids": [args['id']]}]):
            return {"message": "Invalid id"}, 400
        return {"success": True}
