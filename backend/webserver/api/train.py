"""Training YOLO models on the server (the trainer service runs them, one
at a time). Needs the "train" permission."""
import datetime
import json
import os
import re
import shutil
import zipfile

import yaml

from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from database import (DatasetModel, ExportModel, TrainRunModel, TrainerStatusModel, TrainUploadModel,
                      TrainWorkerModel)
from trainer import catalog as model_catalog
from trainer.runner import (TASK_SUFFIX, archive_path, package, queue_resume, resumable, safe_name,
                            uploads_dir, work_dir)
from ..util import activity

api = Namespace('train', description='Train models on the server')

TRAINER_ALIVE_SECONDS = 30
TRAINABLE = tuple(TASK_SUFFIX)  # detect, segment, obb, pose, classify

create_args = reqparse.RequestParser()
create_args.add_argument('export_id', type=int, required=True, location='json')
create_args.add_argument('source', default='catalog', location='json',
                         help='catalog (official .pt / .yaml), models (the models folder) or upload')
create_args.add_argument('model', default='', location='json',
                         help='An official model name: yolo26s.pt (pretrained) or yolo26s.yaml (from scratch)')
create_args.add_argument('family', default='', location='json', help='Older form: family + size')
create_args.add_argument('size', default='n', location='json')
create_args.add_argument('base_model', default='', location='json',
                         help='A model of the models folder (source=models)')
create_args.add_argument('upload_id', type=int, location='json', help='An uploaded model (source=upload)')
create_args.add_argument('extra', type=dict, default=None, location='json',
                         help='More Ultralytics training arguments, {name: value}')
create_args.add_argument('epochs', type=int, default=100, location='json')
create_args.add_argument('imgsz', type=int, default=640, location='json')
create_args.add_argument('batch', type=float, default=-1, location='json',
                         help='Images per batch; -1 automatic, 0.7 = use 70% of the GPU memory')
create_args.add_argument('patience', type=int, default=50, location='json')
create_args.add_argument('name', default='', location='json')
create_args.add_argument('target', default='', location='json',
                         help='The trainer (server) to train on; empty: whichever is free')


upload_args = reqparse.RequestParser()
upload_args.add_argument('file', location='files', type=FileStorage, required=True)

MAX_UPLOAD = 2 * 1024 * 1024 * 1024
MAX_YAML = 1024 * 1024
# set with their own fields (and limits) when given as extra arguments
MAIN_ARGS = ('epochs', 'imgsz', 'batch', 'patience')
_ARG_NAME = re.compile(r'^[a-z][a-z0-9_]{0,40}$')
_MODEL_NAME = re.compile(r'^[a-z0-9][a-z0-9.-]{0,60}\.(pt|yaml)$')
_local_catalog = None


def _allowed():
    return current_user.has_perm('train')


def _alive(row):
    return bool(row and row.seen_at and
                (datetime.datetime.utcnow() - row.seen_at).total_seconds() < TRAINER_ALIVE_SECONDS)


def _trainer_alive(name):
    """Whether the trainer of that name reports (unknown name: assume so)."""
    if not name:
        return True
    return _alive(TrainerStatusModel.objects(key=name).first())


def _gpu_of(r):
    """What the trainer's GPU is doing (None: not known), ``busy``: used
    outside this site while the trainer is free (it takes nothing then)."""
    gpu = getattr(r, 'gpu', None) if r is not None else None
    if not gpu or not _alive(r):
        return None
    gpu = dict(gpu)
    gpu['busy'] = bool(gpu.get('busy')) and not r.run_id
    return gpu


def trainers():
    """Every trainer: this server's and the other servers' (registered, or
    seen in the last day), alive or not."""
    workers = {w.name for w in TrainWorkerModel.objects.only('name')}
    recent = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    rows = {r.key: r for r in TrainerStatusModel.objects}
    out = []
    for key in sorted(set(rows) | workers, key=lambda k: (rows.get(k) is None or rows[k].kind != 'local', k)):
        r = rows.get(key)
        if r is None and key not in workers:
            continue
        if r is not None and key not in workers and (r.kind or 'local') == 'remote':
            continue  # a worker that was removed
        if r is not None and key not in workers and (not r.seen_at or r.seen_at < recent):
            continue
        out.append({'name': key, 'kind': (r.kind if r else 'remote') or 'local', 'alive': _alive(r),
                    'device': r.device if r else '', 'version': r.version if r else '',
                    'run_id': r.run_id if r else None,
                    'gpu': _gpu_of(r),
                    'seen_at': r.seen_at.isoformat() + 'Z' if r and r.seen_at else None})
    return out


