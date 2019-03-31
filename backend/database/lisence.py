from mongoengine import *


class LicenseModel(DynamicDocument):
    id = SequenceField(primary_key=True)
    name = StringField()
    url = StringField()


__all__ = ["LicenseModel"]