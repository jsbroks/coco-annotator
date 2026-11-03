from mongoengine import *

import datetime


class ModelInfoModel(DynamicDocument):
    """Settings and history of an uploaded YOLO model (the .pt file itself is
    in the models folder; this is keyed by its file name)."""
    name = StringField(primary_key=True)
    display_name = StringField(default="")
    note = StringField(default="")
    #: hidden from the "run a model" dialog and refused by the API when False
    enabled = BooleanField(default=True)
    #: confidence the run dialog starts with for this model
    default_conf = FloatField()
    uploaded_by = StringField()
    uploaded_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


__all__ = ["ModelInfoModel"]
