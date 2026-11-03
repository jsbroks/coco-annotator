"""A trainer on another server ("worker"): it trains with this server's GPU
for the site at TRAINER_URL, connecting with TRAINER_TOKEN (from the
training page → 訓練伺服器). It takes trainings meant for it or for any
trainer, downloads the export, trains, and sends back the output, curves,
the trained model and the results zip. Nothing here touches the site's
database.

    python -m trainer.worker        (docker-compose.worker.yml runs it)
"""
import json
import logging
import os
import shutil
import threading
import time
from types import SimpleNamespace

import requests

from . import runner
from .gpu import Monitor
from .runner import (POLL_SECONDS, _unpack, archive_path, execute, last_weights, package, work_dir)

logger = logging.getLogger("trainer.worker")

RETRY_SECONDS = 10
# results go back in pieces of this size (a proxy may refuse large uploads)
PART_BYTES = 8 * 1024 * 1024
# exports kept here, so training on one again needs no new download
CACHE_GB = float(os.getenv("WORKER_CACHE_GB", "30"))
HEARTBEAT_SECONDS = 10


class Stopped(Exception):
    """Stopped from the site before the training began."""


class Site:
    """The site's worker API (/api/worker)."""

    def __init__(self, url, token):
        self.url = url.rstrip("/") + "/api/worker"
        self.http = requests.Session()
        self.http.headers["X-Worker-Token"] = token

    def post(self, path, json_body=None, timeout=30, **kw):
        r = self.http.post(f"{self.url}/{path}", json=json_body, timeout=timeout, **kw)
        if r.status_code == 401:
            raise PermissionError("the site does not know this token (removed, or a new one was made)")
        r.raise_for_status()
        return r.json() if r.status_code != 204 and r.content else None

    def download(self, path, dest, progress=None):
        """``progress(done, total)`` now and then; it returns True to give up."""
        tmp = dest + ".part"
        with self.http.get(f"{self.url}/{path}", stream=True, timeout=60) as r:
            if r.status_code == 404:
                raise ValueError((r.json() or {}).get("message") or "not found on the site")
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            done, told = 0, 0
            with open(tmp, "wb") as fp:
                for chunk in r.iter_content(1024 * 1024):
                    fp.write(chunk)
                    done += len(chunk)
                    if progress and time.monotonic() - told >= 1:
                        told = time.monotonic()
                        if progress(done, total):
                            raise Stopped()
            if progress:
                progress(done, total)
        os.replace(tmp, dest)
        return dest


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


class _Tail:
    """New whole lines of a file, from where the last read stopped."""

    def __init__(self, path):
        self.path = path
        self.offset = 0

    def start_at_end(self):
        self.offset = _size(self.path)

    def peek(self):
        size = _size(self.path)
        if size < self.offset:  # started again
            self.offset = 0
        if size == self.offset:
            return [], self.offset
        with open(self.path, "rb") as fp:
            fp.seek(self.offset)
            data = fp.read(size - self.offset)
        end = data.rfind(b"\n")
        if end < 0:
            return [], self.offset
        lines = data[:end].decode("utf-8", "replace").split("\n")
        return lines, self.offset + end + 1


