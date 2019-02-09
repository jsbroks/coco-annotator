import eventlet
eventlet.monkey_patch(thread=False)

from flask import Flask
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix

from .models import *
from .config import Config
from .sockets import socketio
from .watcher import run_watcher
from .api import blueprint as api
from .util import query_util, color_util
from .authentication import login_manager

import threading
import requests
import time
import os


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

    db.init_app(flask)
    login_manager.init_app(flask)
    socketio.init_app(flask)

    # Remove all poeple who were annotating when
    # the server shutdown
    ImageModel.objects.update(annotating=[])

    return flask


app = create_app()


if Config.INITIALIZE_FROM_FILE:
    create_from_json(Config.INITIALIZE_FROM_FILE)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):

    if app.debug:
        return requests.get('http://frontend:8080/{}'.format(path)).text

    return app.send_static_file('index.html')
