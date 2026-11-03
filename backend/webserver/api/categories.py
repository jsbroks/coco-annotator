from flask_restx import Namespace, Resource, reqparse
from flask_login import login_required, current_user
from mongoengine.errors import NotUniqueError

from ..util.pagination_util import Pagination
from ..util import query_util
from database import CategoryModel, AnnotationModel

import datetime

api = Namespace('category', description='Category related operations')

create_category = reqparse.RequestParser()
create_category.add_argument('name', required=True, location='json')
create_category.add_argument('supercategory', location='json')
create_category.add_argument('supercategories', type=list, location='json',
                             help='Parent categories (a category can have several)')
create_category.add_argument('color', location='json')
create_category.add_argument('metadata', type=dict, location='json')
create_category.add_argument(
    'keypoint_edges', type=list, default=[], location='json')
create_category.add_argument(
    'keypoint_labels', type=list, default=[], location='json')
create_category.add_argument(
    'keypoint_colors', type=list, default=[], location='json')

update_category = reqparse.RequestParser()
update_category.add_argument('name', required=True, location='json')
update_category.add_argument('supercategory', location='json')
update_category.add_argument('supercategories', type=list, location='json')
update_category.add_argument('color', location='json')
update_category.add_argument('metadata', type=dict, location='json')
update_category.add_argument('keypoint_edges', type=list, location='json')
update_category.add_argument('keypoint_labels', type=list, location='json')
update_category.add_argument('keypoint_colors', type=list, location='json')

page_data = reqparse.RequestParser()
page_data.add_argument('page', default=1, type=int)
page_data.add_argument('limit', default=20, type=int)


@api.route('/')
class Category(Resource):

    @login_required
    def get(self):
        """ Returns all categories """
        return query_util.fix_ids(current_user.categories.all())

    @api.expect(create_category)
    @login_required
    def post(self):
        """ Creates a category """
        if not current_user.has_perm('create_categories'):
            return {'code': 'no_create_categories',
                    'message': 'You do not have permission to create categories'}, 403
        args = create_category.parse_args()
        name = args.get('name')
        parents = CategoryModel.parse_parents(
            args['supercategories'] if args.get('supercategories') is not None else args.get('supercategory'))
        metadata = args.get('metadata', {})
        color = args.get('color')
        keypoint_edges = args.get('keypoint_edges')
        keypoint_labels = args.get('keypoint_labels')
        keypoint_colors = args.get('keypoint_colors')

        # the same name in the creator's trash: bring that one back with the new settings
        # (the one under the same parent first)
        trashed_query = CategoryModel.objects(name=name, creator=current_user.username, deleted=True)
        trashed = trashed_query.filter(supercategory=parents[0] if parents else '').first() or trashed_query.first()
        if trashed is not None:
            update = {'set__deleted': False, 'unset__deleted_date': True, 'unset__deleted_by': True,
                      'unset__delete_batch': True, 'set__supercategory': parents[0] if parents else '',
                      'set__supercategories': parents}
            if color:
                update['set__color'] = color
            try:
                trashed.update(**update)
            except NotUniqueError:
                return {'code': 'exists', 'message': 'A category with this name already exists under this parent.'}, 400
            trashed.reload()
            from ..util import activity
            activity.record('restore', current_user, counts={'items': 1},
                            detail={'kind': 'category', 'name': trashed.name})
            return {**query_util.fix_ids(trashed), 'restored': True}

        try:
            category = CategoryModel(
                name=name,
                supercategory=parents[0] if parents else '',
                supercategories=parents,
                color=color,
                metadata=metadata,
                keypoint_edges=keypoint_edges,
                keypoint_labels=keypoint_labels,
                keypoint_colors=keypoint_colors,
            )
            category.save()
        except NotUniqueError as e:
            return {'code': 'exists', 'message': 'A category with this name already exists under this parent. If it '
                               'was deleted, restore or permanently delete it in the trash (activity log).'}, 400

        from ..util import activity
        activity.record('category_create', current_user, category_id=category.id,
                        detail={'name': category.name, 'color': category.color})
        return query_util.fix_ids(category)


