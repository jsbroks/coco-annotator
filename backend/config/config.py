import os
import subprocess
import json
from typing import Optional

def get_tag():
    result = subprocess.run(["git", "describe", "--abbrev=0", "--tags"], stdout=subprocess.PIPE)
    return str(result.stdout.decode("utf-8")).strip()

def _get_bool(key, default_value):
    if key in os.environ:
        value = os.environ[key]
        if value == 'True' or value == 'true' or value == '1':
            return True
        return False
    return default_value

def mask_classes(code_json: str='/models/code_config.json') -> Optional[str]:

    base_class = "BG"

    if not os.path.exists(code_json):
        return base_class

    with open(code_json, 'r') as f:
        class_dict = json.load(f)

    class_list = [class_name.replace(',', '') for class_name in class_dict.keys()]

    return base_class + ',' + ','.join(class_list)

class Config:

    NAME = os.getenv("NAME", "COCO Annotator")
    VERSION = get_tag()

    ### File Watcher
    FILE_WATCHER = os.getenv("FILE_WATCHER", False)
    IGNORE_DIRECTORIES = ["_thumbnail", "_settings"]

    # Flask/Gunicorn
    #
    #   LOG_LEVEL - The granularity of log output
    #
    #       A string of "debug", "info", "warning", "error", "critical"
    #
    #   WORKER_CONNECTIONS - limits the maximum number of simultaneous
    #       clients that a single process can handle.
    #
    #       A positive integer generally set to around 1000.
    #
    #   WORKER_TIMEOUT - If a worker does not notify the master process
    #       in this number of seconds it is killed and a new worker is
    #       spawned to replace it.
    #
    SWAGGER_UI_JSONEDITOR = True
    DEBUG = os.getenv("DEBUG", 'false').lower() == 'true'
    PRELOAD = False

    MAX_CONTENT_LENGTH = os.getenv("MAX_CONTENT_LENGTH", 1 * 1024 * 1024 * 1024)  # 1GB
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://database/flask")
    SECRET_KEY = os.getenv("SECRET_KEY", "<--- CHANGE THIS KEY --->")

    LOG_LEVEL = 'debug'
    WORKER_CONNECTIONS = 1000

    TESTING = os.getenv("TESTING", False)

    ### Workers
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://user:password@messageq:5672//")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "mongodb://database/flask")

    ### Dataset Options
    DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
    INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")

    ### User Options
    LOGIN_DISABLED = _get_bool("LOGIN_DISABLED", False)
    ALLOW_REGISTRATION = _get_bool('ALLOW_REGISTRATION', True)

    ### Models
    MASK_RCNN_FILE = os.getenv("MASK_RCNN_FILE", "/models/mask_rcnn_ade20k_0080.h5")
    MASK_RCNN_CLASSES = os.getenv("MASK_RCNN_CLASSES", mask_classes())

    DEXTR_FILE = os.getenv("DEXTR_FILE", "/models/dextr_pascal-sbd.h5")

    DETECTRON2_FILE = os.getenv("DETECTRON2_FILE", "/models/ade20k-150/maskformer_R50_bs16_160k.yaml")
    DETECTRON2_WEIGHTS = os.getenv("DETECTRON2_WEIGHTS", "https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R50_bs16_160k/model_final_d8dbeb.pkl")
    # MASK_FORMER_FILE = os.getenv("MASK_FORMER_FILE", "/models/ade20k-150/maskformer_R50_bs16_160k.yaml")
    # MASK_FORMER_WEIGHTS = os.getenv("MASK_FORMER_WEIGHTS", "https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R50_bs16_160k/model_final_d8dbeb.pkl")
    MASK_FORMER_FILE = os.getenv("MASK_FORMER_FILE", "")
    MASK_FORMER_WEIGHTS = os.getenv("MASK_FORMER_WEIGHTS", "")

    MASK_COCO_FILE = os.getenv("MASK_COCO_FILE", "/models/mask_rcnn_coco.h5")
    MASK_COCO_CLASSES = os.getenv("MASK_COCO_CLASSES", "BG,person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush")


__all__ = ["Config"]
