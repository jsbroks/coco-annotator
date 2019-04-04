from config import Config
from flask_socketio import SocketIO


def create_socket():
    return SocketIO(message_queue=Config.CELERY_BROKER_URL)
