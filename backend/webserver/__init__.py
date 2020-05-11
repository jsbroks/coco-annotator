import eventlet
eventlet.monkey_patch(thread=False)

import sys
import workers

from config import Config
from database import (
    connect_mongo,
    ImageModel,
    create_from_json
)

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

from celery import Celery

from .watcher import run_watcher
from .api import blueprint as api
from .util import query_util, thumbnails
from .authentication import login_manager
from .sockets import socketio

import threading
import requests
import logging
import time
import os


connect_mongo('webserver')


def create_app():

    if Config.FILE_WATCHER:
        run_watcher()

    flask = Flask(__name__,
                  static_url_path='',
                  static_folder='../dist')

    flask.config.from_object(Config)

    CORS(flask)

    flask.wsgi_app = ProxyFix(flask.wsgi_app)
    flask.register_blueprint(api)

    login_manager.init_app(flask)
    socketio.init_app(flask, message_queue=Config.CELERY_BROKER_URL)
    # Remove all poeple who were annotating when
    # the server shutdown
    ImageModel.objects.update(annotating=[])
    thumbnails.generate_thumbnails()

    return flask


app = create_app()

logger = logging.getLogger('gunicorn.error')
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)
    

if Config.INITIALIZE_FROM_FILE:
    create_from_json(Config.INITIALIZE_FROM_FILE)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    
    if app.debug:
        return requests.get('http://frontend:8080/{}'.format(path)).text

    return app.send_static_file('index.html')