class RemoteIO:
    """How a training on this server reports to the site (see runner.LocalIO)."""

    def __init__(self, site, job, run):
        self.site = site
        self.job = job
        self.run = run
        work = work_dir(run.id)
        self.log = _Tail(os.path.join(work, "train.log"))
        self.steps = _Tail(os.path.join(work, "steps.jsonl"))
        self.progress_path = os.path.join(work, "progress.txt")
        self._polled = 0
        self._sent_progress = None
        self.stop = False
        self.delete = False

    def _status(self, text, line=False):
        """Before the training: what it is doing (as the progress bar, or a
        line of the output); True when it is to be stopped."""
        body = {"lines": [text] if line else [], "progress": "" if line else text}
        try:
            answer = self.site.post(f"runs/{self.run.id}/progress", body) or {}
            self.stop = bool(answer.get("stop"))
            self.delete = bool(answer.get("delete"))
        except PermissionError:
            raise
        except Exception as e:
            logger.warning("run %s: could not reach the site: %s", self.run.id, e)
        return self.stop

    def _fetch(self, path, dest, what):
        def progress(done, total):
            mb = done / 1e6
            text = f"{what}: {mb:.0f} / {total / 1e6:.0f} MB" if total else f"{what}: {mb:.0f} MB"
            if total:
                text += f" ({100 * done / total:.0f}%)"
            return self._status(text)
        if self._status(f"{what}…", line=True):
            raise Stopped()
        self.site.download(path, dest, progress)

    def prepare(self, work, resume):
        # model files of the site (uploaded, from its Models page)
        # kept for the next runs (same name and size: the same file)
        folder = os.path.join(runner.models_dir(), ".cache", "files")
        os.makedirs(folder, exist_ok=True)
        for f in self.job.get("files") or []:
            dest = os.path.join(folder, os.path.basename(f["name"]))
            if not os.path.isfile(dest) or _size(dest) != f.get("size"):
                self._fetch(f"runs/{self.run.id}/files/{f['index']}", dest, f"Downloading {f['name']}")
            if f["field"] == "model":
                self.run.params["model"] = dest
            elif f["field"] == "pretrained":
                self.run.params.setdefault("extra", {})["pretrained"] = dest
        # from here on, what is written goes to the site
        self.log.start_at_end()
        self.steps.start_at_end()
        if resume and os.path.isdir(os.path.join(work, "data")):
            return None
        export = self.job.get("export") or {}
        if not export.get("available"):
            raise ValueError("the unpacked data and the export are both gone" if resume
                             else "the export file no longer exists")
        cached = _cached_export(export)
        if cached and os.path.isfile(cached):
            os.utime(cached)  # recently used
            self._status(f"Export #{export.get('id')} is already here", line=True)
        else:
            target = cached or os.path.join(work, "export.zip")
            self._fetch(f"runs/{self.run.id}/export", target, f"Downloading export #{export.get('id')}")
            cached = target
            _prune_cache(keep=cached)
        try:
            if self._status("Unpacking the export…", line=True):
                raise Stopped()
            data = _unpack(SimpleNamespace(path=cached, folder=export.get("folder")),
                           os.path.join(work, "data"), self.run.task)
            self._status("Starting the training…", line=True)
            return data
        finally:
            if not cached.startswith(_cache_dir()) and os.path.exists(cached):
                os.remove(cached)

    def fail(self, error):
        try:
            if self.stop or self.delete:  # stopped while getting the data
                self.site.post(f"runs/{self.run.id}/finish",
                               data={"data": json.dumps({"status": "stopped", "metrics": [], "log_tail": ""})})
                shutil.rmtree(work_dir(self.run.id), ignore_errors=True)
                return
            self.site.post(f"runs/{self.run.id}/fail", {"error": error[:1000]})
        except Exception as e:
            logger.warning("could not report run %s failed: %s", self.run.id, e)

    def _send(self, rows=None, out=None):
        lines, log_end = self.log.peek()
        steps, steps_end = self.steps.peek()
        body = {"lines": lines, "steps": []}
        for line in steps:
            try:
                body["steps"].append(json.loads(line))
            except ValueError:
                pass
        try:
            with open(self.progress_path, encoding="utf-8", errors="replace") as fp:
                progress = fp.read()
        except OSError:
            progress = ""
        if progress != self._sent_progress:
            body["progress"] = progress
        if rows is not None:
            body["metrics"] = rows
        if out is not None:
            body["log_tail"] = out.tail()
        answer = self.site.post(f"runs/{self.run.id}/progress", body) or {}
        # sent: go on from there
        self.log.offset, self.steps.offset = log_end, steps_end
        self._sent_progress = progress
        self.stop = bool(answer.get("stop"))
        self.delete = bool(answer.get("delete"))

    #: seconds between reports while training: the page follows the output
    #: almost as it is printed
    tick = 0.2

    def _changed(self):
        """Anything new to send (output lines, batch points, progress bar)?"""
        try:
            with open(self.progress_path, encoding="utf-8", errors="replace") as fp:
                progress = fp.read()
        except OSError:
            progress = ""
        return (progress != self._sent_progress or _size(self.log.path) != self.log.offset
                or _size(self.steps.path) != self.steps.offset)

    def poll(self, rows, out, force=False):
        full = force or time.monotonic() - self._polled >= POLL_SECONDS
        try:
            if full:
                self._polled = time.monotonic()
                self._send(rows(), out)
            elif self._changed():
                self._send()
        except Exception as e:  # the site is unreachable: keep training, send later
            logger.warning("run %s: could not reach the site: %s", self.run.id, e)
        return self.stop

    def removed(self):
        if not self.delete:
            return False
        try:
            self.site.post(f"runs/{self.run.id}/finish", data={"data": "{}"})
        except Exception:
            pass
        shutil.rmtree(work_dir(self.run.id), ignore_errors=True)
        return True

    def finish(self, status, rows, log_tail, error, best, has_last):
        try:  # the last lines
            self._send(rows, None)
        except Exception:
            pass
        try:
            package(self.run)
        except Exception as e:
            logger.warning("could not pack run %s: %s", self.run.id, e)
        archive = archive_path(self.run.id) if os.path.isfile(archive_path(self.run.id)) else None
        # the files in pieces (a proxy's upload limit does not matter), then the end
        uploaded = {}
        for name, path in (("best", best), ("archive", archive)):
            if path and self._upload(name, path):
                uploaded[name] = _size(path)
        data = json.dumps({"status": status, "metrics": rows, "log_tail": log_tail, "error": error,
                           "has_last": has_last, "uploaded": uploaded})
        sent = False
        for attempt in range(1, 7):
            try:
                self.site.post(f"runs/{self.run.id}/finish", data={"data": data}, timeout=120)
                sent = True
                break
            except PermissionError:
                raise
            except Exception as e:
                logger.warning("run %s: could not report the end (%s), try %s", self.run.id, e, attempt)
                time.sleep(RETRY_SECONDS * attempt)
        complete = (not best or "best" in uploaded) and (not archive or "archive" in uploaded)
        if sent and not complete:
            logger.warning("run %s: not everything was sent; it stays in %s", self.run.id, work_dir(self.run.id))
        # only what it needs to go on from where it stopped is kept here
        # (and all of it when the site did not get everything)
        if sent and complete and not has_last:
            shutil.rmtree(work_dir(self.run.id), ignore_errors=True)

    def _upload(self, name, path):
        """Send a file in pieces; True when all of it arrived."""
        total = _size(path)
        offset = 0
        failures = 0
        with open(path, "rb") as fp:
            while offset < total or total == 0:
                fp.seek(offset)
                piece = fp.read(PART_BYTES)
                try:
                    answer = self.site.post(f"runs/{self.run.id}/part?file={name}&offset={offset}",
                                            data=piece, timeout=300) or {}
                    offset = int(answer.get("size", offset))
                    failures = 0
                except PermissionError:
                    raise
                except Exception as e:
                    failures += 1
                    logger.warning("run %s: sending %s (%s), try %s", self.run.id, name, e, failures)
                    if failures > 8:
                        return False
                    time.sleep(RETRY_SECONDS * min(failures, 3))
                    continue
                if total == 0:
                    break
                self._status(f"Sending {name}.{'pt' if name == 'best' else 'zip'} to the site: "
                             f"{offset / 1e6:.0f} / {total / 1e6:.0f} MB ({100 * offset / total:.0f}%)")
        return True


