from mrcnn.config import Config
from ..config import Config as AnnotatorConfig
from keras.preprocessing.image import img_to_array
from imantics import Image, Category, Annotation, Mask

import mrcnn.utils as utils
import mrcnn.model as modellib
import numpy as np


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
    
    # COCO class names
    class_names = ['BG', 'person', 'bicycle', 'car', 'motorcycle', 'airplane',
                   'bus', 'train', 'truck', 'boat', 'traffic light',
                   'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
                   'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
                   'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie',
                   'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                   'kite', 'baseball bat', 'baseball glove', 'skateboard',
                   'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
                   'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                   'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
                   'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
                   'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
                   'keyboard', 'cell phone', 'microwave', 'oven', 'toaster',
                   'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors',
                   'teddy bear', 'hair drier', 'toothbrush']

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
        b_width, b_height = image.size
        image.thumbnail((1024, 1024))

        a_width, a_height = image.size
        image = img_to_array(image)
        result = self.model.detect([image])[0]
        
        masks = result.get('masks')
        class_ids = result.get('class_ids')
        scores = result.get('scores')
        
        scale = max(a_width/b_width, a_height/b_height)
        coco_image = Image(width=a_width, height=a_height)

        for i in range(masks.shape[-1]):
            mask = Mask(masks[..., i])
            class_id = class_ids[i]
            class_name = self.class_names[class_id]
            category = Category(class_name)
            coco_image.add(mask, category=category)

        return coco_image.coco()


model = MaskRCNN()

