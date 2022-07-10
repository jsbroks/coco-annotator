from config import Config as AnnotatorConfig
import imantics as im
import cv2
import numpy as np
import logging
logger = logging.getLogger('gunicorn.error')

# from detectron2.projects.deeplab import add_deeplab_config
from detectron2.config import get_cfg
from detectron2.engine.defaults import DefaultPredictor
from detectron2.data import MetadataCatalog
from detectron2.data.detection_utils import _apply_exif_orientation, convert_PIL_to_numpy

from detectron2.utils.visualizer import GenericMask


COCO_CATEGORIES = [
    {"color": [220, 20, 60], "isthing": 1, "id": 1, "name": "text"},
    {"color": [119, 11, 32], "isthing": 1, "id": 2, "name": "0"},
    {"color": [0, 0, 142], "isthing": 1, "id": 3, "name": "1"},
    {"color": [0, 0, 230], "isthing": 1, "id": 4, "name": "2"},
    {"color": [106, 0, 228], "isthing": 1, "id": 5, "name": "3"},
    {"color": [0, 60, 100], "isthing": 1, "id": 6, "name": "4"},
    {"color": [0, 80, 100], "isthing": 1, "id": 7, "name": "5"},
    {"color": [0, 0, 70], "isthing": 1, "id": 8, "name": "6"},
    {"color": [0, 0, 192], "isthing": 1, "id": 9, "name": "7"},
    {"color": [250, 170, 30], "isthing": 1, "id": 10, "name": "8"},
    {"color": [100, 170, 30], "isthing": 1, "id": 11, "name": "9"},
    {"color": [220, 220, 0], "isthing": 1, "id": 12, "name": "A"},
    {"color": [175, 116, 175], "isthing": 1, "id": 13, "name": "B"},
    {"color": [250, 0, 30], "isthing": 1, "id": 14, "name": "C"},
    {"color": [165, 42, 42], "isthing": 1, "id": 15, "name": "D"},
    {"color": [255, 77, 255], "isthing": 1, "id": 16, "name": "E"},
    {"color": [0, 226, 252], "isthing": 1, "id": 17, "name": "F"},
    {"color": [182, 182, 255], "isthing": 1, "id": 18, "name": "G"},
    {"color": [0, 82, 0], "isthing": 1, "id": 19, "name": "H"},
    {"color": [120, 166, 157], "isthing": 1, "id": 20, "name": "I"},
    {"color": [110, 76, 0], "isthing": 1, "id": 21, "name": "J"},
    {"color": [174, 57, 255], "isthing": 1, "id": 22, "name": "K"},
    {"color": [199, 100, 0], "isthing": 1, "id": 23, "name": "L"},
    {"color": [72, 0, 118], "isthing": 1, "id": 24, "name": "M"},
    {"color": [255, 179, 240], "isthing": 1, "id": 25, "name": "N"},
    {"color": [0, 125, 92], "isthing": 1, "id": 26, "name": "O"},
    {"color": [209, 0, 151], "isthing": 1, "id": 27, "name": "P"},
    {"color": [188, 208, 182], "isthing": 1, "id": 28, "name": "Q"},
    {"color": [0, 220, 176], "isthing": 1, "id": 29, "name": "R"},
    {"color": [255, 99, 164], "isthing": 1, "id": 30, "name": "S"},
    {"color": [92, 0, 73], "isthing": 1, "id": 31, "name": "T"},
    {"color": [133, 129, 255], "isthing": 1, "id": 32, "name": "U"},
    {"color": [78, 180, 255], "isthing": 1, "id": 33, "name": "V"},
    {"color": [0, 228, 0], "isthing": 1, "id": 34, "name": "W"},
    {"color": [174, 255, 243], "isthing": 1, "id": 35, "name": "X"},
    {"color": [45, 89, 255], "isthing": 1, "id": 36, "name": "Y"},
    {"color": [134, 134, 103], "isthing": 1, "id": 37, "name": "Z"},
    {"color": [145, 148, 174], "isthing": 1, "id": 38, "name": "a"},
    {"color": [255, 208, 186], "isthing": 1, "id": 39, "name": "b"},
    {"color": [197, 226, 255], "isthing": 1, "id": 40, "name": "c"},
    {"color": [171, 134, 1], "isthing": 1, "id": 41, "name": "d"},
    {"color": [109, 63, 54], "isthing": 1, "id": 42, "name": "e"},
    {"color": [207, 138, 255], "isthing": 1, "id": 43, "name": "f"},
    {"color": [151, 0, 95], "isthing": 1, "id": 44, "name": "g"},
    {"color": [9, 80, 61], "isthing": 1, "id": 45, "name": "h"},
    {"color": [84, 105, 51], "isthing": 1, "id": 46, "name": "i"},
    {"color": [74, 65, 105], "isthing": 1, "id": 47, "name": "j"},
    {"color": [166, 196, 102], "isthing": 1, "id": 48, "name": "k"},
    {"color": [208, 195, 210], "isthing": 1, "id": 49, "name": "l"},
    {"color": [255, 109, 65], "isthing": 1, "id": 50, "name": "m"},
    {"color": [0, 143, 149], "isthing": 1, "id": 51, "name": "n"},
    {"color": [179, 0, 194], "isthing": 1, "id": 52, "name": "o"},
    {"color": [209, 99, 106], "isthing": 1, "id": 53, "name": "p"},
    {"color": [5, 121, 0], "isthing": 1, "id": 54, "name": "q"},
    {"color": [227, 255, 205], "isthing": 1, "id": 55, "name": "r"},
    {"color": [147, 186, 208], "isthing": 1, "id": 56, "name": "s"},
    {"color": [153, 69, 1], "isthing": 1, "id": 57, "name": "t"},
    {"color": [3, 95, 161], "isthing": 1, "id": 58, "name": "u"},
    {"color": [163, 255, 0], "isthing": 1, "id": 59, "name": "v"},
    {"color": [119, 0, 170], "isthing": 1, "id": 60, "name": "w"},
    {"color": [0, 182, 199], "isthing": 1, "id": 61, "name": "x"},
    {"color": [0, 165, 120], "isthing": 1, "id": 62, "name": "y"},
    {"color": [183, 130, 88], "isthing": 1, "id": 63, "name": "z"},
    {"color": [250, 141, 255], "isthing": 0, "id": 64, "name": "background"},
]



