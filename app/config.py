import os


class Config:

    NAME = "COCO Annotator"
    VERSION = "0.1"

    # Flask instance
    SWAGGER_UI_JSONEDITOR = True
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024  # 1GB
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://database/flask")
    SECRET_KEY = os.getenv('SECRET_KEY', '<--- YOUR_SECRET_FORM_KEY --->')

    TESTING = os.getenv("TESTING", False)

    # Dataset Options
    DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
    INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")
    LOAD_IMAGES_ON_START = os.getenv("LOAD_IMAGES_ON_START", False)

    # User Options
    ALLOW_REGISTRATION = True