def _catalog():
    """What the trainers can train (each publishes it when it starts: this
    server's first); before any ran, what this server's Ultralytics knows."""
    global _local_catalog
    rows = sorted(TrainerStatusModel.objects.only('catalog', 'kind', 'seen_at'),
                  key=lambda r: (not _alive(r), r.kind != 'local'))
    for row in rows:
        if row.catalog and row.catalog.get('families'):
            return row.catalog
    if _local_catalog is None:
        _local_catalog = model_catalog.build()
    return _local_catalog


def _archive(run):
    """The zip of the run's outputs: its size, or whether it can be made"""
    if run.status in ('queued', 'running'):
        return None
    path = archive_path(run.id)
    if os.path.isfile(path):
        return {'size': os.path.getsize(path)}
    if os.path.isdir(os.path.join(work_dir(run.id), 'runs', 'train')):
        return {'size': None}  # packed when downloaded (runs from before)
    return None


def _fitness_weights():
    return _catalog().get('fitness') or [0.0, 0.0, 0.1, 0.9]


def _best(run, weights):
    """Which epoch best.pt is (as Ultralytics picks it)"""
    best = model_catalog.best_epoch(run.metrics or [], weights)
    if best is not None:
        best = {k: v for k, v in best.items() if k != 'row'} | {
            'metrics': {k: v for k, v in best['row'].items() if k.startswith('metrics/')}}
    return best


def _catalog_model(name, catalog):
    """(name, None) for an official model, else (None, error message)."""
    known = model_catalog.names(catalog)
    # no list to check against (Ultralytics not installed here): the form
    if (known and name not in known) or not _MODEL_NAME.match(name or ''):
        return None, f'Unknown model: {name}'
    return name, None