@api.route('/<int:category_id>')
class Category(Resource):

    @login_required
    def get(self, category_id):
        """ Returns a category by ID """
        category = current_user.categories.filter(id=category_id).first()

        if category is None:
            return {'success': False}, 400

        return query_util.fix_ids(category)

    @login_required
    def delete(self, category_id):
        """ Deletes a category by ID """
        category = current_user.categories.filter(id=category_id).first()
        if category is None:
            return {"message": "Invalid image id"}, 400

        if not current_user.can_delete(category):
            return {"message": "You do not have permission to delete this category"}, 403

        from ..util.trash import soft_delete
        soft_delete(category, current_user)
        return {'success': True}

    @api.expect(update_category)
    @login_required
    def put(self, category_id):
        """ Updates a category name by ID """

        category = current_user.categories.filter(id=category_id).first()

        # check if the id exits
        if category is None:
            return {"message": "Invalid category id"}, 400

        # a category can be shared by several datasets: only its creator (or an
        # admin) may change it
        if not current_user.can_edit(category):
            return {"message": "Only the creator of this category (or someone who manages categories) can change it"}, 403

        args = update_category.parse_args()
        name = args.get('name')
        if args.get('supercategories') is not None:
            parents = CategoryModel.parse_parents(args['supercategories'])
        elif args.get('supercategory') is not None:
            parents = CategoryModel.parse_parents(args['supercategory'])
        else:
            parents = category.parents()
        supercategory = parents[0] if parents else ''
        color = args.get('color', category.color)
        metadata = args.get('metadata')
        if metadata is None:  # not sent: keep it
            metadata = category.metadata
        keypoint_edges = args.get('keypoint_edges', category.keypoint_edges)
        keypoint_labels = args.get('keypoint_labels', category.keypoint_labels)
        keypoint_colors = args.get('keypoint_colors', category.keypoint_colors)

        # check if there is anything to update
        if category.name == name \
                and category.parents() == parents \
                and category.color == color \
                and category.metadata == metadata \
                and category.keypoint_edges == keypoint_edges \
                and category.keypoint_labels == keypoint_labels \
                and category.keypoint_colors == keypoint_colors:
            return {"message": "Nothing to update"}, 200

        # check if the name is empty
        if not name:
            return {"message": "Invalid category name to update"}, 400

        old_name, old_color, old_parents = category.name, category.color, category.parents()
        # update name of the category
        # check if the name to update exits already in db
        # @ToDo: Is it necessary to allow equal category names among different creators?
        category.name = name
        category.supercategory = supercategory
        category.color = color
        category.keypoint_edges = keypoint_edges
        category.keypoint_labels = keypoint_labels
        category.keypoint_colors = keypoint_colors

        try:
            category.update(
                name=category.name,
                supercategory=category.supercategory,
                supercategories=parents,
                color=category.color,
                metadata=metadata,
                keypoint_edges=category.keypoint_edges,
                keypoint_labels=category.keypoint_labels,
                keypoint_colors=category.keypoint_colors,
            )
        except NotUniqueError:
            # it is only triggered when the name already exists and the creator is the same
            return {"message": f"Category '{name}' already exists"}, 400

        from ..util import activity
        activity.record('category_update', current_user, category_id=category.id,
                        detail={'name': name, 'old_name': old_name if old_name != name else None,
                                'color': color, 'old_color': old_color if old_color != color else None,
                                'parents': parents if parents != old_parents else None},
                        text=f"{name} {old_name}")
        return {"success": True}


@api.route('/data')
class CategoriesData(Resource):

    @api.expect(page_data)
    @login_required
    def get(self):
        """ Endpoint called by category viewer client """
        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']

        categories = current_user.categories.filter(deleted=False)

        pagination = Pagination(categories.count(), limit, page)
        categories = query_util.fix_ids(
            categories[pagination.start:pagination.end])

        for category in categories:
            category['numberAnnotations'] = AnnotationModel.objects(
                deleted=False, category_id=category.get('id')).count()

        return {
            "pagination": pagination.export(),
            "page": page,
            "categories": categories
        }
