
from flask_login import current_user
from mongoengine import *

from .colors import random_color


class CategoryCreateDenied(Exception):
    """A new category was needed, but the user may not make categories."""

    def __init__(self, name):
        super().__init__(name)
        self.name = name


class CategoryModel(DynamicDocument):

    COCO_PROPERTIES = ["id", "name", "supercategory", "supercategories", "color", "metadata",\
                       "keypoint_edges", "keypoint_labels", "keypoint_colors"]

    id = SequenceField(primary_key=True)
    #: the same name can be used again under another parent (e.g. "person"
    #: under "Outdoor/Street" and "Indoor/Hall"): unique per creator and first parent
    name = StringField(required=True, unique_with=['creator', 'supercategory'])
    #: COCO's single parent: the first of ``supercategories``
    supercategory = StringField(default='')
    #: all parent categories (a category can be in several groups). A parent
    #: is a path: "Vehicles/Land" is "Land" inside "Vehicles" (any depth)
    supercategories = ListField(StringField(), default=[])

    #: the unique index of older versions (name per creator only)
    OLD_UNIQUE_INDEX = 'name_1_creator_1'

    @classmethod
    def drop_old_unique_index(cls):
        """Older databases have a unique (name, creator) index that would still
        refuse the same name under another parent."""
        try:
            collection = cls._get_collection()
            if cls.OLD_UNIQUE_INDEX in collection.index_information():
                collection.drop_index(cls.OLD_UNIQUE_INDEX)
        except Exception:  # pragma: no cover
            pass
    color = StringField(default=None)
    metadata = DictField(default={})

    creator = StringField(default='unknown')
    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    keypoint_edges = ListField(default=[])
    keypoint_labels = ListField(default=[])
    keypoint_colors = ListField(default=[])

    @staticmethod
    def normalize_path(value):
        """ "Vehicles / Land " -> "Vehicles/Land" (a parent path, any depth)"""
        import re
        parts = [p.strip() for p in re.split(r"[/／]", str(value or ''))]
        return '/'.join(p for p in parts if p)

    @staticmethod
    def ancestors(path):
        """ "a/b/c" -> ["a", "a/b", "a/b/c"] """
        parts = [p for p in str(path or '').split('/') if p]
        return ['/'.join(parts[:i + 1]) for i in range(len(parts))]

    @classmethod
    def parse_parents(cls, value):
        """A list or "a, b、c" -> unique, trimmed parent paths (in order)."""
        import re
        if value is None:
            return []
        items = value if isinstance(value, (list, tuple)) else re.split(r"[,，、;；\n]+", str(value))
        out = []
        for item in items:
            name = cls.normalize_path(item)
            if name and name not in out:
                out.append(name)
        return out[:20]

    def parents(self):
        return list(self.supercategories or []) or self.parse_parents(self.supercategory)

    def set_parents(self, parents):
        """Fields to update for these parents (supercategory = the first one)."""
        parents = self.parse_parents(parents)
        return {'supercategories': parents, 'supercategory': parents[0] if parents else ''}

    @classmethod
    def bulk_create(cls, categories, create=True):
        """Category ids for a list of ids (existing categories) and names
        (found, or created without a parent). With ``create`` False a name
        that would need a new category raises CategoryCreateDenied (the user
        may not make categories)."""

        if not categories:
            return []

        category_ids = []
        for category in categories:
            if isinstance(category, int) or (isinstance(category, str) and category.isdigit()
                                             and CategoryModel.objects(id=int(category)).first()):
                category_model = CategoryModel.objects(id=int(category)).first()
                if category_model is None:
                    continue
            else:
                # the same name can exist under several parents: the one without a
                # parent, or the only one of that name; else a new one (no parent)
                category_model = CategoryModel.objects(name=category, supercategory__in=['', None]).first()
                if category_model is None:
                    same = CategoryModel.objects(name=category)
                    category_model = same.first() if same.count() == 1 else None

            if category_model is not None and category_model.deleted:
                # in the trash: picking it again brings it back
                category_model.update(set__deleted=False, unset__deleted_date=True,
                                      unset__deleted_by=True, unset__delete_batch=True)

            if category_model is None and not create:
                raise CategoryCreateDenied(category)
            if category_model is None:
                new_category = CategoryModel(name=category)
                new_category.save()
                category_ids.append(new_category.id)
            elif category_model.id not in category_ids:
                category_ids.append(category_model.id)

        return category_ids

    def save(self, *args, **kwargs):

        if not self.color:
            self.color = random_color()

        if current_user:
            self.creator = current_user.username
        else:
            self.creator = 'system'
      
        return super(CategoryModel, self).save(*args, **kwargs)

    
    def is_owner(self, user):

        if user.is_admin or user.has_perm('manage_categories'):
            return True

        return user.username.lower() == (self.creator or '').lower()
    
    def can_edit(self, user):
        return self.is_owner(user)
    
    def can_delete(self, user):
        return self.is_owner(user)


__all__ = ["CategoryModel", "CategoryCreateDenied"]