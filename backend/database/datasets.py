
from flask_login import current_user
from mongoengine import *
from config import Config

from .tasks import TaskModel

import os


class DatasetModel(DynamicDocument):
    
    id = SequenceField(primary_key=True)
    name = StringField(required=True, unique=True)
    directory = StringField()
    thumbnails = StringField()
    categories = ListField(default=[])

    owner = StringField(required=True)
    users = ListField(default=[])
    # what the dataset is for: detect, segment, obb, pose, classify, semantic ('' = not set)
    task = StringField(default="")
    # members who may approve / reject images (the owner always can)
    reviewers = ListField(default=[])

    annotate_url = StringField(default="")

    default_annotation_metadata = DictField(default={})

    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    def save(self, *args, **kwargs):

        directory = os.path.join(Config.DATASET_DIRECTORY, self.name + '/')
        os.makedirs(directory, mode=0o777, exist_ok=True)

        self.directory = directory
        self.owner = current_user.username if current_user else 'system'

        return super(DatasetModel, self).save(*args, **kwargs)

    def get_users(self):
        from .users import UserModel
    
        # (a copy: appending to self.users would change the dataset in memory)
        members = list(self.users or []) + [self.owner]

        return UserModel.objects(username__in=members)\
            .exclude('password', 'id', 'preferences')

    def _log(self, action, user, task, **detail):
        """Activity line for a background task; the task fills in the numbers."""
        from .activity import ActivityModel
        try:
            ActivityModel(action=action, user=getattr(user, 'username', None), dataset_id=self.id,
                          task_id=task.id, detail={'dataset_name': self.name, **detail},
                          text=f"{self.name} {' '.join(str(v) for v in detail.values() if v)}".lower(),
                          hidden=action == 'scan').save()
        except Exception:  # pragma: no cover - the log must not stop the task
            pass

    def import_coco(self, coco_json, style="COCO", user=None, create_categories=True):

        from workers.tasks import import_annotations

        task = TaskModel(
            name="Import {} format into {}".format(style, self.name),
            dataset_id=self.id,
            group="Annotation Import"
        )
        if user is not None:
            task.creator = user.username
        task.save()
        self._log('import', user, task, format=style)

        cel_task = import_annotations.delay(task.id, self.id, coco_json, create_categories)

        return {
            "celery_id": cel_task.id,
            "id": task.id,
            "name": task.name
        }

    def export_coco(self, categories=None, style="COCO", with_empty_images=False,
                    fmt="coco", yolo_task="detect", with_images=False, split=None, seed=42,
                    folder=None, only_approved=False, augment=None, user=None, merge=None):
        """``merge``: other datasets (ids) exported together with this one into
        one file; categories with the same name become one."""

        from workers.tasks import export_annotations

        merge = [i for i in (merge or []) if i != self.id]
        if categories is None or len(categories) == 0:
            categories = list(self.categories or [])
            for other in DatasetModel.objects(id__in=merge).only('categories'):
                categories += [c for c in (other.categories or []) if c not in categories]

        if fmt == "yolo":
            style = f"YOLO {yolo_task}"
        names = self.name
        if merge:
            others = [d.name for d in DatasetModel.objects(id__in=merge).only('name')]
            names = " + ".join([self.name] + others)
        task = TaskModel(
            name=f"Exporting {names} into {style} format",
            dataset_id=self.id,
            group="Annotation Export"
        )
        if user is not None:
            task.creator = user.username
        task.save()
        self._log('export', user, task, format=style, split=bool(split), only_approved=only_approved or None,
                  augment=augment or None, merged=merge or None)

        cel_task = export_annotations.delay(task.id, self.id, categories, with_empty_images,
                                            fmt, yolo_task, with_images, split, seed, folder,
                                            only_approved, augment, merge or None)

        return {
            "celery_id": cel_task.id,
            "id": task.id,
            "name": task.name
        }

    def scan(self, user=None):

        from workers.tasks import scan_dataset
        
        task = TaskModel(
            name=f"Scanning {self.name} for new images",
            dataset_id=self.id,
            group="Directory Image Scan"
        )
        if user is not None:
            task.creator = user.username
        task.save()
        self._log('scan', user, task)
        
        cel_task = scan_dataset.delay(task.id, self.id)

        return {
            "celery_id": cel_task.id,
            "id": task.id,
            "name": task.name
        }

    def is_owner(self, user):

        if user.is_admin:
            return True
        
        return user.username.lower() == self.owner.lower()

    def can_download(self, user):
        return self.is_owner(user)

    def can_delete(self, user):
        return self.is_owner(user)
    
    def can_share(self, user):
        return self.is_owner(user)
    
    def can_generate(self, user):
        return self.is_owner(user)

    def can_edit(self, user):
        return user.username in self.users or self.is_owner(user)

    def is_creator(self, user):
        """The person who created the dataset (being an admin is not enough)."""
        return bool(self.owner) and user.username.lower() == self.owner.lower()

    def is_reviewer(self, user):
        """Chosen as a reviewer and still a member of the dataset."""
        return user.username in (self.reviewers or []) and user.username in (self.users or [])

    def can_review(self, user):
        """Approve / reject: only the creator and the reviewers the creator chose
        (not admins as such)."""
        return self.is_creator(user) or self.is_reviewer(user)

    def can_assign(self, user):
        return self.is_owner(user) or self.is_reviewer(user)
    
    def permissions(self, user):
        return {
            'owner': self.is_owner(user),
            'edit': self.can_edit(user),
            'review': self.can_review(user),
            'share': self.can_share(user),
            'generate': self.can_generate(user),
            'delete': self.can_delete(user),
            'download': self.can_download(user)
        }


__all__ = ["DatasetModel"]
