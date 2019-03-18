import os

from .util.version_util import get_tag


class Config:

    NAME = "COCO Annotator"
    VERSION = get_tag()

    # File Watcher
    FILE_WATCHER = os.getenv("FILE_WATCHER", False)
    IGNORE_DIRECTORIES = ["_thumbnail", "_settings"]

    # Flask instance
    SWAGGER_UI_JSONEDITOR = True
    MAX_CONTENT_LENGTH = os.getenv("MAX_CONTENT_LENGTH", 1 * 1024 * 1024 * 1024)  # 1GB
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://database/flask")
    SECRET_KEY = os.getenv("SECRET_KEY", "<--- CHANGE THIS KEY --->")

    TESTING = os.getenv("TESTING", False)

    # Dataset Options
    DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
    DATASET_THUMBNAILS = os.getenv("DATASET_THUMBNAILS", "/thumbnails/")
    INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")

    # User Options
    LOGIN_DISABLED = os.getenv("LOGIN_DISABLED", False)
    ALLOW_REGISTRATION = True

    # Models
    MASK_RCNN_FILE = os.getenv("MASK_RCNN_FILE", "")
    MASK_RCNN_CLASSES = os.getenv("MASK_RCNN_CLASSES", "BG")

    DEXTR_FILE = os.getenv("DEXTR_FILE", "/models/dextr_pascal-sbd.h5")
