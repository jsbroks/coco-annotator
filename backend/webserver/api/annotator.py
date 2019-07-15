import datetime

from flask_restplus import Namespace, Resource
from flask_login import login_required, current_user
from flask import request

from ..util import query_util, coco_util, profile

from config import Config
from database import (
    ImageModel,
    CategoryModel,
    AnnotationModel,
    SessionEvent
)

api = Namespace('annotator', description='Annotator related operations')


@api.route('/data')
class AnnotatorData(Resource):

    @profile
    @login_required
    def post(self):
        """
        Called when saving data from the annotator client
        """
        data = request.get_json(force=True)
        image = data.get('image')
        dataset = data.get('dataset')
        image_id = image.get('id')
        
        image_model = ImageModel.objects(id=image_id).first()

        if image_model is None:
            return {'success': False, 'message': 'Image does not exist'}, 400

        # Check if current user can access dataset
        db_dataset = current_user.datasets.filter(id=image_model.dataset_id).first()
        if dataset is None:
            return {'success': False, 'message': 'Could not find associated dataset'}
        
        db_dataset.update(annotate_url=dataset.get('annotate_url', ''))
        
        categories = CategoryModel.objects.all()
        annotations = AnnotationModel.objects(image_id=image_id)

        current_user.update(preferences=data.get('user', {}))

        annotated = False
        # Iterate every category passed in the data
        for category in data.get('categories', []):
            category_id = category.get('id')

            # Find corresponding category object in the database
            db_category = categories.filter(id=category_id).first()
            if db_category is None:
                continue

            category_update = {'color': category.get('color')}
            if current_user.can_edit(db_category):
                category_update['keypoint_edges'] = category.get('keypoint_edges', [])
                category_update['keypoint_labels'] = category.get('keypoint_labels', [])
            
            db_category.update(**category_update)

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
                sessions = []
                total_time = 0
                for session in annotation.get('sessions', []):
                    date = datetime.datetime.fromtimestamp(int(session.get('start')) / 1e3)
                    model = SessionEvent(
                        user=current_user.username,
                        created_at=date,
                        milliseconds=session.get('milliseconds'),
                        tools_used=session.get('tools')
                    )
                    total_time += session.get('milliseconds')
                    sessions.append(model)

                db_annotation.update(
                    add_to_set__events=sessions,
                    inc__milliseconds=total_time,
                    set__isbbox=annotation.get('isbbox', False),
                    set__keypoints=annotation.get('keypoints', []),
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
                        set__isbbox=annotation.get('isbbox', False),
                        set__bbox=bbox,
                        set__paper_object=paperjs_object,
                    )

                    if area > 0:
                        annotated = True

        image_model.update(
            set__metadata=image.get('metadata', {}),
            set__annotated=annotated,
            set__category_ids=image.get('category_ids', []),
            set__regenerate_thumbnail=annotated,
            set__num_annotations=annotations\
                .filter(deleted=False, area__gt=0).count()
        )

        return {"success": True}


@api.route('/data/<int:image_id>')
class AnnotatorId(Resource):

    @profile
    @login_required
    def get(self, image_id):
        """ Called when loading from the annotator client """
        image = ImageModel.objects(id=image_id)\
            .exclude('events').first()

        if image is None:
            return {'success': False, 'message': 'Could not load image'}, 400

        dataset = current_user.datasets.filter(id=image.dataset_id).first()
        if dataset is None:
            return {'success': False, 'message': 'Could not find associated dataset'}, 400

        categories = CategoryModel.objects(deleted=False)\
            .in_bulk(dataset.categories).items()

        # Get next and previous image
        images = ImageModel.objects(dataset_id=dataset.id, deleted=False)
        pre = images.filter(file_name__lt=image.file_name).order_by('-file_name').first()
        nex = images.filter(file_name__gt=image.file_name).order_by('file_name').first()

        preferences = {}
        if not Config.LOGIN_DISABLED:
            preferences = current_user.preferences

        # Generate data about the image to return to client
        data = {
            'image': query_util.fix_ids(image),
            'categories': [],
            'dataset': query_util.fix_ids(dataset),
            'preferences': preferences,
            'permissions': {
                'dataset': dataset.permissions(current_user),
                'image': image.permissions(current_user)
            }
        }

        data['image']['previous'] = pre.id if pre else None
        data['image']['next'] = nex.id if nex else None

        for category in categories:
            category = query_util.fix_ids(category[1])

            category_id = category.get('id')
            annotations = AnnotationModel.objects(image_id=image_id, category_id=category_id, deleted=False)\
                .exclude('events').all()

            category['show'] = True
            category['visualize'] = False
            category['annotations'] = [] if annotations is None else query_util.fix_ids(annotations)
            data.get('categories').append(category)

        return data


