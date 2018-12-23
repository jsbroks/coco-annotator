import copy
from flask_restplus import Namespace, Api, Resource, reqparse
from flask import request

from ..util import query_util
from ..util import coco_util
from ..models import *


api = Namespace('annotator', description='Annotator related operations')


@api.route('/data')
class AnnotatorData(Resource):

    def post(self):
        """
        Called when saving data from the annotator client
        """
        data = request.get_json(force=True)
        image = data.get('image')
        image_id = image.get('id')

        image_model = ImageModel.objects(id=image_id).first()

        if image_model is None:
            return {'message': 'image does not exist'}, 400

        categories = CategoryModel.objects.all()
        annotations = AnnotationModel.objects(image_id=image_id)

        annotated = False
        # Iterate every category passed in the data
        for category in data.get('categories', []):
            category_id = category.get('id')

            # Find corresponding category object in the database
            db_category = categories.filter(id=category_id).first()
            if db_category is None:
                continue

            db_category.update(set__color=category.get('color'))

            # Iterate every annotation from the data annotations
            for annotation in category.get('annotations', []):

                # Find corresponding annotation object in database
                annotation_id = annotation.get('id')
                db_annotation = annotations.filter(id=annotation_id).first()

                if db_annotation is None:
                    continue

                # Paperjs objects are complex, so they will not always be passed. Therefor we update
                # the annotation twice, checking if the paperjs exists.

                # Update annotation in database
                db_annotation.update(
                    set__metadata=annotation.get('metadata'),
                    set__color=annotation.get('color')
                )

                paperjs_object = annotation.get('compoundPath', [])

                # Update paperjs if it exists
                if len(paperjs_object) == 2:

                    width = db_annotation.width
                    height = db_annotation.height

                    # Generate coco formatted segmentation data
                    segmentation, area, bbox = coco_util.\
                        paperjs_to_coco(width, height, paperjs_object)

                    db_annotation.update(
                        set__segmentation=segmentation,
                        set__area=area,
                        set__bbox=bbox,
                        set__paper_object=paperjs_object,
                    )

                    if area > 0:
                        annotated = True

        image_model.update(
            set__metadata=image.get('metadata', {}),
            set__annotated=annotated,
            set__category_ids=image.get('category_ids', [])
        )

        return data


@api.route('/data/<int:image_id>')
class AnnotatorId(Resource):

    def put(self, image_id):
        """Called when copying/adding annotations from another image"""

        image = ImageModel.objects(id=image_id).first()

        if image is None:
            return {'success': False}, 400

        data = request.get_json(force=True)
        # add these annotations by id
        annotations_to_add = data.get('addAnnotations', [])
        # add all annotations from these image ids
        add_annotations_from = data.get('add_annotations_from', [])

        if add_annotations_from:
            # validate the passed image ids are numbers
            from_image_ids = []
            for from_image_id in add_annotations_from:
                try:
                    from_image_ids.append(int(from_image_id))
                except ValueError:
                    return {'success': False}, 400

            annotation_ids = AnnotationModel.objects(
                image_id__in=from_image_ids).filter(
                    deleted=False, area__gt=0).distinct('_id')
            annotations_to_add += annotation_ids

        if annotations_to_add:
            dataset = DatasetModel.objects(id=image.dataset_id).first()
            dataset_categories = dataset.categories
            image_categories = image.category_ids

            annotations = AnnotationModel.objects(id__in=list(set(annotations_to_add)))
            existing_annotations = list(AnnotationModel.objects(image_id=image_id).filter(deleted=False))

            annotated = False
            for annotation in annotations:
                if annotation.width != image.width \
                        or annotation.height != image.height:
                    # cannot copy annotations from differently sized images
                    continue

                annotation_exists = False
                for existing in existing_annotations:
                    if annotation.category_id == existing.category_id \
                            and annotation.area == existing.area:
                        # if IOU matches, then we already have this annotation
                        if coco_util.get_annotations_iou(annotation, existing) == 1:
                            annotation_exists = True
                            break

                if annotation_exists:
                    continue

                # make sure the category is added to image
                if annotation.category_id not in dataset_categories:
                    image_categories = image.category_ids
                    dataset_categories.append(annotation.category_id)
                    image_categories = image.category_ids
                    dataset.update(set__categories=dataset_categories)
                    image_categories = image.category_ids
                
                if annotation.category_id not in image_categories:
                    image_categories.append(annotation.category_id)

                new_annotation = AnnotationModel(
                    image_id=image_id, category_id=annotation.category_id, metadata=annotation.metadata)
                new_annotation.dataset_id = image.dataset_id
                new_annotation.width = image.width
                new_annotation.height = image.height
                new_annotation.color = annotation.color
                new_annotation.bbox = annotation.bbox
                new_annotation.area = annotation.area
                try:
                    new_annotation.compoundPath = annotation.compoundPath
                except AttributeError:
                    pass
                try:
                    new_annotation.paper_object = annotation.paper_object
                except AttributeError:
                    pass
                try:
                    new_annotation.segmentation = annotation.segmentation
                except AttributeError:
                    pass
                new_annotation.save()
                annotated = True
                existing_annotations.append(new_annotation)

            image.update(
                set__annotated=annotated,
                set__category_ids=image_categories
            )

    def get(self, image_id):
        """ Called when loading from the annotator client """
        image = ImageModel.objects(id=image_id).first()

        if image is None:
            return {'success': False}, 400

        dataset = DatasetModel.objects(id=image.dataset_id).first()
        categories = CategoryModel.objects(deleted=False).in_bulk(dataset.categories).items()

        # Get next and previous image
        images = list(ImageModel.objects(dataset_id=dataset.id, deleted=False).order_by('file_name').all())
        image_index = images.index(image)
        image_previous = None if image_index - 1 < 0 else images[image_index - 1].id
        image_next = None if image_index + 1 == len(images) else images[image_index + 1].id

        # Generate data about the image to return to client
        data = {
            'image': query_util.fix_ids(image),
            'categories': [],
            'dataset': query_util.fix_ids(dataset),
            'settings': []
        }

        data['image']['previous'] = image_previous
        data['image']['next'] = image_next

        for category in categories:
            category = query_util.fix_ids(category[1])

            category_id = category.get('id')
            annotations = AnnotationModel.objects(image_id=image_id, category_id=category_id, deleted=False).all()

            category['show'] = True
            category['visualize'] = False
            category['annotations'] = [] if annotations is None else query_util.fix_ids(annotations)
            data.get('categories').append(category)

        return data


