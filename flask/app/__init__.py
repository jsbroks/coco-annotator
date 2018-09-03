from flask import Flask
from werkzeug.contrib.fixers import ProxyFix
from flask_cors import CORS
from config import Config

from watchdog.observers import Observer

from .image_folder import ImageFolderHandler, load_images
from .api import blueprint as api
from .routes import client
from .models import db

import time
import os


app = Flask(__name__)
handler = ImageFolderHandler()
handler.start()

CORS(app)

app.config.from_object(Config)
db.init_app(app)

app.wsgi_app = ProxyFix(app.wsgi_app)
app.register_blueprint(api)
app.register_blueprint(client)


def run_watcher():
    observer = Observer()
    observer.schedule(handler, Config.DATASET_DIRECTORY, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def create_app():

    if not os.path.isdir(Config.DATASET_DIRECTORY):
        os.makedirs(Config.DATASET_DIRECTORY)

    if Config.LOAD_IMAGES_ON_START:
        load_images(Config.DATASET_DIRECTORY)

    return app

