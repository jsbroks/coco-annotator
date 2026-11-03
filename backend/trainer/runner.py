"""Runs queued trainings one at a time: unpack the YOLO export, run
Ultralytics in a child process, follow results.csv, keep the best weights
in the models folder (where pre-annotation finds them)."""
import codecs
import collections
import csv
import datetime
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile



def _db():
    """The site's database models: imported only where used, so a worker on
    another server (trainer/worker.py) needs neither them nor their packages."""
    import database
    return database

logger = logging.getLogger("trainer")

POLL_SECONDS = 3
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
LOG_TAIL_CHARS = 6000
# how often the page's view of the output is refreshed while training
LOG_SECONDS = 1
# model name suffix of each task (yolo26s-seg.pt)
TASK_SUFFIX = {"detect": "", "segment": "-seg", "obb": "-obb", "pose": "-pose", "classify": "-cls"}


def trainer_name():
    """This trainer's name (several servers can train: each has its own)."""
    return (os.getenv("TRAINER_NAME") or "main").strip()[:40] or "main"


def models_dir():
    return os.getenv("MODELS_DIRECTORY", "/models")


def work_dir(run_id):
    # hidden: the models page lists every .pt it finds, not these
    return os.path.join(models_dir(), ".training", f"run-{run_id}")


def safe_name(text):
    return re.sub(r"[^\w.-]+", "_", str(text or "")).strip("_.")[:80] or "model"


