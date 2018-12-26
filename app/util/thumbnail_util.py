import numpy as np

from ..models import AnnotationModel
from .color_util import hex_to_rgb
from .coco_util import decode_seg

from PIL import Image


def apply_mask(image, mask, color, alpha=0.5):
    """Apply the given mask to the image.
    """
    for c in range(3):
        image[:, :, c] = np.where(mask == 1,
                                  image[:, :, c] *
                                  (1 - alpha) + alpha * color[c] * 255,
                                  image[:, :, c])
    return image


def generate_thumbnail(image_model, save=True):

    image = Image.open(image_model.path)
    binary_image = np.array(image)
    binary_image.setflags(write=True)

    annotations = AnnotationModel.objects(image_id=image_model.id, deleted=False).all()

    for annotation in annotations:

        if len(annotation.segmentation) == 0:
            continue

        color = np.array(hex_to_rgb(annotation.color))/255
        binary_image = apply_mask(binary_image, annotation.mask(), color)

    image = Image.fromarray(binary_image)

    if save:
        image.save(image_model.thumbnail_path())

    return image





