from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user

from ..util import query_util
from ..config import Config
from ..models import TaskModel


api = Namespace('tasks', description='Task related operations')


@api.route('/')
class Info(Resource):
    @login_required
    def get(self):
        """ Returns all tasks """
        return query_util.fix_ids(TaskModel.objects.all())
        

