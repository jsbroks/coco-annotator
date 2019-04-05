from mongoengine import *

import datetime


class TaskModel(DynamicDocument):
    id = SequenceField(primary_key=True)
    
    # Type of task: Importer, Exporter, Scanner, etc.
    group = StringField(required=True)
    name = StringField(required=True) 
    desciption = StringField()
    status = StringField(default="PENDING")
    creator = StringField()

    #: Start date of the executor 
    start_date = DateTimeField()
    #: End date of the executor 
    end_date = DateTimeField()
    completed = BooleanField(default=False)
    failed = BooleanField(default=False)
    has_download = BooleanField(default=False)
    
    # If any of the information is relevant to the task
    # it should be added
    dataset_id = IntField()
    image_id = IntField()
    category_id = IntField()

    progress = FloatField(default=0, min_value=0, max_value=100)

    logs = ListField(default=[])
    errors = IntField(default=0)
    warnings = IntField(default=0)

    priority = IntField()

    metadata = DictField(default={})

    _update_every = 10
    _progress_update = 0

    def error(self, string):
        self._log(string, level="ERROR")
    
    def warning(self, string):
        self._log(string, level="WARNING")
    
    def info(self, string):
        self._log(string, level="INFO")
    
    def _log(self, string, level):

        level = level.upper()
        date = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        message = f"[{date}] [{level}] {string}"

        statment = {
            'push__logs': message
        }

        if level == "ERROR":
            statment['inc__errors'] = 1
            self.errors += 1
        
        if level == "WARNING":
            statment['inc__warnings'] = 1
            self.warnings += 1

        self.update(**statment)

    def set_progress(self, percent, socket=None):

        self.update(progress=int(percent), completed=(percent >= 100))

        # Send socket update every 10%
        if self._progress_update < percent or percent >= 100:
            
            if socket is not None:
                # logger.debug(f"Emitting {percent} progress update for task {self.id}")

                socket.emit('taskProgress', {
                    'id': self.id,
                    'progress': percent,
                    'errors': self.errors,
                    'warnings': self.warnings
                }, broadcast=True)
            
            self._progress_update += self._update_every
    
    def api_json(self):
        return {
            "id": self.id,
            "name": self.name
        }


__all__ = ["TaskModel"]