import os
import subprocess


def get_tag():
    if os.getenv("VERSION"):
        return os.getenv("VERSION")
    try:
        result = subprocess.run(["git", "describe", "--abbrev=0", "--tags"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return result.stdout.decode("utf-8").strip()
    except OSError:
        return ""

def _get_bool(key, default_value):
    if key in os.environ:
        value = os.environ[key]
        if value == 'True' or value == 'true' or value == '1':
            return True
        return False
    return default_value

_DEFAULT_SECRET_KEYS = {"", "ChangeThisSecretKey", "<--- CHANGE THIS KEY --->"}


def _secret_key():
    """SECRET_KEY from the environment, or a random one kept on disk.

    The key signs login sessions: a well-known default would let anyone
    forge them. When none is set, one is generated once and stored next to
    the datasets (a persistent volume), so restarts keep people logged in.
    """
    key = os.getenv("SECRET_KEY", "").strip()
    if key not in _DEFAULT_SECRET_KEYS:
        return key
    path = os.path.join(os.getenv("DATASET_DIRECTORY", "/datasets/"), ".secret_key")
    try:
        with open(path) as f:
            key = f.read().strip()
        if key:
            return key
    except OSError:
        pass
    import secrets
    key = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(key)
        os.chmod(path, 0o600)
    except OSError:
        pass  # not persisted: sessions end when the server restarts
    return key


class Config:

    NAME = os.getenv("NAME", "COCO Annotator")
    VERSION = get_tag()

    ### File Watcher
    FILE_WATCHER = _get_bool("FILE_WATCHER", False)
    IGNORE_DIRECTORIES = ["_thumbnail", "_settings"]

    # Flask/Gunicorn
    #
    #   LOG_LEVEL - The granularity of log output
    #
    #       A string of "debug", "info", "warning", "error", "critical"
    #
    #   WORKER_CONNECTIONS - limits the maximum number of simultaneous
    #       clients that a single process can handle.
    #
    #       A positive integer generally set to around 1000.
    #
    #   WORKER_TIMEOUT - If a worker does not notify the master process
    #       in this number of seconds it is killed and a new worker is
    #       spawned to replace it.
    #
    SWAGGER_UI_JSONEDITOR = True
    DEBUG = os.getenv("DEBUG", 'false').lower() == 'true'
    PRELOAD = False

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 1 * 1024 * 1024 * 1024))  # 1GB
    # videos are sent in pieces, so they are not limited by MAX_CONTENT_LENGTH
    MAX_VIDEO_SIZE = int(os.getenv("MAX_VIDEO_SIZE", 20 * 1024 * 1024 * 1024))  # 20GB
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://database/flask")
    SECRET_KEY = _secret_key()

    LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
    # gunicorn threads; each open page holds one for its websocket
    WEB_THREADS = int(os.getenv("WEB_THREADS", 300))
    WORKER_CONNECTIONS = 1000

    TESTING = _get_bool("TESTING", False)

    ### Workers
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://user:password@messageq:5672//")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "mongodb://database/flask")
    CELERY_TASK_ALWAYS_EAGER = _get_bool("CELERY_TASK_ALWAYS_EAGER", False)

    ### Dataset Options
    DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
    INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")

    ### User Options
    LOGIN_DISABLED = _get_bool("LOGIN_DISABLED", False)
    ALLOW_REGISTRATION = _get_bool('ALLOW_REGISTRATION', True)

    ### AI assist (Segment Anything)
    #   SAM_CHECKPOINT: sam2.1_b.pt (default, SAM 2.1 via Ultralytics) or
    #     sam2.1_t/s/l.pt, or an original SAM sam_vit_b/l/h_*.pth. When it is
    #     missing the best checkpoint found in MODELS_DIRECTORY is used.
    #   SAM_MODEL_TYPE: only for original SAM files with other names (vit_b, vit_l, vit_h)
    #   SAM_DEVICE: auto | cpu | cuda
    SAM_MODEL_TYPE = os.getenv("SAM_MODEL_TYPE", "vit_b")
    SAM_CHECKPOINT = os.getenv("SAM_CHECKPOINT", "/models/sam2.1_b.pt")
    SAM_DEVICE = os.getenv("SAM_DEVICE", "auto")
    # image embeddings kept in memory (SAM 1 ~4 MB, SAM 2.1 ~16 MB of RAM each)
    SAM_CACHE_SIZE = int(os.getenv("SAM_CACHE_SIZE", 64))

    ### Trash: deleted items are permanently removed after this many days (0 = never)
    TRASH_DAYS = int(os.getenv("TRASH_DAYS", 90))

    ### Your own models (Ultralytics YOLO .pt files) for pre-annotation
    MODELS_DIRECTORY = os.getenv("MODELS_DIRECTORY", "/models")
    YOLO_DEVICE = os.getenv("YOLO_DEVICE", "auto")

    ### Web terminal (needs the "terminal" permission): an SSH login to this
    #   host only (from the container, the server itself is host.docker.internal).
    #   Off unless TERMINAL_ENABLED=true: no page, no permission, no SSH.
    TERMINAL_ENABLED = _get_bool("TERMINAL_ENABLED", False)
    TERMINAL_SSH_HOST = os.getenv("TERMINAL_SSH_HOST", "host.docker.internal")
    TERMINAL_SSH_PORT = int(os.getenv("TERMINAL_SSH_PORT", 22))
    # a session with no input for this long is closed (minutes, 0 = never)
    TERMINAL_IDLE_MINUTES = int(os.getenv("TERMINAL_IDLE_MINUTES", 60))


__all__ = ["Config"]