def _check_value(key, value):
    """The value for the command line, or raise ValueError."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        if len(value) > 64 or not all(isinstance(v, (int, float, str)) and not isinstance(v, bool) for v in value):
            raise ValueError(f'{key}: a list may only hold numbers or names')
        for v in value:
            if isinstance(v, str):
                _check_text(key, v)
        return value
    if isinstance(value, str):
        return _check_text(key, value.strip())
    raise ValueError(f'{key}: unsupported value')


def _check_text(key, text):
    if len(text) > 200 or any(c in text for c in '\r\n\0'):
        raise ValueError(f'{key}: value too long or on several lines')
    # no files of the server: only the trainer decides those
    if '/' in text or '\\' in text or '..' in text:
        raise ValueError(f'{key}: paths are not allowed')
    return text


def check_extra(extra, catalog, upload_path=None):
    """Validated extra arguments: (args, errors). ``pretrained`` may be
    true/false, an official .pt name or "upload:<id>" (an uploaded .pt)."""
    known = (catalog or {}).get('args') or {}
    out, errors = {}, []
    for key, value in (extra or {}).items():
        key = str(key).strip()
        if not _ARG_NAME.match(key) or key in model_catalog.BLOCKED_ARGS or (known and key not in known):
            errors.append(f'{key}: not a training argument that can be set here')
            continue
        if key == 'pretrained' and isinstance(value, str) and value.strip().lower() not in ('true', 'false'):
            v = value.strip()
            if v.startswith('upload:'):
                path = upload_path(v[7:]) if upload_path else None
                if path is None or not path.endswith('.pt'):
                    errors.append('pretrained: unknown uploaded weights')
                    continue
                out[key] = path
                continue
            name, err = _catalog_model(v, catalog)
            if err or not name.endswith('.pt'):
                errors.append(f'pretrained: {err or "only .pt weights"}')
                continue
            out[key] = name
            continue
        try:
            out[key] = _check_value(key, value)
        except ValueError as e:
            errors.append(str(e))
    return out, errors


def _upload_path(upload_id):
    try:
        upload = TrainUploadModel.objects(id=int(upload_id)).first()
    except (TypeError, ValueError):
        return None
    if upload is None:
        return None
    path = os.path.join(uploads_dir(), upload.filename)
    return path if os.path.isfile(path) else None


def _export_ok(export):
    """The user may export every dataset of this export."""
    from .exports import export_dataset
    return export_dataset(export) is not None


def run_visible(run, user=None, cache=None):
    """The user may see a run's details, log and outputs (plots show its
    images, best.pt was trained on them): its creator, an admin, or someone
    who may download every dataset it was trained on."""
    user = user or current_user
    if user.is_admin or run.creator == user.username:
        return True
    key = (run.export_id, run.dataset_id)
    if cache is not None and key in cache:
        return cache[key]
    ok = _run_data_visible(run, user)
    if cache is not None:
        cache[key] = ok
    return ok


def _run_data_visible(run, user):
    export = ExportModel.objects(id=run.export_id).first() if run.export_id else None
    if export is not None:
        from .exports import export_dataset
        return export_dataset(export) is not None
    dataset = user.datasets.filter(id=run.dataset_id).first() if run.dataset_id else None
    return dataset is not None and user.can_download(dataset)


def _task_of(export):
    tags = list(export.tags or [])
    return tags[1] if tags[:1] == ["YOLO"] and len(tags) > 1 else None


def _has_images(export):
    try:
        with zipfile.ZipFile(export.path) as zf:
            return any('/images/' in n or n.lower().endswith(('.jpg', '.jpeg', '.png')) for n in zf.namelist())
    except (OSError, zipfile.BadZipFile):
        return False


@api.route('/status')
class TrainerStatus(Resource):

    @login_required
    def get(self):
        """ Is the trainer service running, on which device; queue length """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        all_trainers = trainers()
        alive = [t for t in all_trainers if t['alive']]
        first = alive[0] if alive else (all_trainers[0] if all_trainers else None)
        return {
            'alive': bool(alive), 'device': first['device'] if first else '',
            'trainers': all_trainers, 'can_manage': bool(current_user.is_admin),
            'queued': TrainRunModel.objects(status='queued').count(),
            'running': TrainRunModel.objects(status='running').count(),
            'tasks': list(TRAINABLE), 'version': first['version'] if first else '',
        }


@api.route('/catalog')
class TrainCatalog(Resource):

    @login_required
    def get(self):
        """ Models that can be trained (.pt pretrained / .yaml from scratch) and
        the training arguments with their defaults """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        cat = _catalog()
        return {'families': cat.get('families', []), 'args': cat.get('args', {}),
                'version': cat.get('version'), 'blocked': sorted(model_catalog.BLOCKED_ARGS),
                'fitness': cat.get('fitness') or [0.0, 0.0, 0.1, 0.9],
                'main': list(MAIN_ARGS)}


def _is_yaml_model(data):
    try:
        cfg = yaml.safe_load(data)
    except yaml.YAMLError:
        return False
    return isinstance(cfg, dict) and 'backbone' in cfg and 'head' in cfg


@api.route('/uploads')
class TrainUploads(Resource):

    @login_required
    def get(self):
        """ Model files uploaded for training """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        return {'uploads': [u.to_dict() for u in TrainUploadModel.objects.order_by('-id')]}

    @api.expect(upload_args)
    @login_required
    def post(self):
        """ Upload weights (.pt) or an architecture (.yaml) to train from """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        f = upload_args.parse_args()['file']
        original = os.path.basename(f.filename or '')
        ext = os.path.splitext(original)[1].lower()
        if ext not in ('.pt', '.yaml', '.yml'):
            return {'message': 'Only .pt weights or .yaml model files'}, 400
        if ext == '.pt' and not current_user.has_perm('manage_models'):
            # loading a .pt file runs code from it (pickle), as on the Models page
            return {'message': 'Uploading .pt weights needs the "manage models" permission'}, 403
        os.makedirs(uploads_dir(), exist_ok=True)
        upload = TrainUploadModel(original=original[:120], kind='pt' if ext == '.pt' else 'yaml',
                                  uploader=current_user.username, filename='-')
        upload.save()
        stem = safe_name(os.path.splitext(original)[0])
        # Ultralytics reads the scale from a yaml name (yolo26s.yaml): keep it
        upload.filename = f"{stem}-u{upload.id}{'.pt' if ext == '.pt' else '.yaml'}" if ext == '.pt' \
            else f"u{upload.id}-{stem}.yaml"
        path = os.path.join(uploads_dir(), upload.filename)
        limit = MAX_YAML if ext != '.pt' else MAX_UPLOAD
        size = 0
        with open(path, 'wb') as out:
            while True:
                chunk = f.stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    break
                out.write(chunk)
        bad = None
        if size > limit:
            bad = 'File too large'
        elif ext == '.pt':
            with open(path, 'rb') as fp:
                head = fp.read(4)
            # torch.save writes a zip (old ones a pickle)
            if not (head.startswith(b'PK') or head[:1] == b'\x80'):
                bad = 'Not PyTorch weights'
        else:
            with open(path, 'rb') as fp:
                if not _is_yaml_model(fp.read()):
                    bad = 'Not an Ultralytics model yaml (needs backbone and head)'
        if bad:
            os.remove(path)
            upload.delete()
            return {'message': bad}, 400
        upload.size = size
        upload.save()
        activity.record('train', current_user, detail={'upload': upload.id, 'file': original},
                        text=f"upload {original}")
        return upload.to_dict()


@api.route('/uploads/<int:upload_id>')
class TrainUpload(Resource):

    @login_required
    def delete(self, upload_id):
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        upload = TrainUploadModel.objects(id=upload_id).first()
        if upload is None:
            return {'message': 'Invalid upload'}, 400
        if upload.uploader != current_user.username and not current_user.is_admin:
            return {'message': 'Only its uploader or an admin can remove it'}, 403
        try:
            os.remove(os.path.join(uploads_dir(), upload.filename))
        except OSError:
            pass
        upload.delete()
        return {'success': True}


@api.route('/parse-args')
class TrainParseArgs(Resource):

    @api.expect(upload_args)
    @login_required
    def post(self):
        """ Read an args.yaml (e.g. of an earlier Ultralytics run): the
        arguments that can be used, and those left out """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        data = upload_args.parse_args()['file'].stream.read(MAX_YAML + 1)
        if len(data) > MAX_YAML:
            return {'message': 'File too large'}, 400
        try:
            cfg = yaml.safe_load(data)
        except yaml.YAMLError as e:
            return {'message': f'Not a yaml file: {e}'.splitlines()[0][:200]}, 400
        if not isinstance(cfg, dict):
            return {'message': 'The file has no "name: value" lines'}, 400
        cat = _catalog()
        defaults = cat.get('args') or {}
        args, ignored = {}, []
        for key, value in cfg.items():
            one, errors = check_extra({key: value}, cat)
            if errors:
                ignored.append({'key': str(key), 'reason': errors[0]})
            elif key in defaults and one[key] == defaults[key]:
                continue  # the default anyway
            else:
                args.update(one)
        return {'args': args, 'ignored': ignored}


@api.route('/exports')
class TrainExports(Resource):

    @login_required
    def get(self):
        """ YOLO exports (with images) of the user's datasets that can be trained on """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        out = []
        for dataset in current_user.datasets.filter(deleted=False).only('id', 'name', 'owner', 'users'):
            if not current_user.can_download(dataset):
                continue
            for export in ExportModel.objects(dataset_id=dataset.id).order_by('-id').limit(30):
                task = _task_of(export)
                if task not in TRAINABLE or not export.path or not os.path.isfile(export.path):
                    continue
                if not _has_images(export):
                    continue
                if getattr(export, 'dataset_ids', None) and not _export_ok(export):
                    continue
                out.append({
                    'id': export.id, 'task': task, 'dataset_id': dataset.id,
                    'datasets': list(getattr(export, 'dataset_names', None) or [dataset.name]),
                    'categories': list(export.tags or [])[2:],
                    'split': getattr(export, 'split', None),
                    'split_counts': getattr(export, 'split_counts', None),
                    'augment': getattr(export, 'augment', None),
                    'size': os.path.getsize(export.path),
                    'created_at': export.created_at.replace(microsecond=0).isoformat() + 'Z',
                })
        out.sort(key=lambda e: -e['id'])
        return {'exports': out}