def _unpack(export, dest, task):
    """Unzip the export; returns what Ultralytics' ``data=`` takes."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    with zipfile.ZipFile(export.path) as zf:
        for member in zf.namelist():
            target = os.path.realpath(os.path.join(dest, member))
            if not target.startswith(os.path.realpath(dest) + os.sep):
                raise ValueError(f"unsafe path in the export: {member}")
        zf.extractall(dest)
    if task == "classify":
        folder = getattr(export, "folder", None)
        candidates = [os.path.join(dest, folder)] if folder else []
        candidates += [os.path.join(dest, d) for d in sorted(os.listdir(dest)) if os.path.isdir(os.path.join(dest, d))]
        for c in candidates:
            if os.path.isdir(os.path.join(c, "train")):
                return c
        raise ValueError("no train/ folder in the export")
    data = os.path.join(dest, "data.yaml")
    if not os.path.isfile(data):
        raise ValueError("no data.yaml in the export (is it a YOLO export?)")
    return data


def uploads_dir():
    return os.path.join(models_dir(), ".training", "uploads")


def _weights(name):
    """Official .pt weights by name: downloaded once into a hidden folder and
    kept for the next runs. Anything else (a path, a .yaml) as it is."""
    if not name.endswith(".pt") or os.sep in name or "/" in name:
        return name
    base = os.path.join(models_dir(), ".training", "base")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, name)


def _value(v):
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v)


def last_weights(run_id):
    return os.path.join(work_dir(run_id), "runs", "train", "weights", "last.pt")


def _trim_steps(path, epochs_done):
    """Points of the epoch that was cut off go: it is trained again."""
    if not os.path.isfile(path):
        return
    keep = []
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            try:
                if json.loads(line).get("x", 0) <= epochs_done:
                    keep.append(line)
            except ValueError:
                pass
    with open(path, "w", encoding="utf-8") as fp:
        fp.writelines(keep)


def resumable(run):
    """Can go on from where it stopped: the last epoch's weights are there
    and it did not reach its epochs."""
    if run.status not in ("failed", "stopped") or (run.epoch or 0) >= (run.epochs or 0):
        return False
    if getattr(run, "has_last", False):  # kept on the (remote) trainer that ran it
        return True
    return os.path.isfile(last_weights(run.id))


def build_command(run, data, out_dir):
    """The Ultralytics command line (replaced in tests)."""
    p = run.params or {}
    if p.get("resume"):
        # on from the last finished epoch: Ultralytics takes everything else
        # (arguments, data, where it writes) from the checkpoint
        return [sys.executable, "-c", "from ultralytics.cfg import entrypoint; entrypoint()",
                run.task or "detect", "train", f"model={last_weights(run.id)}",
                f"resume={last_weights(run.id)}"]
    args = [
        f"model={_weights(p.get('model') or '')}", f"data={data}", f"epochs={int(p.get('epochs', 100))}",
        f"imgsz={int(p.get('imgsz', 640))}", f"batch={p.get('batch', -1)}",
        f"patience={int(p.get('patience', 50))}", "plots=True",
    ]
    if p.get("device"):
        args.append(f"device={p['device']}")
    # the page's own arguments (checked by the API); "pretrained" may name
    # official weights to start a .yaml architecture from
    for key, value in (p.get("extra") or {}).items():
        if key == "pretrained" and isinstance(value, str) and value.endswith(".pt"):
            value = _weights(value)
        args.append(f"{key}={_value(value)}")
    # where the results go: last, so nothing overrides it
    args += [f"project={out_dir}", "name=train", "exist_ok=True"]
    # the "yolo" command line (it reads sys.argv)
    return [sys.executable, "-c", "from ultralytics.cfg import entrypoint; entrypoint()",
            run.task or "detect", "train", *args]


def _read_results(path):
    """results.csv rows with numbers, header names without spaces."""
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, newline="") as fp:
        for row in csv.DictReader(fp):
            clean = {}
            for k, v in row.items():
                if k is None:
                    continue
                try:
                    clean[k.strip()] = round(float(v), 5)
                except (TypeError, ValueError):
                    pass
            if clean:
                rows.append(clean)
    return rows


_BAR_HEAD = re.compile(r"^\s*Epoch\s+GPU_mem\s+(.*?)\s+Instances\s+Size\s*$")
_BAR = re.compile(r"^\s*(\d+)/(\d+)\s+([\d.]+)([KMGT]?)B?\s+(.*?):\s*(\d+)%.*?\s(\d+)/(\d+)")
STEP_SECONDS = 0.2


def parse_step(text, losses):
    """A training progress bar line ("  3/100  2.1G  1.23  0.98 ...  640: 45% ━━ 9/20")
    as a point: x = epochs done (2.45), the losses so far in this epoch, GPU
    memory (GB). None for other lines (validation bars, …)."""
    m = _BAR.match(text)
    if not m or not losses:
        return None
    epoch, _, mem, unit, rest, _, batch, batches = m.groups()
    values = rest.split()
    if len(values) != len(losses) + 2:  # + instances, size
        return None
    try:
        point = {k: float(v) for k, v in zip(losses, values)}
        batch, batches = int(batch), int(batches)
    except ValueError:
        return None
    point["x"] = round(int(epoch) - 1 + (batch / batches if batches else 0), 4)
    point["gpu_mem"] = round(float(mem) * {"K": 1e-6, "M": 1e-3, "G": 1, "T": 1e3}.get(unit, 1), 3)
    return point


class LogFollower:
    """Reads the training's output as it comes. Progress bars rewrite their
    line with \r ten times a second: only the line's last state is kept, so
    the log stays small and its end always has the lines before the bar
    (reading the end of the raw output would be one huge bar line)."""

    def __init__(self, log_file, progress_path=None, steps_path=None):
        self.log = log_file
        # each state of the training progress bar: the losses within an
        # epoch (results.csv only has one value per epoch)
        self.steps_path = steps_path
        self.losses = []
        self._last_step = None
        self._last_step_at = 0
        # the progress bar's state, for the page to follow live (the log
        # file only gets finished lines)
        self.progress_path = progress_path
        self._shown_progress = None
        self.lines = collections.deque(maxlen=400)
        self.current = ""
        self.version = 0
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._lock = threading.Lock()

    def feed(self, data):
        text = self._decoder.decode(data, final=not data).replace("\r\n", "\n")
        with self._lock:
            text = self.current + text
            *done, self.current = text.split("\n")
            for line in done:
                line = ANSI.sub("", line).split("\r")[-1].rstrip()
                self.lines.append(line)
                self.log.write((line + "\n").encode())
                self._step(line, final=True)
            if done:
                self.log.flush()
            # keep only the bar's last state (escape codes may be cut: strip at the end)
            if "\r" in self.current:
                parts = self.current.split("\r")
                last = parts[-1] or (parts[-2] if len(parts) > 1 else "")
                self.current = last if parts[-1] else last + "\r"
            self.version += 1
            self._write_progress()

    def _step(self, text, final=False):
        if not self.steps_path:
            return
        head = _BAR_HEAD.match(text)
        if head:
            self.losses = head.group(1).split()
            return
        point = parse_step(text, self.losses)
        if point is None:
            return
        now = time.monotonic()
        # a point when the bar moved, at most five a second (the epoch's end always)
        last = self._last_step or {}
        if point == last or (not final and (point["x"] == last.get("x") or now - self._last_step_at < STEP_SECONDS)):
            return
        self._last_step, self._last_step_at = point, now
        try:
            with open(self.steps_path, "a", encoding="utf-8") as fp:
                fp.write(json.dumps(point) + "\n")
        except OSError:
            pass

    def _write_progress(self):
        if not self.progress_path:
            return
        text = ANSI.sub("", self.current).strip("\r").rstrip()
        self._step(text)
        if text == self._shown_progress:
            return
        self._shown_progress = text
        try:
            tmp = self.progress_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(text)
            os.replace(tmp, self.progress_path)
        except OSError:
            pass

    def follow(self, stream):
        fd = stream.fileno()
        while True:
            chunk = os.read(fd, 65536)
            self.feed(chunk)
            if not chunk:
                break
        with self._lock:
            if self.current.strip("\r"):
                line = ANSI.sub("", self.current).strip("\r").rstrip()
                self.lines.append(line)
                self.log.write((line + "\n").encode())
                self.log.flush()
            self.current = ""
            self._write_progress()

    def tail(self):
        with self._lock:
            current = ANSI.sub("", self.current).strip("\r")
            text = "\n".join(list(self.lines) + ([current] if current else []))
        return text[-LOG_TAIL_CHARS:]


def heartbeat(device=None, catalog=None, name=None, kind="local", run_id=False, gpu=False):
    """This trainer is alive (and what it is training: run_id, None = free;
    what its GPU is doing: gpu, None = unknown)."""
    update = {"set__seen_at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), "set__kind": kind}
    if gpu is not False:
        update["set__gpu"] = gpu
    if device is not None:
        update["set__device"] = device
    if catalog is not None:
        update["set__catalog"] = catalog
        update["set__version"] = catalog.get("version") or ""
    if run_id is not False:
        update["set__run_id"] = run_id
    _db().TrainerStatusModel.objects(key=name or trainer_name()).update_one(upsert=True, **update)


class LocalIO:
    """How a training talks to the site when the trainer reads the database
    itself (this server). A worker on another server has its own (worker.py)."""

    def __init__(self, run):
        self.run = run
        self.export = _db().ExportModel.objects(id=run.export_id).first()
        self._polled = 0
        self._shown = -1

    def _export_file(self):
        e = self.export
        return e if e is not None and e.path and os.path.isfile(e.path) else None

    def prepare(self, work, resume):
        """Unpack the export; the data path (None: already unpacked)."""
        if resume and os.path.isdir(os.path.join(work, "data")):
            return None
        export = self._export_file()
        if export is None:
            raise ValueError("the unpacked data and the export are both gone" if resume
                             else "the export file no longer exists")
        return _unpack(export, os.path.join(work, "data"), self.run.task)

    def fail(self, error):
        self.run.update(set__status="failed", set__error=error[:1000], set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    def poll(self, rows, out, force=False):
        """Every second while training: the output, and every few seconds the
        epochs done; True when it is to be stopped."""
        run = self.run
        if force or time.monotonic() - self._polled >= POLL_SECONDS:
            self._polled = time.monotonic()
            r = rows()
            run.reload("stop_requested")
            run.update(set__metrics=r, set__epoch=len(r))
            heartbeat()
        if out.version != self._shown:
            self._shown = out.version
            run.update(set__log_tail=out.tail())
        return bool(run.stop_requested)

    def removed(self):
        self.run.reload("delete_requested")
        if self.run.delete_requested:  # removed while it ran: nothing kept
            shutil.rmtree(work_dir(self.run.id), ignore_errors=True)
            self.run.delete()
            return True
        return False

    def finish(self, status, rows, log_tail, error, best, has_last):
        run = self.run
        model_name = None
        if best:
            names = run.dataset_names or ["model"]
            name = f"{safe_name('+'.join(names))}-{run.task}-run{run.id}.pt"
            target_dir = os.path.join(models_dir(), "trained")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(best, os.path.join(target_dir, name))
            model_name = f"trained/{name}"
        if status == "done" and not model_name:
            status = "failed"
        try:
            package(run)
        except Exception as e:  # the run is still done; the page can pack it later
            logger.warning("could not pack run %s: %s", run.id, e)
        run.update(set__status=status, set__metrics=rows, set__epoch=len(rows), set__log_tail=log_tail,
                   set__model_name=model_name, set__error=error, set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                   set__has_last=False)


def execute(run, command=None, io=None):
    """Train one run to the end (or until stopped). ``io``: how it reports
    to the site (LocalIO here; a worker on another server has its own)."""
    io = io or LocalIO(run)
    work = work_dir(run.id)
    log_path = os.path.join(work, "train.log")
    resume = bool((run.params or {}).get("resume"))
    out_dir = os.path.join(work, "runs")
    try:
        os.makedirs(work, exist_ok=True)
        if resume:
            if not os.path.isfile(last_weights(run.id)):
                raise ValueError("no weights of a finished epoch to resume from")
            # the data as it was unpacked (the export may be gone since)
            _trim_steps(os.path.join(work, "steps.jsonl"), run.epoch or 0)
            data = io.prepare(work, True)
        else:
            data = io.prepare(work, False)
            # nothing left from an earlier run with this number
            shutil.rmtree(out_dir, ignore_errors=True)
            for old in ("steps.jsonl", "progress.txt", "results.zip"):
                if os.path.exists(os.path.join(work, old)):
                    os.remove(os.path.join(work, old))
        cmd = (command or build_command)(run, data, out_dir)
    except Exception as e:  # nothing started: say why
        io.fail(str(e))
        return
    results = os.path.join(out_dir, "train", "results.csv")
    # online: Ultralytics downloads the base weights the first time
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    env.pop("YOLO_OFFLINE", None)
    if resume and os.path.exists(archive_path(run.id)):
        os.remove(archive_path(run.id))  # packed again at the end
    with open(log_path, "ab") as log:
        log.write(("$ " + " ".join(cmd) + "\n").encode())
        log.flush()
        out = LogFollower(log, os.path.join(work, "progress.txt"), os.path.join(work, "steps.jsonl"))
        if resume:
            out.feed(f"--- resumed after epoch {run.epoch} ---\n".encode())
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=work, env=env,
                                start_new_session=True)
        reader = threading.Thread(target=out.follow, args=(proc.stdout,), daemon=True)
        reader.start()
        stopped = False
        while True:
            code = proc.poll()
            stop = io.poll(lambda: _read_results(results), out, force=code is not None)
            if code is not None:
                break
            if stop and not stopped:
                stopped = True
                # the whole process group (data loader workers too)
                os.killpg(proc.pid, signal.SIGINT)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
            # how often it reports: a remote trainer more often (its output
            # reaches the page only this way)
            time.sleep(getattr(io, "tick", min(LOG_SECONDS, POLL_SECONDS)))
        reader.join(timeout=10)
        proc.stdout.close()
        log_tail = out.tail()
    if io.removed():
        return
    rows = _read_results(results)
    best = os.path.join(out_dir, "train", "weights", "best.pt")
    best = best if os.path.isfile(best) and rows else None
    status = "stopped" if stopped else ("done" if code == 0 and best else "failed")
    error = ""
    if status == "failed":
        tail = log_tail.strip().splitlines()
        error = (tail[-1] if tail else f"exit code {code}")[:1000]
    has_last = os.path.isfile(last_weights(run.id)) and len(rows) < (run.epochs or 0)
    io.finish(status, rows, log_tail, error, best, has_last)


# already compressed: stored as they are (faster, no bigger)
_STORED = (".pt", ".jpg", ".jpeg", ".png", ".zip", ".onnx", ".engine")


def archive_path(run_id):
    return os.path.join(work_dir(run_id), "results.zip")


def package(run, log_path=None):
    """Everything Ultralytics wrote (runs/train: weights, results.csv,
    args.yaml, plots) and the output, as one zip next to the run. Returns
    its path, or None when there is nothing to pack."""
    train = os.path.join(work_dir(run.id), "runs", "train")
    if not os.path.isdir(train):
        return None
    log_path = log_path or os.path.join(work_dir(run.id), "train.log")
    target = archive_path(run.id)
    tmp = target + ".part"
    top = f"{safe_name('+'.join(run.dataset_names or ['train']))}-{run.task}-run{run.id}"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, _, files in os.walk(train):
            for f in sorted(files):
                path = os.path.join(folder, f)
                arc = os.path.join(top, os.path.relpath(path, train))
                kind = zipfile.ZIP_STORED if f.lower().endswith(_STORED) else zipfile.ZIP_DEFLATED
                zf.write(path, arc, compress_type=kind)
        if os.path.isfile(log_path):
            zf.write(log_path, os.path.join(top, "train.log"))
    os.replace(tmp, target)
    return target


def claim_next(worker=None):
    """The oldest queued run this trainer may take (meant for it, or for any
    trainer), now running on it; None when there is none."""
    from mongoengine.queryset.visitor import Q
    worker = worker or trainer_name()
    for first in _db().TrainRunModel.objects(Q(status="queued") & (Q(target__in=["", None]) | Q(target=worker))
                                       ).order_by("id").only("id")[:5]:
        claimed = _db().TrainRunModel.objects(id=first.id, status="queued").update_one(
            set__status="running", set__started_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), set__worker=worker)
        if claimed:
            return _db().TrainRunModel.objects(id=first.id).first()
    return None


def _device_name():
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return "ultralytics not installed (build with SAM=cuda or SAM=cpu)"
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
        return "CPU"
    except Exception:
        return "CPU"


def queue_resume(run, reason=""):
    """Queue a run again, to go on from its last finished epoch."""
    params = dict(run.params or {})
    params["resume"] = True
    params["resumes"] = int(params.get("resumes") or 0) + 1
    # its last epoch's weights are on the server that trained it
    return _db().TrainRunModel.objects(id=run.id, status__in=["running", "failed", "stopped"]).update_one(
        set__status="queued", set__params=params, set__stop_requested=False, set__error=reason,
        set__ended_at=None, set__target=run.worker or "")


def recover():
    """Runs left "running" when the trainer stopped (server restarted, power
    cut…): queued again to go on from their last finished epoch, else failed."""
    from mongoengine.queryset.visitor import Q
    me = trainer_name()
    for run in _db().TrainRunModel.objects(Q(status="running") & (Q(worker=me) | Q(worker__in=["", None]))):
        if run.delete_requested:
            shutil.rmtree(work_dir(run.id), ignore_errors=True)
            run.delete()
        elif os.path.isfile(last_weights(run.id)) and (run.epoch or 0) < (run.epochs or 0):
            queue_resume(run, "")
            logger.info("run %s resumes after epoch %s", run.id, run.epoch)
        else:
            run.update(set__status="failed", set__error="the trainer restarted during this training",
                       set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def serve():
    """Run queued trainings, forever."""
    recover()
    device = _device_name()
    from .catalog import build
    heartbeat(device, build())
    logger.info("trainer ready (%s)", device)
    # the name used before trainers had names
    if trainer_name() != "trainer":
        _db().TrainerStatusModel.objects(key="trainer").delete()
    from .gpu import Monitor
    monitor = Monitor()
    while True:
        gpu = monitor.sample()
        heartbeat(device, run_id=None, gpu=gpu)
        if gpu and gpu.get("busy"):
            # used outside this site (a training started by hand, ...): wait
            time.sleep(POLL_SECONDS)
            continue
        run = claim_next()
        if run is None:
            time.sleep(POLL_SECONDS)
            continue
        logger.info("training run %s", run.id)
        heartbeat(device, run_id=run.id, gpu=None)
        try:
            execute(run)
        except Exception as e:  # pragma: no cover - keep serving the queue
            logger.exception("run %s", run.id)
            run.update(set__status="failed", set__error=str(e)[:1000], set__ended_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def start_embedded():
    """TRAINER_EMBEDDED=true: train inside the webserver process (no
    separate trainer container)."""
    import threading
    thread = threading.Thread(target=serve, name="trainer", daemon=True)
    thread.start()
    return thread


def main():
    logging.basicConfig(level=logging.INFO)
    from database import connect_mongo
    connect_mongo("trainer")
    serve()
