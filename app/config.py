
class Config:

    DEBUG = True
    MONGOALCHEMY_DATABASE = 'library'
    SWAGGER_UI_JSONEDITOR = True
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15MB
    MONGODB_SETTINGS = {'host': 'mongodb://database/flask'}

    DATASET_DIRECTORY = '/data/datasets/'
    LOAD_IMAGES_ON_START = False

