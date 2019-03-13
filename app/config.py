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
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024  # 1GB
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://database/flask")
    SECRET_KEY = os.getenv("SECRET_KEY", "<--- DEFAULT_SECRET_KEY --->")

    TESTING = os.getenv("TESTING", False)

    # Dataset Options
    DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
    INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")

    # Coco Importer Options
    COCO_IMPORTER_VERBOSE = os.getenv("COCO_IMPORTER_VERBOSE", False)
    COCO_IMPORTER_MAX_WORKERS = int(os.getenv("COCO_IMPORTER_MAX_WORKERS", 4))
    COCO_IMPORTER_IMAGE_BATCH_SIZE = int(
        os.getenv("COCO_IMPORTER_IMAGE_BATCH_SIZE", 1000))
    COCO_IMPORTER_ANNOTATION_BATCH_SIZE = int(
        os.getenv("COCO_IMPORTER_ANNOTATION_BATCH_SIZE", 1000))

    # User Options
    LOGIN_DISABLED = os.getenv("LOGIN_DISABLED", False)
    ALLOW_REGISTRATION = True

    # Mask RCNN MOdel
    ENABLE_MASK_RCNN = True
