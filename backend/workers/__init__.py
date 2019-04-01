from celery import Celery
from config import Config


celery = Celery(
    Config.NAME,
    backend=Config.CELERY_RESULT_BACKEND,
    broker=Config.CELERY_BROKER_URL
)
celery.autodiscover_tasks(['workers.tasks'])


if __name__ == '__main__':
    celery.start()
