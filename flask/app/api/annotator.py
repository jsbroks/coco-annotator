from flask_restplus import Namespace, Api, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage
from flask import jsonify, send_file, request

import sys
from ..util import query_util
from ..util import coco_util
from ..models import *

import numpy as np


api = Namespace('annotator', description='Annotator related operations')


@api.route('/data')
class AnnotatorData(Resource):

    def post(self):
        """
        Called when saving data from the annotator client
        """
        data = request.get_json(force=True)
        image_id = data.get('image').get('id')

        image = ImageModel.objects(id=image_id).first()
        categories = CategoryModel.objects.all()
        annotations = AnnotationModel.objects(image_id=image_id)

        for category in data.get('categories', []):
            category_id = category.get('id')

            db_category = categories.filter(id=category_id).first()
            if db_category is None:
                continue

            for annotation in category.get('annotations', []):
                annotation_id = annotation.get('id')
                db_annotation = annotations.filter(id=annotation_id).first()
                if db_annotation is None:
                    continue

                paperjs_object = annotation.get('compoundPath', [])

                if len(paperjs_object) == 2:

                    width = db_annotation.width
                    height = db_annotation.height

                    segmentation, area, bbox = coco_util.\
                        paperjs_to_coco(width, height, paperjs_object)

                    db_annotation.update(
                        set__segmentation=segmentation,
                        set__area=area,
                        set__bbox=bbox,
                        set__paper_object=paperjs_object
                    )

        return data


@api.route('/data/<int:image_id>')
class AnnotatorId(Resource):

    def get(self, image_id):
        """ Called when loading from the annotator client """
        image = ImageModel.objects(id=image_id).first()

        if image is None:
            return {"message": "Image does not exist"}, 400

        dataset = DatasetModel.objects(id=image.dataset_id).first()
        categories = CategoryModel.objects(deleted=False).in_bulk(dataset.categories).items()

        data = {
            'image': query_util.fix_ids(image),
            'categories': [],
            'dataset': query_util.fix_ids(dataset),
            'settings': []
        }

        for category in categories:
            category = query_util.fix_ids(category[1])

            category_id = category.get('id')
            annotations = AnnotationModel.objects(image_id=image_id, category_id=category_id, deleted=False).all()

            category['show'] = True
            category['visualize'] = False
            category['annotations'] = [] if annotations is None else query_util.fix_ids(annotations)
            data.get('categories').append(category)

        return data


