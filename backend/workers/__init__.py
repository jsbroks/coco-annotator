import os
import sys

# `celery -A workers` only puts the working directory on sys.path while it
# loads the app, so later task-module imports of sibling packages (geometry,
# database, ...) would fail. Make the backend folder importable for good.
# (Appended unconditionally: celery removes its own temporary entry later.)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_BACKEND_DIR)

from celery import Celery
from config import Config
from database import connect_mongo

connect_mongo('Celery_Worker')

celery = Celery(
    Config.NAME,
    backend=Config.CELERY_RESULT_BACKEND,
    broker=Config.CELERY_BROKER_URL
)
celery.conf.update(
    broker_connection_retry_on_startup=True,
    # Run tasks in-process (no worker/broker needed) for local development
    task_always_eager=Config.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=Config.CELERY_TASK_ALWAYS_EAGER,
    # Progress is tracked in TaskModel; nothing reads Celery's own results,
    # which otherwise pile up in the celery_taskmeta collection forever.
    task_ignore_result=True,
)
# shared_task resolves the "current" app, which is thread-local: make this
# app the process-wide default so request threads (gthread) use it too.
celery.set_default()
celery.autodiscover_tasks(['workers.tasks'])


if __name__ == '__main__':
    celery.start()
