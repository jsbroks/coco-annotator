from flask_restplus import Namespace, Resource

from workers.tasks import long_task
from config import Config
from database import UserModel, TaskModel


api = Namespace('info', description='Software related operations')


@api.route('/')
class Info(Resource):
    def get(self):
        """ Returns information about current version """

        return {
            "name": "COCO Annotator",
            "author": "Justin Brooks",
            "demo": "https://annotator.justinbrooks.ca/",
            "repo": "https://github.com/jsbroks/coco-annotator",
            "git": {
                "tag": Config.VERSION
            },
            "login_enabled": not Config.LOGIN_DISABLED,
            "total_users": UserModel.objects.count(),
            "allow_registration": Config.ALLOW_REGISTRATION
        }


@api.route('/long_task')
class TaskTest(Resource):
    def get(self):
        """ Returns information about current version """
        task_model = TaskModel(group="test", name="Testing Celery")
        task_model.save()

        task = long_task.delay(20, task_model.id)
        return {'id': task.id, 'state': task.state}