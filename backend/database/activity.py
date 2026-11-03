from mongoengine import *

import datetime


class ActivityModel(DynamicDocument):
    """One line of the activity log ("tester imported 120 annotations into ships").

    Repeated small actions (annotating one image, uploading images) are merged
    into one entry while they keep happening; ``updated_at`` is the time of
    the latest one.
    """
    id = SequenceField(primary_key=True)
    action = StringField(required=True)
    user = StringField()
    dataset_id = IntField()
    image_id = IntField()
    category_id = IntField()

    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    updated_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    #: numbers shown in the sentence ({"annotations": 3, ...})
    counts = DictField(default={})
    #: names and other details ({"format": "yolo", "file_name": ...})
    detail = DictField(default={})

    #: deletes: what went to the trash in this action
    batch = StringField()
    items = ListField(default=[])

    #: imports: the task whose annotations / images can be taken back
    task_id = IntField()
    undone_by = StringField()
    undone_at = DateTimeField()

    undo_batch = StringField()

    #: annotate: ids added / changed (pending: created, nothing drawn yet);
    #: hidden until something was actually drawn or changed
    added = ListField(IntField(), default=[])
    edited = ListField(IntField(), default=[])
    pending = ListField(IntField(), default=[])
    hidden = BooleanField(default=False)

    #: lower-case words to search in (file names, categories, dataset)
    text = StringField(default="")

    meta = {
        'indexes': ['-updated_at', 'dataset_id', 'action', 'batch', 'task_id',
                    ('action', 'user', 'image_id'), ('image_id', 'action')]
    }


__all__ = ["ActivityModel"]
