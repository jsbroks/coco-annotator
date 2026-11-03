"""Model training runs (Ultralytics YOLO on a YOLO export), run one at a
time by the trainer service."""
import datetime

from mongoengine import (DynamicDocument, SequenceField, IntField, StringField, ListField,
                         DateTimeField, DictField, BooleanField)

# queued -> running -> done | failed | stopped
STATUSES = ('queued', 'running', 'done', 'failed', 'stopped')


class TrainRunModel(DynamicDocument):
    id = SequenceField(primary_key=True)
    name = StringField(default='')
    creator = StringField()
    export_id = IntField(required=True)
    dataset_id = IntField()
    dataset_names = ListField(StringField(), default=list)
    task = StringField(default='detect')
    #: model (base weights), epochs, imgsz, batch, patience, device
    params = DictField(default=dict)
    status = StringField(default='queued')
    stop_requested = BooleanField(default=False)
    #: removed as soon as the trainer has stopped it
    delete_requested = BooleanField(default=False)
    epoch = IntField(default=0)
    epochs = IntField(default=0)
    #: one row per finished epoch (columns of Ultralytics' results.csv)
    metrics = ListField(DictField(), default=list)
    log_tail = StringField(default='')
    error = StringField(default='')
    #: the trained weights, as a name in the models folder
    model_name = StringField()
    #: the trainer it must run on (a name; empty: whichever is free)
    target = StringField(default='')
    #: the trainer that runs / ran it
    worker = StringField(default='')
    #: a remote trainer still has its last finished epoch (last.pt), to resume
    has_last = BooleanField(default=False)
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    started_at = DateTimeField()
    ended_at = DateTimeField()

    meta = {'collection': 'train_run', 'indexes': ['status']}

    def to_dict(self, full=False):
        def iso(d):
            return d.isoformat() + 'Z' if d else None
        out = {
            'id': self.id, 'name': self.name, 'creator': self.creator, 'export_id': self.export_id,
            'dataset_id': self.dataset_id, 'dataset_names': list(self.dataset_names or []),
            'task': self.task, 'params': dict(self.params or {}), 'status': self.status,
            'stop_requested': bool(self.stop_requested), 'delete_requested': bool(self.delete_requested), 'epoch': self.epoch, 'epochs': self.epochs,
            'model_name': self.model_name, 'error': self.error,
            'target': self.target or '', 'worker': self.worker or '',
            'created_at': iso(self.created_at), 'started_at': iso(self.started_at), 'ended_at': iso(self.ended_at),
            'last': (self.metrics or [None])[-1],
        }
        if full:
            out['metrics'] = list(self.metrics or [])
            out['log_tail'] = self.log_tail or ''
        return out


class TrainerStatusModel(DynamicDocument):
    """Heartbeat of a trainer (this server's, or a worker on another one):
    is it running, which GPU, what it is training. key: its name."""
    key = StringField(primary_key=True, default='trainer')
    #: local (reads the database) or remote (a worker over the web API)
    kind = StringField(default='local')
    #: the run it is training now (None: free)
    run_id = IntField()
    seen_at = DateTimeField()
    device = StringField(default='')
    version = StringField(default='')
    #: what the trainer's Ultralytics can train (trainer/catalog.py)
    catalog = DictField(default=dict)
    #: its GPU (trainer/gpu.py): name, util, mem_used, mem_total, procs, busy
    #: (used outside this site); None when unknown
    gpu = DictField(default=None, null=True)

    meta = {'collection': 'trainer_status'}


class TrainWorkerModel(DynamicDocument):
    """Another server allowed to train (it connects with its token)."""
    name = StringField(primary_key=True)
    token_hash = StringField(required=True)
    created_by = StringField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    last_ip = StringField(default='')

    meta = {'collection': 'train_worker'}


class TrainUploadModel(DynamicDocument):
    """A model file (.pt weights or .yaml architecture) uploaded for training."""
    id = SequenceField(primary_key=True)
    filename = StringField(required=True)      # stored as, in .training/uploads/
    original = StringField(default='')
    kind = StringField(default='pt')           # pt | yaml
    size = IntField(default=0)
    uploader = StringField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    meta = {'collection': 'train_upload'}

    def to_dict(self):
        return {'id': self.id, 'name': self.original or self.filename, 'kind': self.kind, 'size': self.size,
                'uploader': self.uploader,
                'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None}
