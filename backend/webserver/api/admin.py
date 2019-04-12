from flask_login import login_required, current_user
from flask_restplus import Namespace, Resource, reqparse
from werkzeug.security import generate_password_hash

from database import UserModel
from ..util.query_util import fix_ids

api = Namespace('admin', description='Admin related operations')

users = reqparse.RequestParser()
users.add_argument('limit', type=int, default=50)
users.add_argument('page', type=int, default=1)

create_user = reqparse.RequestParser()
create_user.add_argument('name', default="", location='json')
create_user.add_argument('password', default="", location='json')

register = reqparse.RequestParser()
register.add_argument('username', required=True, location='json')
register.add_argument('password', required=True, location='json')
register.add_argument('email', location='json')
register.add_argument('name', location='json')
register.add_argument('isAdmin', type=bool, default=False, location='json')


@api.route('/users')
class Users(Resource):

    @api.expect(users)
    @login_required
    def get(self):
        """ Get list of all users """

        if not current_user.is_admin:
            return {"success": False, "message": "Access denied"}, 401

        args = users.parse_args()
        per_page = args['limit']
        page = args['page']-1

        user_model = UserModel.objects
        total = user_model.count()
        pages = int(total/per_page) + 1

        user_model = user_model.skip(page*per_page).limit(per_page).exclude("preferences", "password")

        return {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
            "users": fix_ids(user_model.all())
        }


@api.route('/user/')
class User(Resource):

    @login_required
    @api.expect(register)
    def post(self):
        """ Create a new user """

        if not current_user.is_admin:
            return {"success": False, "message": "Access denied"}, 401

        args = register.parse_args()
        username = args.get('username')

        if UserModel.objects(username__iexact=username).first():
            return {'success': False, 'message': 'Username already exists.'}, 400

        user = UserModel()
        user.username = args.get('username')
        user.password = generate_password_hash(args.get('password'), method='sha256')
        user.name = args.get('name', "")
        user.email = args.get('email', "")
        user.is_admin = args.get('isAdmin', False)
        user.save()

        user_json = fix_ids(current_user)
        del user_json['password']

        return {'success': True, 'user': user_json}


@api.route('/user/<string:username>')
class Username(Resource):

    @login_required
    def get(self, username):
        """ Get a users """

        if not current_user.is_admin:
            return {"success": False, "message": "Access denied"}, 401

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400

        return fix_ids(user)

    @api.expect(create_user)
    @login_required
    def patch(self, username):
        """ Edit a user """

        if not current_user.is_admin:
            return {"success": False, "message": "Access denied"}, 401

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400

        args = create_user.parse_args()
        name = args.get('name')
        if len(name) > 0:
            user.name = name

        password = args.get('password')
        if len(password) > 0:
            user.password = generate_password_hash(password, method='sha256')

        user.save()

        return fix_ids(user)

    @login_required
    def delete(self, username):
        """ Delete a user """

        if not current_user.is_admin:
            return {"success": False, "message": "Access denied"}, 401

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400

        user.delete()
        return {"success": True}

