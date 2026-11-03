"""Trainers on other servers ("workers"): they connect with their token
(header X-Worker-Token), take queued trainings meant for them or for any
trainer, get the export and model files from here, and send back the output,
the curves, and at the end the trained model and the results zip.

The same files as a local training are written here (train.log,
progress.txt, steps.jsonl in the run's folder), so the page shows a remote
training like a local one."""
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil

from flask import request, send_file
from flask_login import current_user, login_required
from flask_restx import Namespace, Resource

from database import ExportModel, TrainRunModel, TrainerStatusModel, TrainWorkerModel
from trainer.runner import (_trim_steps, archive_path, claim_next, heartbeat, models_dir, queue_resume,
                            safe_name, work_dir)

api = Namespace('worker', description='Trainers on other servers (token in X-Worker-Token)')

NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$')
MAX_LINES = 2000


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_token():
    return 'cw_' + secrets.token_urlsafe(32)


def _worker():
    """The worker the request comes from (its token), or None."""
    token = request.headers.get('X-Worker-Token') or ''
    if not token:
        return None
    digest = token_hash(token)
    for w in TrainWorkerModel.objects:
        if hmac.compare_digest(w.token_hash, digest):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
            if ip and ip != w.last_ip:
                w.update(set__last_ip=ip)
            return w
    return None


def _num(value):
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def _gpu(data):
    """The GPU a worker reports (trainer/gpu.py), kept small; None: unknown."""
    g = data.get('gpu')
    if not isinstance(g, dict):
        return None
    procs = [{'pid': _num(p.get('pid')), 'name': str(p.get('name') or '')[:60], 'mem': _num(p.get('mem'))}
             for p in (g.get('procs') or [])[:8] if isinstance(p, dict)]
    return {'name': str(g.get('name') or '')[:100], 'util': _num(g.get('util')),
            'mem_used': _num(g.get('mem_used')), 'mem_total': _num(g.get('mem_total')),
            'busy': bool(g.get('busy')), 'procs': procs}


def _denied():
    return {'message': 'Unknown or removed trainer token'}, 401


def _run_of(worker, run_id):
    run = TrainRunModel.objects(id=run_id).first()
    if run is None or run.worker != worker.name:
        return None
    return run


def _files(run):
    """Files of this server a training uses (an uploaded or a Models page
    model, uploaded pretrained weights, official weights it has downloaded
    already): the worker downloads them."""
    base = os.path.realpath(models_dir())
    out = []
    p = run.params or {}
    for field, value in (('model', p.get('model')), ('pretrained', (p.get('extra') or {}).get('pretrained'))):
        if isinstance(value, str) and value.endswith('.pt') and os.sep not in value and '/' not in value:
            # official weights this server already downloaded: the worker
            # need not reach the internet for them
            value = os.path.join(base, '.training', 'base', value)
        if isinstance(value, str) and os.path.isabs(value):
            path = os.path.realpath(value)
            if path.startswith(base + os.sep) and os.path.isfile(path):
                out.append({'field': field, 'index': len(out), 'name': os.path.basename(path),
                            'size': os.path.getsize(path), 'path': path})
    return out


def job(run):
    """What a worker needs to run a training."""
    export = ExportModel.objects(id=run.export_id).first()
    files = _files(run)
    return {
        'id': run.id, 'task': run.task, 'epoch': run.epoch or 0, 'epochs': run.epochs or 0,
        'params': dict(run.params or {}), 'dataset_names': list(run.dataset_names or []),
        'export': {'id': run.export_id, 'folder': getattr(export, 'folder', None) if export else None,
                   'available': bool(export and export.path and os.path.isfile(export.path)),
                   # the worker keeps exports it downloaded: same file, no new download
                   'size': os.path.getsize(export.path) if export and export.path and os.path.isfile(export.path) else 0,
                   'mtime': int(os.path.getmtime(export.path)) if export and export.path and os.path.isfile(export.path) else 0},
        'files': [{k: v for k, v in f.items() if k != 'path'} for f in files],
    }


