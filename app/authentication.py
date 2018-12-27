from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from .config import Config
from .models import UserModel

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return UserModel.objects(id=user_id).first()


@login_manager.unauthorized_handler
def unauthorized():
    return {'success': False, 'message': 'Authorization required'}, 401

