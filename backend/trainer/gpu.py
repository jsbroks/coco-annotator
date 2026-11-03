"""What a trainer's GPU is doing, so a queued training is not started on a GPU
someone is using outside this site (a training run by hand on that computer,
a game, another program).

Read with nvidia-smi (in the trainer's container with the NVIDIA runtime).
While the trainer itself trains nothing, a GPU is "used by others" when its
memory in use is over GPU_BUSY_MEMORY_MB (the desktop alone takes a few
hundred MB), or it has been busier than GPU_BUSY_UTIL % for a few readings in
a row. Without nvidia-smi nothing is known and nothing is held back."""
import os
import shutil
import subprocess
import time

# readings in a row over the utilisation limit before it counts (a short
# spike, e.g. a video decoded, does not)
UTIL_READINGS = 3


def _int(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def enabled():
    """GPU_BUSY_CHECK=false: the GPU is still shown, but never held back."""
    return os.getenv("GPU_BUSY_CHECK", "true").strip().lower() not in ("0", "false", "no", "off")


def busy_memory_mb():
    return _int(os.getenv("GPU_BUSY_MEMORY_MB"), 2048)


def busy_util():
    return _int(os.getenv("GPU_BUSY_UTIL"), 50)


def _smi(*args):
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def read():
    """The first GPU now: {name, util, mem_used, mem_total, procs} (MB, %),
    or None when it cannot be read."""
    rows = _smi("--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits")
    if not rows:
        return None
    parts = [p.strip() for p in rows[0].split(",")]
    if len(parts) < 4:
        return None
    gpu = {"name": parts[0], "util": _int(parts[1], 0), "mem_used": _int(parts[2], 0),
           "mem_total": _int(parts[3], 0), "procs": []}
    # the programs on it (in a container these may not be visible: memory and
    # utilisation are still the whole GPU's)
    for line in _smi("--query-compute-apps=pid,process_name,used_memory",
                     "--format=csv,noheader,nounits") or []:
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 3:
            gpu["procs"].append({"pid": _int(p[0], 0), "name": os.path.basename(p[1])[:60],
                                 "mem": _int(p[2], 0)})
    return gpu


class Monitor:
    """Readings over time: whether the GPU is used by others."""

    def __init__(self, reader=read):
        self.reader = reader
        self._hot = 0
        self.last = None

    def sample(self, training=False):
        """The GPU now, with ``busy``: used by something else (only judged
        while this trainer trains nothing: its own training uses the GPU)."""
        gpu = self.reader()
        if gpu is None:
            self.last = None
            return None
        gpu = dict(gpu)
        if training:
            self._hot = 0
            gpu["busy"] = False
        else:
            self._hot = self._hot + 1 if gpu["util"] >= busy_util() else 0
            gpu["busy"] = enabled() and (gpu["mem_used"] >= busy_memory_mb() or self._hot >= UTIL_READINGS)
        gpu["at"] = time.time()
        self.last = gpu
        return gpu
