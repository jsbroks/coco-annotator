from flask import Flask
from werkzeug.contrib.fixers import ProxyFix
from flask_cors import CORS
from watchdog.observers import Observer

from .image_folder import ImageFolderHandler
from .api import blueprint as api
from .config import Config
from .models import *
from .authentication import login_manager
from .util import query_util, color_util

import threading
import requests
import time
import os


def run_watcher():
    observer = Observer()
    observer.schedule(ImageFolderHandler(), Config.DATASET_DIRECTORY, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def create_app():

    if os.environ.get("APP_WORKER_ID", "1") == "1" and not Config.TESTING:
        print("Creating file watcher on PID: {}".format(os.getpid()), flush=True)
        watcher_thread = threading.Thread(target=run_watcher)
        watcher_thread.start()

    flask = Flask(__name__,
                  static_url_path='',
                  static_folder='../dist')

    flask.config.from_object(Config)

    CORS(flask)

    flask.wsgi_app = ProxyFix(flask.wsgi_app)
    flask.register_blueprint(api)

    db.init_app(flask)
    login_manager.init_app(flask)

    return flask


app = create_app()


if Config.INITIALIZE_FROM_FILE:
    create_from_json(Config.INITIALIZE_FROM_FILE)

if Config.LOAD_IMAGES_ON_START:
    ImageModel.load_images(Config.DATASET_DIRECTORY)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):

    if app.debug:
        return requests.get('http://frontend:8080/{}'.format(path)).text

    return app.send_static_file('index.html')


