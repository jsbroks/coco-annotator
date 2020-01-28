import os
import imantics as im


from PIL import Image
from mongoengine import *

from .events import Event, SessionEvent
from .datasets import DatasetModel
from .annotations import AnnotationModel

class ImageModel(DynamicDocument):

    COCO_PROPERTIES = ["id", "width", "height", "file_name", "path", "license",\
                       "flickr_url", "coco_url", "date_captured", "dataset_id"]

    # -- Contants
    THUMBNAIL_DIRECTORY = '.thumbnail'
    PATTERN = (".gif", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".GIF", ".PNG", ".JPG", ".JPEG", ".BMP", ".TIF", ".TIFF")

    # Set maximum thumbnail size (h x w) to use on dataset page
    MAX_THUMBNAIL_DIM = (1024, 1024)

    # -- Private
    _dataset = None

    # -- Database
    id = SequenceField(primary_key=True)
    dataset_id = IntField(required=True)
    category_ids = ListField(default=[])

    # Absolute path to image file
    path = StringField(required=True, unique=True)
    width = IntField(required=True)
    height = IntField(required=True)
    file_name = StringField()
    
    # True if the image is annotated
    annotated = BooleanField(default=False)
    # Poeple currently annotation the image
    annotating = ListField(default=[])
    num_annotations = IntField(default=0)
    
    thumbnail_url = StringField()
    image_url = StringField()
    coco_url = StringField()
    date_captured = DateTimeField()

    metadata = DictField()
    license = IntField()

    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    milliseconds = IntField(default=0)
    events = EmbeddedDocumentListField(Event)
    regenerate_thumbnail = BooleanField(default=False)

    @classmethod
    def create_from_path(cls, path, dataset_id=None):

        pil_image = Image.open(path)

        image = cls()
        image.file_name = os.path.basename(path)
        image.path = path
        image.width = pil_image.size[0]
        image.height = pil_image.size[1]

        if dataset_id is not None:
            image.dataset_id = dataset_id
        else:
            # Get dataset name from path
            folders = path.split('/')
            i = folders.index("datasets")
            dataset_name = folders[i+1]

            dataset = DatasetModel.objects(name=dataset_name).first()
            if dataset is not None:
                image.dataset_id = dataset.id

        pil_image.close()

        return image

    def delete(self, *args, **kwargs):
        self.thumbnail_delete()
        AnnotationModel.objects(image_id=self.id).delete()
        return super(ImageModel, self).delete(*args, **kwargs)

    def thumbnail(self):
        """
        Generates (if required) and returns thumbnail
        """
        
        thumbnail_path = self.thumbnail_path()

        if self.regenerate_thumbnail or \
            not os.path.isfile(thumbnail_path):
            
            # logger.debug(f'Generating thumbnail for {self.id}')

            pil_image = self.generate_thumbnail()
            pil_image = pil_image.convert("RGB")

            # Resize image to fit in MAX_THUMBNAIL_DIM envelope as necessary
            pil_image.thumbnail((self.MAX_THUMBNAIL_DIM[1], self.MAX_THUMBNAIL_DIM[0]))

            # Save as a jpeg to improve loading time
            # (note file extension will not match but allows for backwards compatibility)
            pil_image.save(thumbnail_path, "JPEG", quality=80, optimize=True, progressive=True)

            self.update(is_modified=False)
            return pil_image
        else:
            return Image.open(thumbnail_path)
    
    def thumbnail_path(self):
        folders = self.path.split('/')
        folders.insert(len(folders)-1, self.THUMBNAIL_DIRECTORY)

        path = '/' + os.path.join(*folders)
        directory = os.path.dirname(path)

        if not os.path.exists(directory):
            os.makedirs(directory)
        
        return path
    
    def thumbnail_delete(self):
        path = self.thumbnail_path()
        if os.path.isfile(path):
            os.remove(path)

    def generate_thumbnail(self):
        image = self().draw(color_by_category=True, bbox=False)
        return Image.fromarray(image)

    def flag_thumbnail(self, flag=True):
        """
        Toggles values to regenerate thumbnail on next thumbnail request
        """
        if self.regenerate_thumbnail != flag:
            self.update(regenerate_thumbnail=flag)

    def copy_annotations(self, annotations):
        """
        Creates a copy of the annotations for this image
        :param annotations: QuerySet of annotation models
        :return: number of annotations
        """
        annotations = annotations.filter(
            width=self.width, height=self.height, area__gt=0).exclude('events')

        for annotation in annotations:
            clone = annotation.clone()

            clone.dataset_id = self.dataset_id
            clone.image_id = self.id

            clone.save(copy=True)

        return annotations.count()

    @property
    def dataset(self):
        if self._dataset is None:
            self._dataset = DatasetModel.objects(id=self.dataset_id).first()
        return self._dataset

    def __call__(self):

        image = im.Image.from_path(self.path)
        for annotation in AnnotationModel.objects(image_id=self.id, deleted=False).all():
            if not annotation.is_empty():
                image.add(annotation())

        return image
    
    def can_delete(self, user):
        return user.can_delete(self.dataset)
    
    def can_download(self, user):
        return user.can_download(self.dataset)
    
    # TODO: Fix why using the functions throws an error
    def permissions(self, user):
        return {
            'delete': True,
            'download': True
        }
    
    def add_event(self, e):
        u = {
            'push__events': e,
        }
        if isinstance(e, SessionEvent):
            u['inc__milliseconds'] = e.milliseconds

        self.update(**u)


__all__ = ["ImageModel"]
