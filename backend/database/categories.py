
from flask_login import current_user
from mongoengine import *

import imantics as im


class CategoryModel(DynamicDocument):

    COCO_PROPERTIES = ["id", "name", "supercategory", "color", "metadata",\
                       "keypoint_edges", "keypoint_labels", "keypoint_colors"]

    id = SequenceField(primary_key=True)
    name = StringField(required=True, unique_with=['creator'])
    supercategory = StringField(default='')
    color = StringField(default=None)
    metadata = DictField(default={})

    creator = StringField(default='unknown')
    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    keypoint_edges = ListField(default=[])
    keypoint_labels = ListField(default=[])
    keypoint_colors = ListField(default=[])

    @classmethod
    def bulk_create(cls, categories):

        if not categories:
            return []

        category_ids = []
        for category in categories:
            category_model = CategoryModel.objects(name=category).first()

            if category_model is None:
                new_category = CategoryModel(name=category)
                new_category.save()
                category_ids.append(new_category.id)
            else:
                category_ids.append(category_model.id)

        return category_ids

    def save(self, *args, **kwargs):

        if not self.color:
            self.color = im.Color.random().hex

        if current_user:
            self.creator = current_user.username
        else:
            self.creator = 'system'
      
        return super(CategoryModel, self).save(*args, **kwargs)

    def __call__(self):
        """ Generates imantics category object """
        data = {
            'name': self.name,
            'color': self.color,
            'parent': self.supercategory,
            'metadata': self.metadata,
            'id': self.id
        }
        return im.Category(**data)
    
    def is_owner(self, user):

        if user.is_admin:
            return True
        
        return user.username.lower() == self.creator.lower()
    
    def can_edit(self, user):
        return self.is_owner(user)
    
    def can_delete(self, user):
        return self.is_owner(user)


__all__ = ["CategoryModel"]