import datetime

from mongoengine import *
from flask_login import UserMixin

from .annotations import AnnotationModel
from .categories import CategoryModel
from .datasets import DatasetModel
from .images import ImageModel


class UserModel(DynamicDocument, UserMixin):

    password = StringField(required=True)
    username = StringField(max_length=25, required=True, unique=True)
    email = StringField(max_length=30)

    name = StringField()
    online = BooleanField(default=False)
    last_seen = DateTimeField()

    is_admin = BooleanField(default=False)

    preferences = DictField(default={})
    #: a reviewer's saved reasons for rejecting (None: the built-in suggestions)
    reject_reasons = ListField(StringField(), default=None)
    permissions = ListField(defualt=[])
    # 身分 (database/roles.py); admins are role "admin" and keep is_admin
    role = StringField(default=None)
    # set when an admin picks the password (bulk accounts, new account, reset):
    # the user is asked to choose their own right after logging in
    must_change_password = BooleanField(default=False)

    # meta = {'allow_inheritance': True}

    @classmethod
    def total(cls):
        """Exact number of users.

        ``objects.count()`` without a filter uses MongoDB's collection
        metadata, which can be stale (e.g. 0 after an unclean shutdown). This
        decides whether registration is open and who becomes admin, so count
        the documents.
        """
        return cls._get_collection().count_documents({})

    @property
    def role_key(self):
        from .roles import ADMIN, DEFAULT
        return ADMIN if self.is_admin else (self.role if self.role and self.role != ADMIN else DEFAULT)

    def perms(self):
        """What this user's role allows (see database/roles.py), cached per request."""
        cached = getattr(self, '_perms_cache', None)
        if cached is None or cached[0] != self.role_key:
            from .roles import RoleModel
            cached = (self.role_key, RoleModel.permissions_of(self.role_key))
            object.__setattr__(self, '_perms_cache', cached)
        return cached[1]

    def has_perm(self, perm):
        return bool(self.is_admin) or perm in self.perms()

    def can_page(self, page):
        """Activity log, Models and Tasks pages."""
        return self.has_perm(page)

    @property
    def datasets(self):
        self._update_last_seen()

        if self.is_admin or self.has_perm('all_datasets'):
            return DatasetModel.objects

        return DatasetModel.objects(Q(owner=self.username) | Q(users__contains=self.username))

    @property
    def categories(self):
        self._update_last_seen()

        if self.is_admin or self.has_perm('all_datasets') or self.has_perm('manage_categories'):
            return CategoryModel.objects

        dataset_ids = self.datasets.distinct('categories')
        return CategoryModel.objects(Q(id__in=dataset_ids) | Q(creator=self.username))

    @property
    def images(self):
        self._update_last_seen()

        if self.is_admin or self.has_perm('all_datasets'):
            return ImageModel.objects

        dataset_ids = self.datasets.distinct('id')
        return ImageModel.objects(dataset_id__in=dataset_ids)

    @property
    def annotations(self):
        self._update_last_seen()

        if self.is_admin or self.has_perm('all_datasets'):
            return AnnotationModel.objects

        image_ids = self.images.distinct('id')
        return AnnotationModel.objects(image_id__in=image_ids)

    # ---- what this user may change ------------------------------------------
    # "all_datasets" lets a role SEE every dataset; changing anything still
    # needs being a member (or the owner, or an admin). Write endpoints use
    # these instead of datasets / images / annotations / categories.

    @property
    def editable_datasets(self):
        if self.is_admin:
            return DatasetModel.objects
        return DatasetModel.objects(Q(owner=self.username) | Q(users__contains=self.username))

    @property
    def editable_images(self):
        if self.is_admin:
            return ImageModel.objects
        return ImageModel.objects(dataset_id__in=self.editable_datasets.distinct('id'))

    @property
    def editable_annotations(self):
        if self.is_admin:
            return AnnotationModel.objects
        return AnnotationModel.objects(image_id__in=self.editable_images.distinct('id'))

    def dataset_categories(self, dataset):
        """Categories of one dataset (for checking a category id)."""
        return CategoryModel.objects(id__in=list(dataset.categories or []))

    def can_view(self, model):
        if model is None:
            return False

        return model.can_view(self)
    
    def can_download(self, model):
        if model is None:
            return False

        return model.can_download(self)
        
    def can_delete(self, model):
        if model is None:
            return False
        return model.can_delete(self)

    def can_edit(self, model):
        if model is None:
            return False

        return model.can_edit(self)

    def _update_last_seen(self):
        # called on most requests (several times each): write at most once a
        # minute instead of on every image / thumbnail request
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        last = getattr(self, 'last_seen', None)
        if isinstance(last, datetime.datetime) and (now - last).total_seconds() < 60:
            return
        self.last_seen = now
        self.update(last_seen=now)
    


__all__ = ["UserModel"]