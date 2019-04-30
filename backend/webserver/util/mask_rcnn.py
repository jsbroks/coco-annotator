from config import Config as AnnotatorConfig
from skimage.transform import resize
import imantics as im

from keras.preprocessing.image import img_to_array
from mrcnn.config import Config
import mrcnn.model as modellib
import logging
logger = logging.getLogger('gunicorn.error')


MODEL_DIR = "/workspace/models"
COCO_MODEL_PATH = AnnotatorConfig.MASK_RCNN_FILE
CLASS_NAMES = AnnotatorConfig.MASK_RCNN_CLASSES.split(',')

class CocoConfig(Config):
    """
    Configuration for COCO Dataset.
    """
    NAME = "coco"
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1
    NUM_CLASSES = len(CLASS_NAMES)


class MaskRCNN():

    def __init__(self):

        self.config = CocoConfig()
        self.model = modellib.MaskRCNN(
            mode="inference",
            model_dir=MODEL_DIR,
            config=self.config
        )
        try:
            self.model.load_weights(COCO_MODEL_PATH, by_name=True)
            self.model.keras_model._make_predict_function()
            logger.info(f"Loaded MaskRCNN model: {COCO_MODEL_PATH}")
        except:
            logger.error(f"Could not load MaskRCNN model (place 'mask_rcnn_coco.h5' in the models directory)")
            self.model = None


    def detect(self, image):

        if self.model is None:
            return {}

        image = image.convert('RGB')
        width, height = image.size
        image.thumbnail((1024, 1024))

        image = img_to_array(image)
        result = self.model.detect([image])[0]

        masks = result.get('masks')
        class_ids = result.get('class_ids')

        coco_image = im.Image(width=width, height=height)

        for i in range(masks.shape[-1]):
            mask = resize(masks[..., i], (height, width))
            mask = im.Mask(mask)
            class_id = class_ids[i]
            class_name = CLASS_NAMES[class_id]
            category = im.Category(class_name)
            coco_image.add(mask, category=category)

        return coco_image.coco()


model = MaskRCNN()
