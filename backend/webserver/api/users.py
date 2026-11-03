from flask_login import login_user, login_required, logout_user, current_user
from ..util.passwords import hash_password, check_password, check_and_upgrade
from flask_restx import Namespace, Resource, reqparse

from database import UserModel
from config import Config
from ..util.query_util import fix_ids

import logging
logger = logging.getLogger('gunicorn.error')

api = Namespace('user', description='User related operations')


def user_json(user):
    """The signed-in user for the client, with their role and what it allows."""
    out = fix_ids(user)
    out.pop('password', None)
    out.pop('permissions', None)
    out['role'] = user.role_key
    out['perms'] = sorted(user.perms())
    return out

register = reqparse.RequestParser()
register.add_argument('username', required=True, location='json')
register.add_argument('password', required=True, location='json')
register.add_argument('email', location='json')
register.add_argument('name', location='json')

login = reqparse.RequestParser()
login.add_argument('password', required=True, location='json')
login.add_argument('username', required=True, location='json')

set_password = reqparse.RequestParser()
set_password.add_argument('password', required=True, location='json')
set_password.add_argument('new_password', required=True, location='json')


@api.route('/')
class User(Resource):
    @login_required
    def get(self):
        """ Get information of current user """
        if Config.LOGIN_DISABLED and not current_user.is_authenticated:
            return current_user.to_json()

        return {'user': user_json(current_user)}


reasons_args = reqparse.RequestParser()
reasons_args.add_argument('reasons', type=list, required=True, location='json')


@api.route('/reject-reasons')
class UserRejectReasons(Resource):
    @login_required
    def get(self):
        """ Saved reasons for rejecting (null: never set) """
        return {'reasons': current_user.reject_reasons}

    @api.expect(reasons_args)
    @login_required
    def put(self):
        """ Replace the saved reasons (at most 9, each up to 200 characters) """
        reasons = []
        for r in reasons_args.parse_args()['reasons'] or []:
            r = str(r or '').strip()[:200]
            if r and r not in reasons:
                reasons.append(r)
        reasons = reasons[:9]
        current_user.update(reject_reasons=reasons)
        return {'reasons': reasons}


@api.route('/password')
class UserPassword(Resource):

    @login_required
    @api.expect(register)
    def post(self):
        """ Set password of current user """
        args = set_password.parse_args()

        if check_password(current_user.password, args.get('password')):
            new_password = args.get('new_password') or ''
            if len(new_password) < 5:
                return {'success': False, 'message': 'The new password needs at least 5 characters.',
                        'code': 'too_short'}, 400
            if new_password == args.get('password'):
                return {'success': False, 'message': 'The new password must be different.',
                        'code': 'same'}, 400
            first = bool(getattr(current_user, 'must_change_password', False))
            current_user.update(password=hash_password(new_password), new=False,
                                must_change_password=False)
            from ..util import activity
            activity.record('password_change', current_user, detail={'first_login': first or None})
            return {'success': True}

        return {'success': False, 'message': 'Password does not match current passowrd'}, 400


@api.route('/register')
class UserRegister(Resource):
    @api.expect(register)
    def post(self):
        """ Creates user """

        users = UserModel.total()

        if not Config.ALLOW_REGISTRATION and users != 0:
            return {'success': False, 'message': 'Registration of new accounts is disabled.'}, 400

        args = register.parse_args()
        username = args.get('username')

        if UserModel.objects(username__iexact=username).first():
            return {'success': False, 'message': 'Username already exists.'}, 400

        user = UserModel()
        user.username = args.get('username')
        user.password = hash_password(args.get('password'))
        user.name = args.get('name')
        user.email = args.get('email')
        if users == 0:
            user.is_admin = True
        user.save()

        login_user(user)

        return {'success': True, 'user': user_json(current_user)}


@api.route('/login')
class UserLogin(Resource):
    @api.expect(login)
    def post(self):
        """ Logs user in """
        args = login.parse_args()
        username = args.get('username')

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {'success': False, 'message': 'Could not authenticate user'}, 400

        if check_and_upgrade(user, args.get('password')):
            login_user(user)

            logger.info(f'User {current_user.username} has LOGIN')

            return {'success': True, 'user': user_json(current_user)}

        return {'success': False, 'message': 'Could not authenticate user'}, 400


@api.route('/logout')
class UserLogout(Resource):
    @login_required
    def get(self):
        """ Logs user out """
        logger.info(f'User {current_user.username} has LOGOUT')
        logout_user()
        return {'success': True}

