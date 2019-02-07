from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user

from ..util import query_util
from ..config import Config
from ..models import TaskModel


api = Namespace('tasks', description='Task related operations')


@api.route('/')
class Task(Resource):
    @login_required
    def get(self):
        """ Returns all tasks """
        return query_util.fix_ids(TaskModel.objects.all())


@api.route('/<int:task_id>')
class TaskId(Resource):
    @login_required
    def delete(self, task_id):
        """ Deletes task """
        task = TaskModel.objects(id=task_id).first()
        if task is None:
            return {"message": "Invalid task id"}, 400

        task.delete()
        return {"success": True}