def _cache_dir():
    return os.path.join(runner.models_dir(), ".cache", "exports")


def _cached_export(export):
    """Where an export is kept here (None: not kept, e.g. no size known)."""
    if not CACHE_GB or not export.get("size"):
        return None
    os.makedirs(_cache_dir(), exist_ok=True)
    return os.path.join(_cache_dir(), f"export-{export.get('id')}-{export['size']}-{export.get('mtime', 0)}.zip")


def _prune_cache(keep=None):
    """Oldest-used exports go when the kept ones pass WORKER_CACHE_GB."""
    folder = _cache_dir()
    if not os.path.isdir(folder):
        return
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".zip")]
    files.sort(key=lambda f: os.path.getatime(f) if os.path.exists(f) else 0)
    total = sum(_size(f) for f in files)
    for f in files:
        if total <= CACHE_GB * 1e9:
            break
        if f != keep:
            total -= _size(f)
            os.remove(f)


def _resumable_here():
    """Runs whose last finished epoch is on this server."""
    root = os.path.join(runner.models_dir(), ".training")
    out = []
    for name in os.listdir(root) if os.path.isdir(root) else []:
        if name.startswith("run-") and name[4:].isdigit() and os.path.isfile(last_weights(int(name[4:]))):
            out.append(int(name[4:]))
    return out


