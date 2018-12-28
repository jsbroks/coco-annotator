from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user

from ..models import AnnotationModel
from ..util import query_util, color_util

import datetime

api = Namespace('annotation', description='Annotation related operations')

create_annotation = reqparse.RequestParser()
create_annotation.add_argument('image_id', type=int, required=True, location='json')
create_annotation.add_argument('category_id', type=int, location='json')
create_annotation.add_argument('metadata', type=dict, location='json')
create_annotation.add_argument('color', location='json')


@api.route('/')
class Annotation(Resource):

    @login_required
    def get(self):
        """ Returns all annotations """
        return query_util.fix_ids(AnnotationModel.objects.exclude("paper_object").all())

    @api.expect(create_annotation)
    @login_required
    def post(self):
        """ Creates an annotation """
        args = create_annotation.parse_args()
        image_id = args.get('image_id')
        category_id = args.get('category_id')
        metadata = args.get('metadata', {})
        color = args.get('color')

        try:
            annotation = AnnotationModel(image_id=image_id, category_id=category_id, metadata=metadata)
            annotation.color = color_util.random_color_hex() if color is None else color
            annotation.save()
        except (ValueError, TypeError) as e:
            return {'message': str(e)}, 400

        return query_util.fix_ids(annotation)


@api.route('/<int:annotation_id>')
class AnnotationId(Resource):

    @login_required
    def get(self, annotation_id):
        """ Returns annotation by ID """
        annotation = AnnotationModel.objects(id=annotation_id).first()

        if annotation is None:
            return {"message": "Invalid annotation id"}, 400

        return query_util.fix_ids(annotation)

    @login_required
    def delete(self, annotation_id):
        """ Deletes an annotation by ID """
        annotation = AnnotationModel.objects(id=annotation_id).first()

        if annotation is None:
            return {"message": "Invalid annotation id"}, 400

        annotation.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
        return {'success': True}


# @api.route('/<int:annotation_id>/mask')
# class AnnotationMask(Resource):
#     def get(self, annotation_id):
#         """ Returns the binary mask of an annotation """
#         return query_util.fix_ids(AnnotationModel.objects(id=annotation_id).first())


