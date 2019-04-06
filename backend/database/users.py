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
    permissions = ListField(defualt=[])

    # meta = {'allow_inheritance': True}

    @property
    def datasets(self):
        self._update_last_seen()

        if self.is_admin:
            return DatasetModel.objects

        return DatasetModel.objects(Q(owner=self.username) | Q(users__contains=self.username))

    @property
    def categories(self):
        self._update_last_seen()

        if self.is_admin:
            return CategoryModel.objects

        dataset_ids = self.datasets.distinct('categories')
        return CategoryModel.objects(Q(id__in=dataset_ids) | Q(creator=self.username))

    @property
    def images(self):
        self._update_last_seen()

        if self.is_admin:
            return ImageModel.objects

        dataset_ids = self.datasets.distinct('id')
        return ImageModel.objects(dataset_id__in=dataset_ids)

    @property
    def annotations(self):
        self._update_last_seen()

        if self.is_admin:
            return AnnotationModel.objects

        image_ids = self.images.distinct('id')
        return AnnotationModel.objects(image_id__in=image_ids)

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
        self.update(last_seen=datetime.datetime.utcnow())
    


__all__ = ["UserModel"]