from database import ImageModel
from celery import task


@task
def thumbnail_generate_single_image(image_id):
    image = ImageModel.objects(id=image_id).first()
    image.thumbnail()
    image.flag_thumbnail(flag=False)


__all__ = ["thumbnail_generate_single_image"]