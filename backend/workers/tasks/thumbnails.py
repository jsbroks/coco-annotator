import os
import logging

from database import ImageModel
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def thumbnail_generate_single_image(image_id):
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        # e.g. a queued task for an image that was deleted in the meantime
        logger.warning(f"Skipping thumbnail for image {image_id}: image no longer exists")
        return
    if not os.path.isfile(image.path):
        logger.warning(f"Skipping thumbnail for image {image_id}: file missing ({image.path})")
        return
    image.thumbnail()
    image.flag_thumbnail(flag=False)


__all__ = ["thumbnail_generate_single_image"]
