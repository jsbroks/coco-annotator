from config import Config as AnnotatorConfig
import imantics as im
import cv2
import numpy as np
import logging
logger = logging.getLogger('gunicorn.error')

from detectron2.projects.deeplab import add_deeplab_config
from detectron2.config import get_cfg
from detectron2.engine.defaults import DefaultPredictor
from detectron2.data import MetadataCatalog
from detectron2.data.detection_utils import _apply_exif_orientation, convert_PIL_to_numpy




from MaskFormer.mask_former import add_mask_former_config

from MaskFormer.mask_former.mask_former_model import MaskFormer

MODEL_DIR = "/workspace/models"
COCO_MODEL_PATH = AnnotatorConfig.MASK_FORMER_FILE
COCO_MODEL_WEIGHTS = AnnotatorConfig.MASK_FORMER_WEIGHTS

def get_config():
    """
    Configuration for COCO Dataset.
    """
    cfg = get_cfg()
    add_deeplab_config(cfg)
    add_mask_former_config(cfg)
    cfg.merge_from_file(COCO_MODEL_PATH)

    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.75

    cfg.MODEL.WEIGHTS = COCO_MODEL_WEIGHTS

    cfg.MODEL.DEVICE='cpu'

    cfg.freeze()

    return cfg


class MaskFormerModel():

    def __init__(self):

        self.config = get_config()
        self.model = DefaultPredictor(self.config)

        self.classes = MetadataCatalog.get(self.config.DATASETS.TRAIN[0]).stuff_classes
        self.classes = [class_name.split(',')[0] for class_name in self.classes]
        
        logger.info(f"Loaded MaskFormer model.")


    def detect(self, image):

        if self.model is None:
            return {}

        image = _apply_exif_orientation(image)
        image = convert_PIL_to_numpy(image, format="BGR")
        height, width, col_channels = image.shape

        predictions = self.model(image)
        pred_grid = predictions['sem_seg'].argmax(dim=0)

        labels = pred_grid.unique()

        class_id_list = []
        mask_list = []
        label_list = []

        for i in range(len(labels)):
            pred_lab = pred_grid == labels[i]
            polygons = im.Mask(pred_lab).polygons()

            for j in range(len(polygons.points)):
                coords = polygons.points[j]
                zeros = np.zeros(pred_grid.shape, dtype=np.uint8)
                mask = cv2.fillPoly(zeros, [np.array(coords, dtype=np.int32)], 1)
                class_id_list.append(labels[i].item())
                label_list.append(self.classes[labels[i].item()])
                mask_list.append(mask)

        result = {
            'class_ids': np.array(class_id_list),
            'masks': np.dstack(mask_list),
            'labels': np.array(label_list)
        }       

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


model = MaskFormerModel()
