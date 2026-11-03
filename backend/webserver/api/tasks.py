from flask_restx import Namespace, Resource
from flask_login import login_required, current_user

from ..util import query_util
from database import TaskModel, DatasetModel


api = Namespace('tasks', description='Task related operations')


def _task(task_id):
    """A task this user may see: any with Tasks page access, else their own."""
    query = TaskModel.objects(id=task_id)
    if not current_user.can_page('tasks'):
        query = query.filter(creator=current_user.username)
    return query.first()


@api.route('/')
class Task(Resource):
    @login_required
    def get(self):
        """ Returns all tasks (only your own without access to the Tasks page) """
        query = TaskModel.objects
        if not current_user.can_page('tasks'):
            query = query.filter(creator=current_user.username)
        query = query.only(
            'group', 'id', 'name', 'completed', 'progress',
            'priority', 'creator', 'desciption', 'errors',
            'warnings', 'failed', 'start_date', 'end_date', 'dataset_id'
        ).all()
        tasks = query_util.fix_ids(query)
        names = {d.id: d.name for d in DatasetModel.objects(
            id__in=list({t.get('dataset_id') for t in tasks if t.get('dataset_id')})).only('id', 'name')}
        for t in tasks:
            if t.get('dataset_id') in names:
                t['dataset_name'] = names[t['dataset_id']]
        return tasks


@api.route('/completed')
class TasksCompleted(Resource):
    @login_required
    def delete(self):
        """ Removes the finished tasks you can see (with their logs) """
        query = TaskModel.objects(completed=True)
        if not current_user.can_page('tasks'):
            query = query.filter(creator=current_user.username)
        n = query.count()
        query.delete()
        if n:
            from ..util import activity
            activity.record('task_clear', current_user, counts={'items': n})
        return {"success": True, "deleted": n}


@api.route('/<int:task_id>')
class TaskId(Resource):
    @login_required
    def delete(self, task_id):
        """ Deletes task """
        task = _task(task_id)

        if task is None:
            return {"message": "Invalid task id"}, 400

        if not task.completed:
            return {"message": "Task is not completed"}, 400

        name = task.name
        task.delete()
        from ..util import activity
        activity.record('task_delete', current_user, detail={'name': name, 'task': task_id}, text=name)
        return {"success": True}


@api.route('/<int:task_id>/logs')
class TaskId(Resource):
    @login_required
    def get(self, task_id):
        """ Deletes task """
        task = _task(task_id)
        if task is None:
            return {"message": "Invalid task id"}, 400

        return {'logs': task.logs}