@api.route('/hello')
class WorkerHello(Resource):

    def post(self):
        """ A worker starts: what it can train; its trainings left running
        (it stopped) go on from their last epoch if it still has it """
        worker = _worker()
        if worker is None:
            return _denied()
        data = request.get_json(silent=True) or {}
        catalog = data.get('catalog') if isinstance(data.get('catalog'), dict) else None
        heartbeat(str(data.get('device') or '')[:200], catalog, name=worker.name, kind='remote', run_id=None)
        kept = {int(i) for i in data.get('resumable') or [] if str(i).isdigit()}
        for run in TrainRunModel.objects(status='running', worker=worker.name):
            if run.delete_requested:
                shutil.rmtree(work_dir(run.id), ignore_errors=True)
                run.delete()
            elif run.id in kept and (run.epoch or 0) < (run.epochs or 0):
                run.update(set__has_last=True)
                queue_resume(run)
            else:
                run.update(set__status='failed', set__error='the trainer restarted during this training',
                           set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        return {'name': worker.name}


@api.route('/heartbeat')
class WorkerHeartbeat(Resource):

    def post(self):
        worker = _worker()
        if worker is None:
            return _denied()
        data = request.get_json(silent=True) or {}
        run_id = data.get('run_id')
        heartbeat(name=worker.name, kind='remote', run_id=int(run_id) if run_id else None,
                  gpu=_gpu(data))
        return {}


@api.route('/claim')
class WorkerClaim(Resource):

    def post(self):
        """ The next training for this worker (204: none) """
        worker = _worker()
        if worker is None:
            return _denied()
        gpu = _gpu(request.get_json(silent=True) or {})
        if gpu and gpu.get('busy'):
            # an older worker does not hold back by itself
            heartbeat(name=worker.name, kind='remote', run_id=None, gpu=gpu)
            return '', 204
        run = claim_next(worker.name)
        if run is None:
            heartbeat(name=worker.name, kind='remote', run_id=None, gpu=gpu)
            return '', 204
        heartbeat(name=worker.name, kind='remote', run_id=run.id, gpu=gpu)
        work = work_dir(run.id)
        os.makedirs(work, exist_ok=True)
        if (run.params or {}).get('resume'):
            # the cut-off epoch is trained again: its points go
            _trim_steps(os.path.join(work, 'steps.jsonl'), run.epoch or 0)
        else:
            for old in ('steps.jsonl', 'progress.txt', 'results.zip'):
                if os.path.exists(os.path.join(work, old)):
                    os.remove(os.path.join(work, old))
        return job(run)


@api.route('/runs/<int:run_id>/export')
class WorkerExport(Resource):

    def get(self, run_id):
        """ The export (zip) a training uses """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        export = ExportModel.objects(id=run.export_id).first() if run else None
        if export is None or not export.path or not os.path.isfile(export.path):
            return {'message': 'the export file no longer exists'}, 404
        return send_file(export.path, as_attachment=True, download_name=f'export-{export.id}.zip')


@api.route('/runs/<int:run_id>/files/<int:index>')
class WorkerFile(Resource):

    def get(self, run_id, index):
        """ A model file of this server the training uses """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        files = _files(run) if run else []
        if index >= len(files):
            return {'message': 'Unknown file'}, 404
        return send_file(files[index]['path'], as_attachment=True, download_name=files[index]['name'])


def _append(path, lines):
    if lines:
        with open(path, 'a', encoding='utf-8') as fp:
            fp.write(''.join(str(line).replace('\n', ' ') + '\n' for line in lines[:MAX_LINES]))


@api.route('/runs/<int:run_id>/progress')
class WorkerProgress(Resource):

    def post(self, run_id):
        """ While training: new output lines, the progress bar, batch points,
        the epochs so far. Answers whether to stop (or remove) it. """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        if run is None:
            return {'stop': True, 'delete': True}
        if run.status != 'running':  # stopped here meanwhile (the worker was unreachable)
            return {'stop': True, 'delete': False}
        data = request.get_json(silent=True) or {}
        work = work_dir(run.id)
        os.makedirs(work, exist_ok=True)
        _append(os.path.join(work, 'train.log'), data.get('lines') or [])
        steps = [json.dumps(p) for p in (data.get('steps') or [])[:MAX_LINES] if isinstance(p, dict)]
        _append(os.path.join(work, 'steps.jsonl'), steps)
        if 'progress' in data:
            tmp = os.path.join(work, 'progress.txt.tmp')
            with open(tmp, 'w', encoding='utf-8') as fp:
                fp.write(str(data.get('progress') or '')[:2000])
            os.replace(tmp, os.path.join(work, 'progress.txt'))
        update = {}
        if isinstance(data.get('metrics'), list):
            update['set__metrics'] = [r for r in data['metrics'] if isinstance(r, dict)]
            update['set__epoch'] = len(update['set__metrics'])
        if isinstance(data.get('log_tail'), str):
            update['set__log_tail'] = data['log_tail'][-6000:]
        if update:
            run.update(**update)
        heartbeat(name=worker.name, kind='remote', run_id=run.id)
        run.reload('stop_requested', 'delete_requested')
        return {'stop': bool(run.stop_requested), 'delete': bool(run.delete_requested)}


@api.route('/runs/<int:run_id>/fail')
class WorkerFail(Resource):

    def post(self, run_id):
        """ It could not start (data, files) """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        if run is not None:
            error = str((request.get_json(silent=True) or {}).get('error') or 'failed')[:1000]
            run.update(set__status='failed', set__error=error, set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        heartbeat(name=worker.name, kind='remote', run_id=None)
        return {}


UPLOADS = ('best', 'archive')
MAX_PART = 64 * 1024 * 1024


def _upload_path(run_id, name):
    return os.path.join(work_dir(run_id), f'{name}.upload')


@api.route('/runs/<int:run_id>/part')
class WorkerPart(Resource):

    def post(self, run_id):
        """ A piece of a result file (?file=best|archive&offset=N, the bytes
        as the body): sent in pieces, so a proxy's upload limit does not
        matter. Answers how much has arrived. """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        name = request.args.get('file')
        if run is None or name not in UPLOADS:
            return {'message': 'Unknown run or file'}, 404
        try:
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return {'message': 'offset'}, 400
        data = request.get_data(cache=False)
        if len(data) > MAX_PART:
            return {'message': 'piece too large'}, 413
        path = _upload_path(run.id, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        if offset == 0:
            size = 0
            open(path, 'wb').close()
        if offset != size:  # a piece missing or sent twice: say where to go on
            return {'size': size, 'resend': True}
        with open(path, 'ab') as fp:
            fp.write(data)
        heartbeat(name=worker.name, kind='remote', run_id=run.id)
        return {'size': size + len(data)}


@api.route('/runs/<int:run_id>/finish')
class WorkerFinish(Resource):

    def post(self, run_id):
        """ The end: status and epochs (form field "data", JSON), the trained
        weights (file "best") and the results zip (file "archive") """
        worker = _worker()
        if worker is None:
            return _denied()
        run = _run_of(worker, run_id)
        heartbeat(name=worker.name, kind='remote', run_id=None)
        if run is None:
            return {'deleted': True}
        work = work_dir(run.id)
        if run.delete_requested:
            shutil.rmtree(work, ignore_errors=True)
            run.delete()
            return {'deleted': True}
        if run.status != 'running':  # ended here meanwhile
            return {'status': run.status, 'ignored': True}
        try:
            data = json.loads(request.form.get('data') or '{}')
        except ValueError:
            data = {}
        rows = [r for r in data.get('metrics') or [] if isinstance(r, dict)]
        status = data.get('status') if data.get('status') in ('done', 'stopped', 'failed') else 'failed'
        # the files: sent before in pieces (data "uploaded": {name: size}),
        # or with this request
        uploaded = data.get('uploaded') if isinstance(data.get('uploaded'), dict) else {}

        def received(name):
            path = _upload_path(run.id, name)
            if name in uploaded and os.path.isfile(path) and os.path.getsize(path) == uploaded[name]:
                return path
            return None

        model_name = None
        best, best_part = request.files.get('best'), received('best')
        if (best is not None or best_part) and rows:
            name = f"{safe_name('+'.join(run.dataset_names or ['model']))}-{run.task}-run{run.id}.pt"
            target = os.path.join(models_dir(), 'trained')
            os.makedirs(target, exist_ok=True)
            if best_part:
                shutil.move(best_part, os.path.join(target, name))
            else:
                best.save(os.path.join(target, name))
            model_name = f'trained/{name}'
        if status == 'done' and not model_name:
            status = 'failed'
        archive, archive_part = request.files.get('archive'), received('archive')
        if archive_part:
            os.replace(archive_part, archive_path(run.id))
        elif archive is not None:
            os.makedirs(work, exist_ok=True)
            tmp = archive_path(run.id) + '.part'
            archive.save(tmp)
            os.replace(tmp, archive_path(run.id))
        for name in UPLOADS:  # pieces not used
            if os.path.exists(_upload_path(run.id, name)):
                os.remove(_upload_path(run.id, name))
        progress = os.path.join(work, 'progress.txt')
        if os.path.exists(progress):
            os.remove(progress)
        run.update(set__status=status, set__metrics=rows, set__epoch=len(rows),
                   set__log_tail=str(data.get('log_tail') or '')[-6000:],
                   set__error=str(data.get('error') or '')[:1000], set__model_name=model_name,
                   set__has_last=bool(data.get('has_last')), set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        return {'status': status, 'model_name': model_name}


# ---- managing the workers (admins) ------------------------------------------

def _admin():
    return current_user.is_authenticated and current_user.is_admin


@api.route('/servers')
class WorkerServers(Resource):

    @login_required
    def get(self):
        """ The other servers allowed to train """
        if not _admin():
            return {'message': 'Admins only'}, 403
        return {'workers': [{'name': w.name, 'created_by': w.created_by, 'last_ip': w.last_ip,
                             'created_at': w.created_at.isoformat() + 'Z' if w.created_at else None}
                            for w in TrainWorkerModel.objects.order_by('name')]}

    @login_required
    def post(self):
        """ Allow another server to train: its name; answers its token (shown once) """
        if not _admin():
            return {'message': 'Admins only'}, 403
        name = str((request.get_json(silent=True) or {}).get('name') or '').strip()
        if not NAME.match(name):
            return {'message': 'A name of letters, digits, - _ . (up to 40)'}, 400
        local = TrainerStatusModel.objects(key=name).first()
        if TrainWorkerModel.objects(name=name).first() or (local and (local.kind or 'local') == 'local'):
            return {'message': f'{name} is taken'}, 400
        token = new_token()
        TrainWorkerModel(name=name, token_hash=token_hash(token), created_by=current_user.username).save()
        from ..util import activity
        activity.record('train', current_user, detail={'worker_added': name}, text=f"trainer {name}")
        return {'name': name, 'token': token}


@api.route('/servers/<name>')
class WorkerServer(Resource):

    @login_required
    def post(self, name):
        """ A new token (the old one stops working) """
        if not _admin():
            return {'message': 'Admins only'}, 403
        worker = TrainWorkerModel.objects(name=name).first()
        if worker is None:
            return {'message': 'Unknown trainer'}, 404
        token = new_token()
        worker.update(set__token_hash=token_hash(token))
        return {'name': name, 'token': token}

    @login_required
    def delete(self, name):
        """ Remove a server: it can no longer train; trainings waiting for it
        go to whichever trainer is free """
        if not _admin():
            return {'message': 'Admins only'}, 403
        worker = TrainWorkerModel.objects(name=name).first()
        if worker is None:
            return {'message': 'Unknown trainer'}, 404
        worker.delete()
        TrainerStatusModel.objects(key=name).delete()
        TrainRunModel.objects(status='queued', target=name).update(set__target='')
        from ..util import activity
        activity.record('train', current_user, detail={'worker_removed': name}, text=f"trainer {name}")
        return {'success': True}
