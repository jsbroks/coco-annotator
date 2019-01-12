from flask_restplus import Namespace, Resource, reqparse

from ..config import Config
from ..util.version_util import get_tag
from ..models import UserModel


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
                "tag": get_tag()
            },
            "login_enabled": not Config.LOGIN_DISABLED,
            "total_users": UserModel.objects.count(),
            "allow_registration": Config.ALLOW_REGISTRATION
        }

