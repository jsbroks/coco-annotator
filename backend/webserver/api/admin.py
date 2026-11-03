from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
from ..util.passwords import hash_password, check_password, check_and_upgrade

import re
import secrets

from database import UserModel, DatasetModel, RoleModel
from database.roles import ADMIN, BASIC, DEFAULT, PERMISSIONS, available
from ..util.query_util import fix_ids
from ..util import activity

api = Namespace('admin', description='Admin related operations')

users = reqparse.RequestParser()
users.add_argument('limit', type=int, default=50)
users.add_argument('page', type=int, default=1)

create_user = reqparse.RequestParser()
create_user.add_argument('name', default="", location='json')
create_user.add_argument('password', default="", location='json')
create_user.add_argument('isAdmin', type=bool, default=None, location='json')
create_user.add_argument('role', default=None, location='json', help='Role key (身分)')

register = reqparse.RequestParser()
register.add_argument('username', required=True, location='json')
register.add_argument('password', required=True, location='json')
register.add_argument('email', location='json')
register.add_argument('name', location='json')
register.add_argument('isAdmin', type=bool, default=False, location='json')
register.add_argument('role', default=None, location='json', help='Role key (身分)')


bulk_users = reqparse.RequestParser()
bulk_users.add_argument('users', location='json', type=list, required=True,
                        help='[{"username": "B12345678", "name": "...", "password": "(optional)"}]')
bulk_users.add_argument('role', location='json', default=None, help='Role key for the new accounts')
bulk_users.add_argument('datasetId', location='json', type=int, default=None,
                        help='Optional dataset to share with the new (and existing) accounts')

STUDENT_ID = re.compile(r'^[A-Z][0-9]{8}$')
# no 0/O, 1/l/I: passwords are read from a printed list
PASSWORD_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def _new_password(length=8):
    return ''.join(secrets.choice(PASSWORD_CHARS) for _ in range(length))


def _is_last_admin(user):
    return user.is_admin and UserModel.objects(is_admin=True).count() <= 1


DENIED = {"success": False, "message": "Access denied"}, 401


def _manages_users():
    """Admins, or a role with "manage_users" (who cannot touch admins)."""
    return current_user.has_perm('manage_users')


def _within_mine(perms):
    """A non-admin manager can only deal with permissions they have themselves."""
    if current_user.is_admin:
        return True
    # making categories: what every account could always do, not a power to guard
    return set(perms or ()) - set(BASIC) <= set(current_user.perms())


def _may_touch(user):
    """Edit / reset / delete this account: admins anyone; a manager only
    non-admins whose permissions are no more than their own."""
    if current_user.is_admin:
        return True
    return not user.is_admin and _within_mine(user.perms())


def _pick_role(key, is_admin=None):
    """Role to give: (key, error). Only admins hand out the admin role; a
    manager only roles with no more permissions than their own."""
    if key is None and is_admin is not None:
        key = ADMIN if is_admin else DEFAULT
    if key is None:
        return None, None
    if not isinstance(key, str) or (RoleModel.objects(key=key).first() is None and key not in (ADMIN, DEFAULT)):
        return None, ({"success": False, "message": "Unknown role"}, 400)
    if key == ADMIN and not current_user.is_admin:
        return None, ({"success": False, "message": "Only admins can make admins."}, 403)
    if not _within_mine(RoleModel.permissions_of(key)):
        return None, ({"success": False,
                       "message": "You can only give roles with permissions you have yourself."}, 403)
    return key, None


def _set_role(user, key):
    user.role = key
    user.is_admin = key == ADMIN


def _role_name(key):
    """A custom role's name for the activity log (built-in ones are translated there)"""
    role = RoleModel.objects(key=key).first() if key and key not in (ADMIN, DEFAULT) else None
    return role.name if role else None


def _user_out(user):
    out = fix_ids(user)
    out.pop('password', None)
    out.pop('permissions', None)
    out['role'] = user.role_key
    return out


@api.route('/users')
class Users(Resource):

    @api.expect(users)
    @login_required
    def get(self):
        """ Get list of all users """

        if not _manages_users():
            return DENIED

        args = users.parse_args()
        per_page = max(1, min(int(args['limit'] or 50), 1000))
        page = max(0, int(args['page'] or 1) - 1)

        user_model = UserModel.objects
        total = user_model.count()
        pages = int(total/per_page) + 1

        user_model = user_model.skip(page*per_page).limit(per_page).exclude("preferences", "password")

        return {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
            "users": [_user_out(u) for u in user_model.all()]
        }


