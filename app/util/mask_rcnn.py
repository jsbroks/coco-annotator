from mrcnn.config import Config
from ..config import Config as AnnotatorConfig
from keras.preprocessing.image import img_to_array

import mrcnn.utils as utils
import mrcnn.model as modellib

import numpy as np

from keras.backend import clear_session


MODEL_DIR = "/workspace/models"
COCO_MODEL_PATH = "/models/mask_rcnn_coco.h5"


class CocoConfig(Config):
    """
    Configuration for COCO Dataset.
    """
    NAME = "coco"
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1
    NUM_CLASSES = 1 + 80


class MaskRCNN():

    def __init__(self):
        
        if not AnnotatorConfig.ENABLE_MASK_RCNN:
            self.model = None
            return
        
        self.config = CocoConfig()

        self.model = modellib.MaskRCNN(
            mode="inference",
            model_dir=MODEL_DIR,
            config=self.config
        )
        try:
            self.model.load_weights(COCO_MODEL_PATH, by_name=True)
            self.model.keras_model._make_predict_function()
        except:
            print("Could not load MaskRCNN model (place 'mask_rcnn_coco.h5' in the models directory)", flush=True)
            self.model = None
                

    def detect(self, image):

        if self.model == None:
            return {}
        
        image = image.convert('RGB')
        image.thumbnail((1024, 1024))
        image = img_to_array(image)
        result = self.model.detect([image], verbose=1)[0]

        coco = {}
        return coco


model = MaskRCNN()

