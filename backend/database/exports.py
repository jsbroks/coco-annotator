from mongoengine import *

import datetime
import time


class ExportModel(DynamicDocument):
    
    id = SequenceField(primary_key=True)
    dataset_id = IntField(required=True)
    path = StringField(required=True)
    tags = ListField(default=[])
    categories = ListField(default=[])
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    
    def get_file(self):
        return


__all__ = ["ExportModel"]