@api.route('/users/bulk')
class UsersBulk(Resource):

    @login_required
    @api.expect(bulk_users)
    def post(self):
        """ Create many accounts at once (student IDs like B12345678) """
        if not _manages_users():
            return DENIED

        args = bulk_users.parse_args()
        # no role given: the default one, which also has to be within the manager's own
        role, error = _pick_role(args.get('role') or DEFAULT)
        if error:
            return error
        dataset = None
        if args.get('datasetId') is not None:
            dataset = DatasetModel.objects(id=args['datasetId'], deleted=False).first()
            if dataset is None:
                return {"success": False, "message": "Invalid dataset id"}, 400
            # adding people to a dataset is its owner's call
            if not dataset.is_owner(current_user):
                return {"success": False, "message": "You can only add accounts to datasets you own."}, 403

        created, existing, invalid, seen = [], [], [], set()
        for row in args['users'] or []:
            row = row if isinstance(row, dict) else {}
            username = str(row.get('username') or '').strip().upper()
            name = str(row.get('name') or '').strip()
            password = str(row.get('password') or '').strip()

            if not STUDENT_ID.match(username):
                invalid.append({"username": username, "reason": "format"})
                continue
            if username in seen:
                invalid.append({"username": username, "reason": "duplicate"})
                continue
            seen.add(username)
            found = UserModel.objects(username__iexact=username).first()
            if found:
                # the account as stored (b12345678): dataset.users is matched exactly
                existing.append(found.username)
                continue

            password = password or _new_password()
            user = UserModel(username=username, name=name or username,
                             password=hash_password(password), is_admin=False,
                             must_change_password=True)
            if role:
                _set_role(user, role)
            user.save()
            created.append({"username": username, "name": user.name, "password": password})

        if created:
            activity.record('user_bulk', current_user, dataset_id=dataset.id if dataset else None,
                            counts={'users': len(created), 'existing': len(existing)},
                            detail={'names': [u['username'] for u in created][:200], 'role': role or DEFAULT,
                                    'role_name': _role_name(role), 'shared': bool(dataset)},
                            text=' '.join(u['username'] for u in created[:200]))
        if dataset is not None:
            members = list(dataset.users or [])
            for username in [u["username"] for u in created] + existing:
                if username not in members:
                    members.append(username)
            dataset.update(users=members)

        return {"success": True, "created": created, "existing": existing, "invalid": invalid}


@api.route('/user/')
class User(Resource):

    @login_required
    @api.expect(register)
    def post(self):
        """ Create a new user """

        if not _manages_users():
            return DENIED

        args = register.parse_args()
        role, error = _pick_role(args.get('role'), bool(args.get('isAdmin')))
        if error:
            return error
        username = args.get('username')

        if UserModel.objects(username__iexact=username).first():
            return {'success': False, 'message': 'Username already exists.'}, 400

        user = UserModel()
        user.username = args.get('username')
        user.password = hash_password(args.get('password'))
        user.name = args.get('name') or ""
        user.email = args.get('email') or ""
        _set_role(user, role or DEFAULT)
        user.must_change_password = True
        user.save()
        activity.record('user_create', current_user, detail={'name': user.username, 'display': user.name or None,
                                                             'role': user.role_key,
                                                             'role_name': _role_name(user.role_key)}, text=f"{user.username} {user.name or ''}")

        return {'success': True, 'user': _user_out(user)}


@api.route('/user/<string:username>')
class Username(Resource):

    @login_required
    def get(self, username):
        """ Get a users """

        if not _manages_users():
            return DENIED

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400

        return _user_out(user)

    @api.expect(create_user)
    @login_required
    def patch(self, username):
        """ Edit a user """

        if not _manages_users():
            return DENIED

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400
        if not _may_touch(user):
            return {"success": False,
                    "message": "You can only edit accounts with no more permissions than your own."}, 403

        args = create_user.parse_args()
        changes, role_from = [], user.role_key
        name = args.get('name') or ''
        if not isinstance(name, str):
            return {"success": False, "message": "Invalid name"}, 400
        if len(name) > 0:
            if name != user.name:
                changes.append('name')
            user.name = name

        password = args.get('password') or ''
        if not isinstance(password, str):
            return {"success": False, "message": "Invalid password"}, 400
        if len(password) > 0:
            changes.append('password')
            user.password = hash_password(password)
            # a password set by someone else: they choose their own at next login
            if user.username.lower() != current_user.username.lower():
                user.must_change_password = True

        role, error = _pick_role(args.get('role'), args.get('isAdmin'))
        if error:
            return error
        if role is not None and role != user.role_key:
            if user.username.lower() == current_user.username.lower():
                return {"success": False, "message": "You cannot change your own role."}, 400
            if user.is_admin and _is_last_admin(user):
                return {"success": False, "message": "At least one admin is required."}, 400
            _set_role(user, role)
            changes.append('role')

        user.save()
        if changes:
            activity.record('user_update', current_user, text=f"{user.username} {user.name or ''}", detail={
                'name': user.username, 'changes': changes, 'display': user.name or None,
                'role_from': role_from if 'role' in changes else None,
                'role_to': user.role_key if 'role' in changes else None,
                'role_from_name': _role_name(role_from) if 'role' in changes else None,
                'role_to_name': _role_name(user.role_key) if 'role' in changes else None})

        return _user_out(user)

    @login_required
    def delete(self, username):
        """ Delete a user """

        if not _manages_users():
            return DENIED

        user = UserModel.objects(username__iexact=username).first()
        if user is None:
            return {"success": False, "message": "User not found"}, 400
        if not _may_touch(user):
            return {"success": False,
                    "message": "You can only delete accounts with no more permissions than your own."}, 403

        if user.username.lower() == current_user.username.lower():
            return {"success": False, "message": "You cannot delete your own account."}, 400
        if _is_last_admin(user):
            return {"success": False, "message": "At least one admin is required."}, 400

        username, display = user.username, user.name
        user.delete()
        activity.record('user_delete', current_user, detail={'name': username, 'display': display or None},
                        text=f"{username} {display or ''}")
        return {"success": True}



