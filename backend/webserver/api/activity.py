"""Activity log: everything that changed, newest first; deletes can be
restored from here and imports taken back."""
import threading

from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse

from ..util import activity, trash

api = Namespace('activity', description='Activity log (includes the trash)')

list_args = reqparse.RequestParser()
list_args.add_argument('group', location='args', default='all',
                       choices=('all', 'trash', *activity.GROUPS))
list_args.add_argument('dataset_id', location='args', type=int, default=None)
list_args.add_argument('user', location='args', default='')
list_args.add_argument('q', location='args', default='')
list_args.add_argument('page', location='args', type=int, default=1)
list_args.add_argument('per_page', location='args', type=int, default=30)

_backfilled = [False]
_backfill_lock = threading.Lock()


def _backfill_once():
    """Deleted before the log existed: give those a line (once per start)."""
    with _backfill_lock:
        if _backfilled[0]:
            return
        _backfilled[0] = True
    try:
        activity.backfill_trash()
    except Exception:  # pragma: no cover
        activity.logger.exception("Activity backfill failed")


@api.route('/')
class ActivityList(Resource):

    @api.expect(list_args)
    @login_required
    def get(self):
        """ Activity lines, newest first, with counts per group """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        args = list_args.parse_args()
        trash.purge_expired()
        _backfill_once()
        return activity.list_activity(current_user, args['group'], args.get('dataset_id'), args.get('user'),
                                      args.get('q'), args.get('page') or 1, args.get('per_page') or 30)


@api.route('/<int:activity_id>/undo')
class ActivityUndo(Resource):

    @login_required
    def post(self, activity_id):
        """ Send what an import created to the trash """
        if not current_user.can_page('activity'):
            return {'message': 'You do not have access to the activity log', 'code': 'no_page'}, 403
        entry = activity.visible(current_user).filter(id=activity_id, action__in=['import', 'video', 'auto_annotate'], task_id__ne=None).first()
        if entry is None:
            return {'message': 'Invalid activity id'}, 400
        if entry.undone_at:
            return {'message': 'Already taken back'}, 400
        if entry.dataset_id:
            from database import DatasetModel
            dataset = DatasetModel.objects(id=entry.dataset_id).first()
            if dataset is None or not current_user.can_edit(dataset):
                return {'message': 'You do not have permission to edit this dataset'}, 403
        n = activity.undo_import(current_user, entry)
        activity.record('undo_import', current_user, dataset_id=entry.dataset_id,
                        counts={'items': n}, detail={'kind': 'image' if entry.action == 'video' else 'annotation',
                                                     'from': entry.id, **{k: v for k, v in (entry.detail or {}).items()
                                                                          if k in ('format', 'file_name')}})
        return {'success': True, 'deleted': n}