@api.route('/')
class TrainRuns(Resource):

    @login_required
    def get(self):
        """ Training runs (everyone with the permission sees the shared queue) """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        runs = TrainRunModel.objects.order_by('-id').limit(100)
        queued = [r.id for r in TrainRunModel.objects(status='queued').order_by('id').only('id')]
        weights = _fitness_weights()
        visible = {}
        out = []
        for r in runs:
            d = r.to_dict()
            d['queue_position'] = queued.index(r.id) + 1 if r.id in queued else None
            d['best'] = _best(r, weights)
            d['archive'] = _archive(r) if run_visible(r, cache=visible) else None
            d['resumable'] = resumable(r)
            out.append(d)
        return {'runs': out}

    @api.expect(create_args)
    @login_required
    def post(self):
        """ Queue a training on a YOLO export """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        args = create_args.parse_args()
        export = ExportModel.objects(id=args['export_id']).first()
        if export is None or not _export_ok(export):
            return {'message': 'Invalid export'}, 400
        task = _task_of(export)
        if task not in TRAINABLE:
            return {'message': 'Only YOLO exports (detect, segment, obb, pose, classify) can be trained on'}, 400
        if not export.path or not os.path.isfile(export.path) or not _has_images(export):
            return {'message': 'The export has no images: export again with "images in the zip"'}, 400

        cat = _catalog()
        source = args.get('source') or 'catalog'
        if args.get('base_model'):
            source = 'models'
        upload = None
        if source == 'models':
            from ..util.yolo import YoloService
            from config import Config
            try:
                YoloService(Config.MODELS_DIRECTORY).path_for(args['base_model'])
            except ValueError:
                return {'message': 'Unknown model'}, 400
            model = os.path.join(Config.MODELS_DIRECTORY, args['base_model'])
            label = args['base_model']
        elif source == 'upload':
            upload = TrainUploadModel.objects(id=args.get('upload_id') or 0).first()
            model = _upload_path(upload.id) if upload else None
            if model is None:
                return {'message': 'Unknown uploaded model'}, 400
            label = upload.original
        elif source == 'catalog':
            name = args.get('model') or ''
            if not name:  # older form (family + size), or the smallest of the newest
                name = f"{args.get('family') or 'yolo26'}{args.get('size') or 'n'}{TASK_SUFFIX.get(task, '')}.pt"
            name, err = _catalog_model(name, cat)
            if err:
                return {'message': err}, 400
            if model_catalog.task_of(name) != task:
                return {'message': f'{name} is a {model_catalog.task_of(name)} model; the export is {task}'}, 400
            model = label = name
        else:
            return {'message': 'Unknown model source'}, 400

        extra, errors = check_extra(args.get('extra') or {}, cat, _upload_path)
        if errors:
            return {'message': '; '.join(errors)}, 400
        if extra.get('pretrained') and not isinstance(extra['pretrained'], bool) and not model.endswith('.yaml'):
            return {'message': 'pretrained weights are for a .yaml model (a .pt already has its weights)'}, 400
        for key in MAIN_ARGS:
            if key in extra:
                try:
                    value = float(extra.pop(key))
                    args[key] = value if key == 'batch' else int(value)
                except (TypeError, ValueError):
                    return {'message': f'{key}: a number'}, 400
        epochs = max(1, min(int(args['epochs']), 1000))
        imgsz = max(32, min(int(args['imgsz']), 2048)) // 32 * 32
        batch = float(args['batch'])
        batch = round(batch, 2) if 0 < batch < 1 else (-1 if batch < 1 else min(int(batch), 512))
        patience = max(0, min(int(args['patience']), 1000))

        target = (args.get('target') or '').strip()
        if target and target not in {t['name'] for t in trainers()}:
            return {'message': f'Unknown trainer: {target}'}, 400

        dataset = DatasetModel.objects(id=export.dataset_id).first()
        names = list(getattr(export, 'dataset_names', None) or ([dataset.name] if dataset else []))
        run = TrainRunModel(
            name=(args.get('name') or '').strip()[:100] or " + ".join(names),
            creator=current_user.username, export_id=export.id, dataset_id=export.dataset_id,
            dataset_names=names, task=task, epochs=epochs, target=target,
            params={'model': model, 'label': label, 'source': source,
                    'base_model': args.get('base_model') or None, 'upload_id': upload.id if upload else None,
                    'epochs': epochs, 'imgsz': imgsz, 'batch': batch, 'patience': patience,
                    'extra': extra,
                    # what the export already did (kept: the export may be removed later)
                    'export_augment': getattr(export, 'augment', None)})
        run.save()
        activity.record('train', current_user, dataset_id=export.dataset_id,
                        detail={'run': run.id, 'export_id': export.id, 'task': task, 'model': label,
                                'epochs': epochs}, text=f"{run.name} {task}")
        return run.to_dict()


