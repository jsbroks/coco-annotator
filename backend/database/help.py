"""Questions while annotating: an annotator asks the dataset's creator /
reviewers for help on one image; they answer there."""
import datetime

from mongoengine import (DynamicDocument, SequenceField, IntField, StringField, ListField,
                         DateTimeField, DictField, BooleanField)


class HelpModel(DynamicDocument):
    id = SequenceField(primary_key=True)
    image_id = IntField(required=True)
    dataset_id = IntField()
    file_name = StringField(default='')
    #: who asks
    user = StringField(required=True)
    #: who is asked (creator / reviewers picked by the asker)
    to = ListField(StringField(), default=list)
    message = StringField(default='')
    #: the annotation the question is about (optional)
    annotation_id = IntField()
    #: the part of the image the asker zoomed to: {x, y, w, h} in image pixels
    region = DictField(default=None)
    status = StringField(default='open')  # open | resolved | cancelled
    #: [{user, message, at}]
    replies = ListField(DictField(), default=list)
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    updated_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    resolved_by = StringField()
    #: the asker has seen the answer (it leaves their lists)
    seen = BooleanField(default=False)

    meta = {'collection': 'help_request', 'indexes': ['image_id', 'to', 'user', 'status']}

    def to_dict(self):
        def iso(d):
            return d.isoformat() + 'Z' if d else None
        return {
            'id': self.id, 'image_id': self.image_id, 'dataset_id': self.dataset_id,
            'file_name': self.file_name, 'user': self.user, 'to': list(self.to or []),
            'message': self.message, 'annotation_id': self.annotation_id, 'status': self.status,
            'region': self.region or None,
            'replies': [{**r, 'at': iso(r.get('at')) if isinstance(r.get('at'), datetime.datetime) else r.get('at')}
                        for r in (self.replies or [])],
            'created_at': iso(self.created_at), 'updated_at': iso(self.updated_at),
            'resolved_by': self.resolved_by, 'seen': bool(self.seen),
        }
