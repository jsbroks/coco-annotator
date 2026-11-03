import os
import workers

from config import Config
from database import (
    connect_mongo,
    ensure_indexes,
    ImageModel,
    create_from_json
)

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .watcher import run_watcher
from .api import blueprint as api
from .util import query_util, thumbnails
from .authentication import login_manager
from .sockets import socketio
from . import terminal  # noqa: F401  (web terminal socket events)
from . import train_live  # noqa: F401  (a training's output, live)

import requests
import logging


connect_mongo('webserver')
ensure_indexes()


def create_app():

    if Config.FILE_WATCHER:
        run_watcher()

    # trainings run in this process instead of a trainer container
    if os.getenv('TRAINER_EMBEDDED', '').lower() in ('1', 'true', 'yes'):
        from trainer.runner import start_embedded
        start_embedded()

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


# The web page may only run scripts from this server: even if someone gets
# markup into a name, the browser will not run it. (/api keeps the Swagger
# page working, which needs its own inline script.)
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "font-src 'self' data:",
    "connect-src 'self' ws: wss:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'self'",
])


@app.after_request
def security_headers(response):
    from flask import request
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    if not request.path.startswith('/api') and not request.path.startswith('/socket.io'):
        response.headers.setdefault('Content-Security-Policy', CSP)
    return response


@app.before_request
def serve_built_files():
    """Built files: the gzip copy when the browser takes it, and files with a
    content hash in the name (/assets/) cached for a year."""
    from flask import request, send_file
    import mimetypes
    import os
    path = request.path
    if request.method != 'GET' or not (path.startswith('/assets/') or path.startswith('/vendor/')):
        return None
    root = os.path.realpath(app.static_folder)
    file = os.path.realpath(os.path.join(root, path.lstrip('/')))
    if not file.startswith(root + os.sep) or not os.path.isfile(file):
        return None
    hashed = path.startswith('/assets/')
    gz = file + '.gz'
    accepts = 'gzip' in (request.headers.get('Accept-Encoding') or '').lower()
    if accepts and os.path.isfile(gz):
        mime = mimetypes.guess_type(file)[0] or 'application/octet-stream'
        response = send_file(gz, mimetype=mime, conditional=True, etag=True,
                             max_age=31536000 if hashed else 0)
        response.headers['Content-Encoding'] = 'gzip'
    else:
        response = send_file(file, conditional=True, etag=True, max_age=31536000 if hashed else 0)
    response.headers['Vary'] = 'Accept-Encoding'
    if hashed:
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    
    if app.debug:
        return requests.get('http://frontend:8080/{}'.format(path)).text

    return app.send_static_file('index.html')