@api.route('/<int:run_id>')
class TrainRun(Resource):

    @login_required
    def get(self, run_id):
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None or not run_visible(run):
            return {'message': 'Invalid run'}, 400
        out = run.to_dict(full=True)
        out['best'] = _best(run, _fitness_weights())
        out['archive'] = _archive(run)
        out['resumable'] = resumable(run)
        out['fitness_weights'] = _fitness_weights()
        params = out.setdefault('params', {}) or {}
        if 'export_augment' not in params:  # runs queued before this was kept
            export = ExportModel.objects(id=run.export_id).only('augment').first()
            params['export_augment'] = getattr(export, 'augment', None) if export else None
        return out

    @login_required
    def delete(self, run_id):
        """ Remove a run and its working files (a model already saved to the
        models folder stays). A running one is stopped first and removed by
        the trainer then, without saving a model. """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None:
            return {'message': 'Invalid run'}, 400
        if run.creator != current_user.username and not current_user.is_admin:
            return {'message': 'Only its creator or an admin can remove it'}, 403
        if run.status == 'running' and _trainer_alive(run.worker):
            run.update(set__stop_requested=True, set__delete_requested=True)
            return {'success': True, 'deleting': True}
        if run.status == 'queued':
            # not started: gone now (unless the trainer just took it)
            if not TrainRunModel.objects(id=run.id, status='queued').update_one(set__status='stopped'):
                run.update(set__stop_requested=True, set__delete_requested=True)
                return {'success': True, 'deleting': True}
        shutil.rmtree(work_dir(run.id), ignore_errors=True)
        run.delete()
        return {'success': True}