role_args = reqparse.RequestParser()
role_args.add_argument('name', location='json', default=None)
role_args.add_argument('permissions', location='json', type=list, default=None)


def _roles_out():
    counts = {}
    for u in UserModel.objects.only('is_admin', 'role'):
        counts[u.role_key] = counts.get(u.role_key, 0) + 1
    return {"roles": [r.to_dict(users=counts.get(r.key, 0)) for r in RoleModel.all_ordered()],
            "permissions": list(available())}


@api.route('/roles')
class Roles(Resource):

    @login_required
    def get(self):
        """ Roles (身分), what each allows and how many users have it """
        if not _manages_users():
            return DENIED
        return _roles_out()

    @login_required
    @api.expect(role_args)
    def post(self):
        """ Add a role (admins only) """
        if not current_user.is_admin:
            return DENIED
        args = role_args.parse_args()
        name = (args.get('name') or '').strip()
        if not name:
            return {"success": False, "message": "A role needs a name."}, 400
        if RoleModel.objects(name__iexact=name).first():
            return {"success": False, "message": "A role with this name already exists."}, 400
        n = 1
        while RoleModel.objects(key=f"r{n}").first():
            n += 1
        RoleModel(key=f"r{n}", name=name, permissions=RoleModel.clean_permissions(args.get('permissions')),
                  order=100 + n).save()
        activity.record('role_create', current_user, detail={'name': name, 'key': f"r{n}"}, text=name)
        return {"success": True, "key": f"r{n}", **_roles_out()}


@api.route('/roles/<string:key>')
class Role(Resource):

    @login_required
    @api.expect(role_args)
    def put(self, key):
        """ Rename a role or change what it allows (admins only; the admin role is fixed) """
        if not current_user.is_admin:
            return DENIED
        RoleModel.ensure_builtin()
        role = RoleModel.objects(key=key).first()
        if role is None:
            return {"success": False, "message": "Unknown role"}, 400
        if key == ADMIN:
            return {"success": False, "message": "The admin role always has every permission."}, 400
        args = role_args.parse_args()
        old_name, old_perms = role.name, set(role.permissions or [])
        name = args.get('name')
        if name is not None and not role.builtin:
            name = name.strip()
            if not name:
                return {"success": False, "message": "A role needs a name."}, 400
            if RoleModel.objects(name__iexact=name, key__ne=key).first():
                return {"success": False, "message": "A role with this name already exists."}, 400
            role.name = name
        if args.get('permissions') is not None:
            role.permissions = RoleModel.clean_permissions(args.get('permissions'))
        role.save()
        new_perms = set(role.permissions or [])
        if role.name != old_name or new_perms != old_perms:
            activity.record('role_update', current_user, text=role.name or key, detail={
                'key': key, 'name': role.name or None, 'old_name': old_name if role.name != old_name else None,
                'added': sorted(new_perms - old_perms), 'removed': sorted(old_perms - new_perms)})
        return {"success": True, **_roles_out()}

    @login_required
    def delete(self, key):
        """ Remove a role; its users become regular users (admins only) """
        if not current_user.is_admin:
            return DENIED
        role = RoleModel.objects(key=key).first()
        if role is None:
            return {"success": False, "message": "Unknown role"}, 400
        if role.builtin:
            return {"success": False, "message": "Built-in roles cannot be removed."}, 400
        moved = UserModel.objects(role=key).update(set__role=DEFAULT)
        activity.record('role_delete', current_user, detail={'name': role.name, 'key': key},
                        counts={'users': moved}, text=role.name)
        role.delete()
        return {"success": True, "moved": moved, **_roles_out()}
