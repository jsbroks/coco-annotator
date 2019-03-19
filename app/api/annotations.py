from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from imantics import Color

from ..models import AnnotationModel
from ..util import query_util

import datetime

api = Namespace('annotation', description='Annotation related operations')

create_annotation = reqparse.RequestParser()
create_annotation.add_argument('image_id', type=int, required=True, location='json')
create_annotation.add_argument('category_id', type=int, location='json')
create_annotation.add_argument('metadata', type=dict, location='json')
create_annotation.add_argument('segmentation', type=list, location='json')
create_annotation.add_argument('keypoints', type=list, location='json')
create_annotation.add_argument('color', location='json')


@api.route('/')
class Annotation(Resource):

    @login_required
    def get(self):
        """ Returns all annotations """
        return query_util.fix_ids(current_user.annotations.exclude("paper_object").all())

    @api.expect(create_annotation)
    @login_required
    def post(self):
        """ Creates an annotation """
        args = create_annotation.parse_args()
        image_id = args.get('image_id')
        category_id = args.get('category_id')
        metadata = args.get('metadata', {})
        segmentation = args.get('segmentation', [])
        keypoints = args.get('keypoints', [])
        color = args.get('color')

        image = current_user.images.filter(id=image_id, deleted=False).first()
        image.flag_thumbnail()

        try:
            annotation = AnnotationModel(
                image_id=image_id,
                category_id=category_id,
                metadata=metadata,
                segmentation=segmentation,
                keypoints=keypoints
            )
            annotation.save()
        except (ValueError, TypeError) as e:
            return {'message': str(e)}, 400

        return query_util.fix_ids(annotation)


@api.route('/<int:annotation_id>')
class AnnotationId(Resource):

    @login_required
    def get(self, annotation_id):
        """ Returns annotation by ID """
        annotation = current_user.annotations.filter(id=annotation_id).first()

        if annotation is None:
            return {"message": "Invalid annotation id"}, 400

        image = current_user.images.filter(id=annotation.image_id, deleted=False).first()

        return query_util.fix_ids(annotation)

    @login_required
    def delete(self, annotation_id):
        """ Deletes an annotation by ID """
        annotation = current_user.annotations.filter(id=annotation_id).first()

        if annotation is None:
            return {"message": "Invalid annotation id"}, 400

        image = current_user.images.filter(id=annotation.image_id, deleted=False).first()
        image.flag_thumbnail()

        annotation.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {'success': True}


# @api.route('/<int:annotation_id>/mask')
# class AnnotationMask(Resource):
#     def get(self, annotation_id):
#         """ Returns the binary mask of an annotation """
#         return query_util.fix_ids(AnnotationModel.objects(id=annotation_id).first())