@api.route('/<int:run_id>/resume')
class TrainRunResume(Resource):

    @login_required
    def post(self, run_id):
        """ Go on from the last finished epoch of a stopped or failed training
        (queued again; same arguments, same data) """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None:
            return {'message': 'Invalid run'}, 400
        if run.creator != current_user.username and not current_user.is_admin:
            return {'message': 'Only its creator or an admin can resume it'}, 403
        if not resumable(run):
            return {'message': 'Nothing to resume: no finished epoch, or it reached its epochs'}, 400
        queue_resume(run)
        activity.record('train', current_user, dataset_id=run.dataset_id,
                        detail={'run': run.id, 'resume': True, 'after_epoch': run.epoch},
                        text=f"{run.name} resume")
        return TrainRunModel.objects(id=run.id).first().to_dict()


@api.route('/<int:run_id>/download')
class TrainRunDownload(Resource):

    @login_required
    def get(self, run_id):
        """ Everything the training wrote (runs/train: weights best.pt / last.pt,
        results.csv, args.yaml, plots) and its output, as a zip """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None or not run_visible(run):
            return {'message': 'Invalid run'}, 400
        if run.status in ('queued', 'running'):
            return {'message': 'The training has not finished'}, 400
        path = archive_path(run.id)
        if not os.path.isfile(path) and package(run) is None:
            return {'message': 'This training wrote nothing'}, 404
        from flask import send_file
        name = f"{safe_name('+'.join(run.dataset_names or ['train']))}-{run.task}-run{run.id}.zip"
        return send_file(path, download_name=name, as_attachment=True, max_age=0)


MAX_STEPS = 4000


@api.route('/<int:run_id>/steps')
class TrainRunSteps(Resource):

    @login_required
    def get(self, run_id):
        """ The losses within each epoch (from the progress bar), at most
        4000 points (each epoch's end always kept) """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None or not run_visible(run):
            return {'message': 'Invalid run'}, 400
        from ..train_live import read_steps
        points = read_steps(os.path.join(work_dir(run_id), 'steps.jsonl'))
        total = len(points)
        if total > MAX_STEPS:
            every = -(-total // MAX_STEPS)
            points = [p for i, p in enumerate(points)
                      if i % every == 0 or i == total - 1 or float(p.get('x', 0)).is_integer()]
        return {'points': points, 'total': total}


@api.route('/<int:run_id>/stop')
class TrainRunStop(Resource):

    @login_required
    def post(self, run_id):
        """ Stop a running training (the weights so far are kept) or cancel a queued one """
        if not _allowed():
            return {'message': 'No permission to train models'}, 403
        run = TrainRunModel.objects(id=run_id).first()
        if run is None:
            return {'message': 'Invalid run'}, 400
        if run.creator != current_user.username and not current_user.is_admin:
            return {'message': 'Only its creator or an admin can stop it'}, 403
        if run.status == 'queued':
            TrainRunModel.objects(id=run.id, status='queued').update_one(
                set__status='stopped', set__ended_at=datetime.datetime.utcnow())
        elif run.status == 'running':
            run.update(set__stop_requested=True)
            if not _trainer_alive(run.worker):
                # its trainer is gone (off, unreachable): nothing will stop it
                run.update(set__status='stopped', set__ended_at=datetime.datetime.utcnow(),
                           set__error='its trainer was not running')
        return TrainRunModel.objects(id=run.id).first().to_dict()
