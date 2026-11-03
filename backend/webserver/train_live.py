"""A training's output, live: the page watching a run gets each new line
and the progress bar as the trainer writes them (shared models folder),
over its socket. Needs the "train" permission."""
import json
import os
import threading
import time

from flask import request
from flask_login import current_user

from database import TrainRunModel
from trainer.runner import work_dir
from .sockets import socketio, authenticated_only

INTERVAL = 0.1        # how often the files are looked at
STATUS_SECONDS = 2    # how often the run's status is checked
FIRST_BYTES = 64 * 1024
FIRST_LINES = 400

#: run id -> watcher
WATCHERS = {}
_LOCK = threading.Lock()


def room(run_id):
    return f"train:{run_id}"


class _Tail:
    """New whole lines of a file that only grows."""

    def __init__(self, path):
        self.path = path
        self.offset = None
        self.partial = b""

    def new_lines(self):
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return []
        if self.offset is None or size < self.offset:  # started again
            self.offset, self.partial = 0, b""
        if size == self.offset:
            return []
        with open(self.path, "rb") as fp:
            fp.seek(self.offset)
            data = fp.read(size - self.offset)
        self.offset = size
        data = self.partial + data
        *done, self.partial = data.split(b"\n")
        return [line.decode("utf-8", "replace") for line in done]


def read_steps(path):
    out = []
    try:
        with open(path, encoding="utf-8") as fp:
            for line in fp:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


class Watcher:
    """Follows one run's files while someone watches it (one thread per run,
    shared by every page watching it)."""

    def __init__(self, run_id):
        self.run_id = run_id
        self.sids = set()
        self.log_path = os.path.join(work_dir(run_id), "train.log")
        self.progress_path = os.path.join(work_dir(run_id), "progress.txt")
        self.offset = None
        self.partial = b""
        self.progress = None
        self.steps = _Tail(os.path.join(work_dir(run_id), "steps.jsonl"))

    def snapshot(self, end=None):
        """The end of the output so far (up to ``end``), and where to go on from."""
        lines, offset = [], 0
        try:
            with open(self.log_path, "rb") as fp:
                fp.seek(0, os.SEEK_END)
                offset = fp.tell() if end is None else min(end, fp.tell())
                fp.seek(max(0, offset - FIRST_BYTES))
                data = fp.read(offset - fp.tell())
            text = data.decode("utf-8", "replace")
            if offset > FIRST_BYTES:  # a cut first line
                text = text.split("\n", 1)[-1]
            lines = text.split("\n")
            if lines and lines[-1] == "":
                lines.pop()
        except OSError:
            pass
        return lines[-FIRST_LINES:], offset

    def read_progress(self):
        try:
            with open(self.progress_path, encoding="utf-8", errors="replace") as fp:
                return fp.read()
        except OSError:
            return ""

    def new_lines(self):
        try:
            size = os.path.getsize(self.log_path)
        except OSError:
            return []
        if self.offset is None or size < self.offset:  # started again
            self.offset, self.partial = 0, b""
        if size == self.offset:
            return []
        with open(self.log_path, "rb") as fp:
            fp.seek(self.offset)
            data = fp.read(size - self.offset)
        self.offset = size
        data = self.partial + data
        *done, self.partial = data.split(b"\n")
        return [line.decode("utf-8", "replace") for line in done]

    def run(self):
        last_status = 0
        running = True
        while True:
            with _LOCK:
                if not self.sids:
                    WATCHERS.pop(self.run_id, None)
                    return
            with _LOCK:
                lines = self.new_lines()
                steps = []
                for line in self.steps.new_lines():
                    try:
                        steps.append(json.loads(line))
                    except ValueError:
                        pass
            progress = self.read_progress() if running else ""
            if lines or steps or progress != self.progress:
                self.progress = progress
                socketio.emit('train_log', {'run_id': self.run_id, 'lines': lines, 'progress': progress,
                                            'steps': steps}, room=room(self.run_id))
            if time.monotonic() - last_status > STATUS_SECONDS:
                last_status = time.monotonic()
                run = TrainRunModel.objects(id=self.run_id).only('status').first()
                was_running = running
                running = run is not None and run.status in ('queued', 'running')
                if not running and not was_running:
                    # finished, and its last lines sent: nothing more will come
                    with _LOCK:
                        WATCHERS.pop(self.run_id, None)
                    return
            time.sleep(INTERVAL)


@socketio.on('train_watch')
@authenticated_only
def train_watch(data):
    """Follow a run's output: answers with its end so far, then 'train_log'
    events with each new line and the progress bar."""
    if not current_user.has_perm('train'):
        return {'ok': False}
    try:
        run_id = int((data or {}).get('run_id'))
    except (TypeError, ValueError):
        return {'ok': False}
    run = TrainRunModel.objects(id=run_id).first()
    from .api.train import run_visible
    if run is None or not run_visible(run):
        return {'ok': False}
    sid = request.sid
    _leave(sid)
    from flask_socketio import join_room
    join_room(room(run_id))
    with _LOCK:
        watcher = WATCHERS.get(run_id)
        start = watcher is None
        if start:
            watcher = WATCHERS[run_id] = Watcher(run_id)
        watcher.sids.add(sid)
        if start:
            lines, watcher.offset = watcher.snapshot()
            # points so far come from the API; new ones from here
            try:
                watcher.steps.offset = os.path.getsize(watcher.steps.path)
            except OSError:
                watcher.steps.offset = 0
        else:
            # up to where the running thread is: it sends what comes after
            lines, _ = watcher.snapshot((watcher.offset or 0) - len(watcher.partial))
    if start:
        socketio.start_background_task(watcher.run)
    return {'ok': True, 'lines': lines, 'progress': watcher.read_progress(),
            'live': run.status in ('queued', 'running')}


@socketio.on('train_unwatch')
@authenticated_only
def train_unwatch(data=None):
    _leave(request.sid)
    return True


def _leave(sid):
    from flask_socketio import leave_room
    with _LOCK:
        for run_id, watcher in list(WATCHERS.items()):
            if sid in watcher.sids:
                watcher.sids.discard(sid)
                try:
                    leave_room(room(run_id), sid=sid)
                except Exception:
                    pass


def close_for(sid):
    """The page went away."""
    with _LOCK:
        for watcher in WATCHERS.values():
            watcher.sids.discard(sid)
