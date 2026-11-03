"""Web terminal settings for the page (the session itself runs over the socket)."""
from flask_login import login_required, current_user
from flask_restx import Namespace, Resource

from config import Config

api = Namespace('terminal', description='Web terminal (SSH to the server)')


@api.route('/')
class TerminalInfo(Resource):

    @login_required
    def get(self):
        """ Where the web terminal logs in to """
        if not Config.TERMINAL_ENABLED or not current_user.has_perm('terminal'):
            return {'message': 'No permission for the web terminal'}, 403
        return {'host': Config.TERMINAL_SSH_HOST, 'port': Config.TERMINAL_SSH_PORT,
                'idle_minutes': Config.TERMINAL_IDLE_MINUTES}
