
class Config:

    NAME = "COCO Annotator"
    VERSION = "0.1"

    SWAGGER_UI_JSONEDITOR = True
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024  # 1GB
    MONGODB_SETTINGS = {'host': 'mongodb://database/flask'}

    DATASET_DIRECTORY = '/data/datasets/'
    LOAD_IMAGES_ON_START = False

