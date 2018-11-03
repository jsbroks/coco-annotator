from flask import Flask
from werkzeug.contrib.fixers import ProxyFix
from flask_cors import CORS

from watchdog.observers import Observer

from .image_folder import ImageFolderHandler, load_images
from .api import blueprint as api
from .config import Config
from .models import db

import threading
import time


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

    watcher_thread = threading.Thread(target=run_watcher)
    watcher_thread.start()

    if Config.LOAD_IMAGES_ON_START:
        load_images(Config.DATASET_DIRECTORY)

    return Flask(__name__,
                 static_url_path='',
                 static_folder='../dist')


app = create_app()

CORS(app)

app.config.from_object(Config)
db.init_app(app)

app.wsgi_app = ProxyFix(app.wsgi_app)
app.register_blueprint(api)


@app.route('/')
def index():
    return app.send_static_file('index.html')


