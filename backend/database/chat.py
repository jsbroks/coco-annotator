"""Chat: one room per dataset, for its members."""
import datetime

from mongoengine import DynamicDocument, SequenceField, IntField, StringField, DateTimeField, ListField


class ChatMessageModel(DynamicDocument):
    id = SequenceField(primary_key=True)
    dataset_id = IntField(required=True)
    user = StringField(required=True)
    text = StringField(default='')
    #: the image the message is about (optional, from the annotator)
    image_id = IntField()
    file_name = StringField(default='')
    #: photos sent with it (ChatPhotoModel ids)
    photos = ListField(StringField(), default=list)
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    meta = {'collection': 'chat_message', 'indexes': [('dataset_id', '-id')]}

    def to_dict(self, names=None, photos=None):
        return {
            'id': self.id, 'dataset_id': self.dataset_id, 'user': self.user,
            'name': (names or {}).get(self.user) or self.user,
            'text': self.text, 'image_id': self.image_id, 'file_name': self.file_name or '',
            'photos': [(photos or {}).get(p, {'id': p}) for p in (self.photos or [])],
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class ChatReadModel(DynamicDocument):
    """The last message a user has seen in a dataset's room."""
    user = StringField(required=True)
    dataset_id = IntField(required=True)
    last_id = IntField(default=0)

    meta = {'collection': 'chat_read', 'indexes': [{'fields': ['user', 'dataset_id'], 'unique': True}]}


class ChatPhotoModel(DynamicDocument):
    """A photo sent in a dataset's chat (stored under the datasets folder,
    in .chat/<dataset id>/)."""
    id = StringField(primary_key=True)
    dataset_id = IntField(required=True)
    user = StringField(required=True)
    filename = StringField(required=True)
    width = IntField(default=0)
    height = IntField(default=0)
    size = IntField(default=0)
    #: the message it was sent with (None: uploaded, not sent yet)
    message_id = IntField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    meta = {'collection': 'chat_photo', 'indexes': ['dataset_id', 'message_id']}

    def to_dict(self):
        return {'id': self.id, 'w': self.width, 'h': self.height}