class _Beat:
    """Tells the site this worker is alive while it downloads or packs."""

    def __init__(self, site, monitor):
        self.site = site
        self.monitor = monitor
        self.run_id = None
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop.wait(HEARTBEAT_SECONDS):
            if self.run_id is None:
                continue  # the main loop reports while it waits for work
            try:
                gpu = self.monitor.sample(training=True)
                self.site.post("heartbeat", {"run_id": self.run_id, "gpu": gpu}, timeout=10)
            except Exception:
                pass


def serve(url, token):
    site = Site(url, token)
    device = runner._device_name()
    from .catalog import build
    catalog = build()
    while True:
        try:
            hello = site.post("hello", {"device": device, "catalog": catalog, "resumable": _resumable_here()})
            break
        except PermissionError:
            raise
        except Exception as e:
            logger.warning("cannot reach %s yet: %s", url, e)
            time.sleep(RETRY_SECONDS)
    logger.info("worker %s ready (%s) for %s", hello.get("name"), device, url)
    monitor = Monitor()
    beat = _Beat(site, monitor)
    while True:
        gpu = monitor.sample()
        if gpu and gpu.get("busy"):
            # used outside this site (e.g. a training run by hand here): no
            # queued training until it is free
            try:
                site.post("heartbeat", {"run_id": None, "gpu": gpu}, timeout=10)
            except PermissionError:
                raise
            except Exception as e:
                logger.warning("cannot reach %s: %s", url, e)
            time.sleep(POLL_SECONDS)
            continue
        try:
            job = site.post("claim", {"gpu": gpu})
        except PermissionError:
            raise
        except Exception as e:
            logger.warning("cannot reach %s: %s", url, e)
            time.sleep(RETRY_SECONDS)
            continue
        if not job:
            time.sleep(POLL_SECONDS)
            continue
        run = SimpleNamespace(id=job["id"], task=job["task"], params=dict(job.get("params") or {}),
                              epoch=job.get("epoch") or 0, epochs=job.get("epochs") or 0,
                              dataset_names=job.get("dataset_names") or [])
        logger.info("training run %s", run.id)
        beat.run_id = run.id
        try:
            execute(run, io=RemoteIO(site, job, run))
        except PermissionError:
            raise
        except Exception as e:  # pragma: no cover - keep serving
            logger.exception("run %s", run.id)
            RemoteIO(site, job, run).fail(str(e))
        beat.run_id = None


def main():
    logging.basicConfig(level=logging.INFO)
    url = os.getenv("TRAINER_URL", "").strip()
    token = os.getenv("TRAINER_TOKEN", "").strip()
    if not url or not token:
        raise SystemExit("Set TRAINER_URL (the site, e.g. http://192.168.1.10:5000) and TRAINER_TOKEN "
                         "(from the training page → 訓練伺服器)")
    os.environ.setdefault("MODELS_DIRECTORY", "/work")
    serve(url, token)


if __name__ == "__main__":
    main()
