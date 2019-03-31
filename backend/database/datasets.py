from mongoengine import *
from config import Config


class DatasetModel(DynamicDocument):
    
    id = SequenceField(primary_key=True)
    name = StringField(required=True, unique=True)
    directory = StringField()
    thumbnails = StringField()
    categories = ListField(default=[])

    owner = StringField(required=True)
    users = ListField(default=[])

    annotate_url = StringField(default="")

    default_annotation_metadata = DictField(default={})

    deleted = BooleanField(default=False)
    deleted_date = DateTimeField()

    def save(self, *args, **kwargs):

        directory = os.path.join(Config.DATASET_DIRECTORY, self.name + '/')

        if not os.path.exists(directory):
            os.makedirs(directory)

        self.directory = directory

        # if current_user:
        #     self.owner = current_user.username
        # else:
        #     self.owner = 'system'

        return super(DatasetModel, self).save(*args, **kwargs)
    
    # def download_images(self, keywords, limit=100):

    #     task = TaskModel(
    #         name="Downloading {} images to {} with keywords {}".format(limit, self.name, keywords),
    #         dataset_id=self.id,
    #         group="Downloading Images"
    #     )

    #     def download_images(task, dataset, keywords, limit):
    #         def custom_print(string):
    #             __builtins__.print("%f -- %s" % (time.time(), string))

    #             print = dprint
    #             task.log()
    #         for keyword in args['keywords']:
    #             response = gid.googleimagesdownload()
    #             response.download({
    #                 "keywords": keyword,
    #                 "limit": args['limit'],
    #                 "output_directory": output_dir,
    #                 "no_numbering": True,
    #                 "format": "jpg",
    #                 "type": "photo",
    #                 "print_urls": False,
    #                 "print_paths": False,
    #                 "print_size": False
    #             })

    #     return task

    # def import_coco(self, coco):
    #     from .util.task_util import import_coco_func
    #     task = TaskModel(
    #         name="Import COCO ({})".format(self.name),
    #         dataset_id=self.id,
    #         group="Annotation Import"
    #     )
    #     task.save()
    #     task.start(import_coco_func, dataset=self, coco_json=coco)

    #     return task.api_json()

    # def export_coco(self):

    #     from .util.task_util import export_coco_func
    #     task = TaskModel(
    #         name="Export COCO ({})".format(self.name),
    #         dataset_id=self.id,
    #         group="Annotation Export"
    #     )
    #     task.save()
    #     task.start(export_coco_func, dataset=self)

    #     return task.api_json()

    # def scan(self):

    #     from .util.task_util import scan_func
    #     task = TaskModel(
    #         name=f"Scanning {self.name} for new images",
    #         dataset_id=self.id,
    #         group="Directory Image Scan"
    #     )
    #     task.save()
    #     task.start(scan_func, dataset=self)

    #     return task.api_json()

    def is_owner(self, user):

        if user.is_admin:
            return True
        
        return user.username.lower() == self.owner.lower()

    def can_download(self, user):
        return self.is_owner(user)

    def can_delete(self, user):
        return self.is_owner(user)
    
    def can_share(self, user):
        return self.is_owner(user)
    
    def can_generate(self, user):
        return self.is_owner(user)

    def can_edit(self, user):
        return user.username in self.users or self.is_owner(user)
    
    def permissions(self, user):
        return {
            'owner': self.is_owner(user),
            'edit': self.can_edit(user),
            'share': self.can_share(user),
            'generate': self.can_generate(user),
            'delete': self.can_delete(user),
            'download': self.can_download(user)
        }


__all__ = ["DatasetModel"]