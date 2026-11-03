from flask_login import LoginManager, AnonymousUserMixin
from .util.passwords import hash_password, check_password, check_and_upgrade
from database import (
    UserModel,
    DatasetModel,
    CategoryModel,
    AnnotationModel,
    ImageModel
)

login_manager = LoginManager()


class AnonymousUser(AnonymousUserMixin):
    @property
    def datasets(self):
        return DatasetModel.objects

    @property
    def categories(self):
        return CategoryModel.objects

    @property
    def annotations(self):
        return AnnotationModel.objects

    @property
    def images(self):
        return ImageModel.objects

    # login disabled: everything is editable, like for an admin
    @property
    def editable_datasets(self):
        return self.datasets

    @property
    def editable_images(self):
        return self.images

    @property
    def editable_annotations(self):
        return self.annotations

    @property
    def username(self):
        return "anonymous"

    @property
    def name(self):
        return "Anonymous User"

    @property
    def is_admin(self):
        return False

    def update(self, *args, **kwargs):
        pass

    # login turned off: one shared user, nothing to hide
    role_key = 'admin'

    def perms(self):
        from database.roles import available
        return set(available())

    def has_perm(self, perm):
        return True

    def can_page(self, page):
        return True

    def to_json(self):
        return {
            "admin": False,
            "username": self.username,
            "name": self.name,
            "is_admin": self.is_admin,
            "role": "admin",
            "perms": sorted(self.perms()),
            "anonymous": True
        }

    def can_edit(self, model):
        return True

    def can_view(self, model):
        return True

    def can_download(self, model):
        return True

    def can_delete(self, model):
        return True


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return UserModel.objects(id=user_id).first()


@login_manager.unauthorized_handler
def unauthorized():
    return {'success': False, 'message': 'Authorization required'}, 401


@login_manager.request_loader
def load_user_from_request(request):
    auth = request.authorization
    if not auth:
        return None
    user = UserModel.objects(username__iexact=auth.username).first()
    if user and check_and_upgrade(user, auth.password):
        # login_user(user)
        return user
    return None
