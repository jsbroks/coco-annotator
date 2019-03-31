from celery import Celery
from config import Config


def make_celery():
    celery = Celery(
        Config.NAME,
        backend=Config.CELERY_RESULT_BACKEND,
        broker=Config.CELERY_BROKER_URL
    )

    return celery


celery = make_celery()
celery.autodiscover_tasks(['tasks', 'mantiance'])

