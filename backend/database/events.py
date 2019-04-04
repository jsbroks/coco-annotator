from mongoengine import *

import datetime
import time


class Event(EmbeddedDocument):
    
    name = StringField()
    created_at = DateTimeField()

    meta = {'allow_inheritance': True}

    def now(self, event):
        self.created_at = datetime.datetime.now()


class SessionEvent(Event):

    user = StringField(required=True)
    milliseconds = IntField(default=0, min_value=0)
    tools_used = ListField(default=[])

    @classmethod
    def create(self, start, user, end=None, tools=[]):

        if end is None:
            end = time.time()

        return SessionEvent(
            user=user.username,
            milliseconds=int((end-start)*1000)
        )


__all__ = ["Event", "SessionEvent"]