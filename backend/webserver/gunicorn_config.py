
from config import Config


bind = '0.0.0.0:5000'
backlog = 2048

workers = 1
worker_class = 'eventlet'
worker_connections = 1000
timeout = 30
keepalive = 2

reload = Config.DEBUG
preload = Config.PRELOAD

errorlog = '-'
loglevel = Config.LOG_LEVEL
accesslog = None