# from MaskFormer.mask_former import add_mask_former_config

# from MaskFormer.mask_former.mask_former_model import MaskFormer

MODEL_DIR = "/workspace/models"
COCO_MODEL_PATH = AnnotatorConfig.DETECTRON2_FILE
COCO_MODEL_WEIGHTS = AnnotatorConfig.DETECTRON2_WEIGHTS

def get_config():
    """
    Configuration for COCO Dataset.
    """
    cfg = get_cfg()
    # add_deeplab_config(cfg)
    # add_mask_former_config(cfg)
    cfg.merge_from_file(COCO_MODEL_PATH)

    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.75

    cfg.MODEL.WEIGHTS = COCO_MODEL_WEIGHTS

    cfg.MODEL.DEVICE='cpu'

    cfg.freeze()

    return cfg


class Detectron2Model():

    def __init__(self):

        self.config = get_config()
        self.model = DefaultPredictor(self.config)

        # self.classes = MetadataCatalog.get(self.config.DATASETS.TRAIN[0]).thing_classes
        # self.classes = [class_name.split(',')[0] for class_name in self.classes]
        self.classes = [c["name"] for c in COCO_CATEGORIES]
        
        logger.info(f"Loaded Detectron2 model.")


    def detect(self, image):

        if self.model is None:
            return {}

        image = _apply_exif_orientation(image)
        image = convert_PIL_to_numpy(image, format="BGR")
        height, width, col_channels = image.shape

        predictions = self.model(image)
        pred_grid = predictions['instances'].to("cpu")

        classes = pred_grid.pred_classes.tolist() if pred_grid.has("pred_classes") else None

        class_id_list = []
        mask_list = []
        label_list = []

        if pred_grid.has("pred_masks"):
            masks = np.asarray(pred_grid.pred_masks)
            masks = [GenericMask(x, height, width).mask for x in masks]
            # polygons = np.asarray(pred_grid.pred_masks)
            # polygons = [GenericMask(x, height, width).polygons for x in masks]
            mask_list=masks
            class_id_list=classes
            label_list = [self.classes[i] for i in classes]
        else:
            masks = None

        print("labels:", len(label_list))
        logger.info("labels: {}".format(len(label_list)))


        result = {
            'class_ids': np.array(class_id_list),
            'masks': np.dstack(mask_list),
            'labels': np.array(label_list)
        }       

        logger.info('result: {}'.format(result))
        masks = result.get('masks')
        class_ids = result.get('class_ids')
        labels = result.get('labels')

        coco_image = im.Image(width=width, height=height)

        for i in range(masks.shape[-1]):
            mask = masks[..., i]
            mask = im.Mask(mask)
            class_id = class_ids[i]
            class_name = labels[i]
            category = im.Category(class_name)
            coco_image.add(mask, category=category)

        return coco_image.coco()


model = Detectron2Model()
