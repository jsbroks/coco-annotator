from database import ImageModel


def generate_thumbnails():
    PREFIX = "[Thumbnails]"
    print(f'{PREFIX} Sending request for regenerating images with non actual thumbnails', flush=True)
    [generate_thumbnail(image) for image in ImageModel.objects(regenerate_thumbnail=True).all()]


def generate_thumbnail(image):
    from workers.tasks import thumbnail_generate_single_image
    thumbnail_generate_single_image.delay(image.id)
