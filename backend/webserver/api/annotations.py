from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user

from database import AnnotationModel
from ..util import query_util

import datetime
import logging
logger = logging.getLogger('gunicorn.error')

api = Namespace('annotation', description='Annotation related operations')

create_annotation = reqparse.RequestParser()
create_annotation.add_argument(
    'image_id', type=int, required=True, location='json')
create_annotation.add_argument('category_id', type=int, location='json')
create_annotation.add_argument('isbbox', type=bool, location='json')
create_annotation.add_argument('metadata', type=dict, location='json')
create_annotation.add_argument('segmentation', type=list, location='json')
create_annotation.add_argument('keypoints', type=list, location='json')
create_annotation.add_argument('color', location='json')

update_annotation = reqparse.RequestParser()
update_annotation.add_argument('category_id', type=int, location='json')

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
        isbbox = args.get('isbbox')
        metadata = args.get('metadata', {})
        segmentation = args.get('segmentation', [])
        keypoints = args.get('keypoints', [])

        image = current_user.images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image id"}, 400
        
        logger.info(
            f'{current_user.username} has created an annotation for image {image_id} with {isbbox}')
        logger.info(
            f'{current_user.username} has created an annotation for image {image_id}')

        try:
            annotation = AnnotationModel(
                image_id=image_id,
                category_id=category_id,
                metadata=metadata,
                segmentation=segmentation,
                keypoints=keypoints,
                isbbox=isbbox
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

        return query_util.fix_ids(annotation)

    @login_required
    def delete(self, annotation_id):
        """ Deletes an annotation by ID """
        annotation = current_user.annotations.filter(id=annotation_id).first()

        if annotation is None:
            return {"message": "Invalid annotation id"}, 400

        image = current_user.images.filter(
            id=annotation.image_id, deleted=False).first()
        image.flag_thumbnail()

        annotation.update(set__deleted=True,
                          set__deleted_date=datetime.datetime.now())
        return {'success': True}

    @api.expect(update_annotation)
    @login_required
    def put(self, annotation_id):
        """ Updates an annotation by ID """
        annotation = current_user.annotations.filter(id=annotation_id).first()

        if annotation is None:
            return { "message": "Invalid annotation id" }, 400

        args = update_annotation.parse_args()

        new_category_id = args.get('category_id')
        annotation.update(category_id=new_category_id)
        logger.info(
            f'{current_user.username} has updated category for annotation (id: {annotation.id})'
        )
        newAnnotation = current_user.annotations.filter(id=annotation_id).first()
        return query_util.fix_ids(newAnnotation)

# @api.route('/<int:annotation_id>/mask')
# class AnnotationMask(Resource):
#     def get(self, annotation_id):
#         """ Returns the binary mask of an annotation """
#         return query_util.fix_ids(AnnotationModel.objects(id=annotation_id).first())
