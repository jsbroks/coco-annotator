from flask import request
from flask_restx import Namespace, Resource, reqparse, inputs
from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
from mongoengine.errors import NotUniqueError
from mongoengine.queryset.visitor import Q

from ..util.pagination_util import Pagination
from ..util import query_util, coco_util, profile

from database import (
    ImageModel,
    DatasetModel,
    CategoryModel,
    CategoryCreateDenied,
    AnnotationModel,
    ExportModel,
    UserModel
)

import datetime
import json
import os

api = Namespace('dataset', description='Dataset related operations')


def _no_create_categories(name):
    return {'code': 'no_create_categories', 'name': name,
            'message': f'"{name}" is not a category yet, and you do not have permission to create categories'}, 403


dataset_create = reqparse.RequestParser()
DATASET_TASKS = ('', 'detect', 'segment', 'obb', 'pose', 'classify', 'semantic')

dataset_create.add_argument('name', required=True)
dataset_create.add_argument('task', location='json', default='', choices=DATASET_TASKS,
                            help='Planned task: detect, segment, obb, pose, classify, semantic')
dataset_create.add_argument('categories', type=list, required=False, location='json',
                            help="List of default categories for sub images")
dataset_create.add_argument('replace_trashed', type=bool, location='json', default=False,
                            help='A dataset of this name is in the trash: delete its records for good '
                                 '(the images in its folder are kept and scanned again) and create a new one')

page_data = reqparse.RequestParser()
page_data.add_argument('page', default=1, type=int)
page_data.add_argument('limit', default=20, type=int)
page_data.add_argument('folder', default='', help='Folder for data')
page_data.add_argument('order', default='file_name', help='Order to display images')
page_data.add_argument('parent', default='', help="Datasets page: only datasets with a category under this parent ('-' = none)")
page_data.add_argument('q', default='', help='Datasets page: search dataset names')

delete_data = reqparse.RequestParser()
delete_data.add_argument('fully', default=False, type=bool,
                         help="Fully delete dataset (no undo)")

coco_upload = reqparse.RequestParser()
coco_upload.add_argument('coco', location='files', type=FileStorage, required=True, help='Json coco')

export = reqparse.RequestParser()
export.add_argument('categories', type=str, default=None, required=False, help='Ids of categories to export')
export.add_argument('with_empty_images', type=inputs.boolean, default=False, required=False, help='Export with un-annotated images')
export.add_argument('format', default='coco', choices=('coco', 'yolo'), help='coco (JSON) or yolo (zip of label files)')
export.add_argument('yolo_task', default='detect', choices=('detect', 'segment', 'obb', 'pose', 'classify', 'semantic'),
                    help='YOLO task')
export.add_argument('with_images', type=inputs.boolean, default=False, help='Put the images in the export (COCO becomes a zip)')
export.add_argument('split', default='', help='train,val,test percentages, e.g. 80,10,10 (empty: no split)')
export.add_argument('seed', type=int, default=42, help='Random seed for the split')
export.add_argument('only_approved', type=inputs.boolean, default=False, help='Only images a reviewer approved')
export.add_argument('folder', default='', help='YOLO: folder in the zip that holds train / val / test (default: dataset name)')
export.add_argument('with_datasets', default='', help='Other dataset ids exported with this one into one file '
                                                     '(categories of the same name become one)')
export.add_argument('augment', default='', help='JSON: {"copies": 2, "ops": {"hflip": true, "rotate": 15, '
                                                '"scale": 0.7, "color": true, ...}} (training images only)')

video_upload = reqparse.RequestParser()
video_upload.add_argument('video', location='files', type=FileStorage, required=False,
                          help='Video file (or upload_id of a video sent to /dataset/video/stage)')
video_upload.add_argument('upload_id', location='form', default=None,
                          help='A video uploaded earlier with /dataset/video/stage')
video_upload.add_argument('every_seconds', location='form', type=float, default=1.0,
                          help='Save one frame every N seconds')
video_upload.add_argument('every_frames', location='form', type=int, default=None,
                          help='Save one frame every N video frames (instead of every_seconds)')
video_upload.add_argument('start_seconds', location='form', type=float, default=0.0,
                          help='Start of the part to use (seconds)')
video_upload.add_argument('end_seconds', location='form', type=float, default=None,
                          help='End of the part to use (seconds; the end of the video if empty)')
video_upload.add_argument('max_frames', location='form', type=int, default=1000,
                          help='Stop after this many frames')

yolo_upload = reqparse.RequestParser()
yolo_upload.add_argument('yolo', location='files', type=FileStorage, required=True,
                         help='Zip with YOLO label .txt files and data.yaml / classes.txt')
yolo_upload.add_argument('task', location='form', default='auto',
                         choices=('auto', 'detect', 'segment', 'obb', 'pose'), help='YOLO label type')

update_dataset = reqparse.RequestParser()
update_dataset.add_argument('categories', location='json', type=list, help="New list of categories")
update_dataset.add_argument('task', location='json', default=None, choices=DATASET_TASKS + (None,),
                            help='Planned task (owner only)')
update_dataset.add_argument('default_annotation_metadata', location='json', type=dict,
                            help="Default annotation metadata")                            


share = reqparse.RequestParser()
share.add_argument('users', location='json', type=list, default=[], help="List of users")


@api.route('/')
class Dataset(Resource):
    @login_required
    def get(self):
        """ Returns all datasets """
        return query_util.fix_ids(current_user.datasets.filter(deleted=False).all())

    @api.expect(dataset_create)
    @login_required
    def post(self):
        """ Creates a dataset """
        args = dataset_create.parse_args()
        name = (args['name'] or '').strip()
        categories = args.get('categories', [])

        # the name is also the dataset's folder under the datasets directory
        if not name or name in ('.', '..') or name.startswith('.') \
                or any(c in name for c in '/\\\0'):
            return {'message': 'Invalid dataset name (it cannot contain / or \\ or start with a dot)'}, 400

        existing = DatasetModel.objects(name=name).first()
        if existing is not None:
            if not existing.deleted:
                return {'code': 'exists', 'message': 'A dataset with this name already exists'}, 400
            if not existing.is_owner(current_user):
                return {'code': 'in_trash_other',
                        'message': "A deleted dataset of another user has this name (in their trash)"}, 409
            if not args.get('replace_trashed'):
                return {'code': 'in_trash', 'dataset_id': existing.id,
                        'images': ImageModel.objects(dataset_id=existing.id).count(),
                        'message': 'A deleted dataset with this name is in the trash'}, 409
            from ..util import activity
            from ..util.trash import purge_dataset
            activity.record('purge', current_user, counts={'items': 1},
                            detail={'kind': 'dataset', 'name': existing.name, 'kept_files': True})
            purge_dataset(existing, keep_files=True)

        try:
            category_ids = CategoryModel.bulk_create(categories, create=current_user.has_perm('create_categories'))
        except CategoryCreateDenied as e:
            return _no_create_categories(e.name)

        try:
            dataset = DatasetModel(name=name, categories=category_ids, task=args.get('task') or '')
            dataset.save()
        except NotUniqueError:
            return {'code': 'exists', 'message': 'A dataset with this name already exists'}, 400

        from ..util import activity
        activity.record('dataset_create', current_user, dataset_id=dataset.id,
                        counts={'categories': len(category_ids)},
                        detail={'name': dataset.name, 'task': dataset.task or None})
        result = query_util.fix_ids(dataset)
        # images already in the folder (e.g. kept from a deleted dataset) are added
        if args.get('replace_trashed') and any(
                f.lower().endswith(ImageModel.PATTERN) for _, _, files in os.walk(dataset.directory) for f in files):
            dataset.scan(user=current_user)
            result['scanned'] = True
        return result




@api.route('/<int:dataset_id>/users')
class DatasetMembers(Resource):

    @login_required
    def get(self, dataset_id):
        """ All users in the dataset """

        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        users = dataset.get_users()
        return query_util.fix_ids(users)


members_args = reqparse.RequestParser()
members_args.add_argument('add', location='json', type=list, default=[])
members_args.add_argument('remove', location='json', type=list, default=[])

candidates_args = reqparse.RequestParser()
candidates_args.add_argument('q', location='args', default='')


def _member_rows(dataset):
    reviewers = set(dataset.reviewers or [])
    rows = []
    for u in dataset.get_users().only('username', 'name', 'last_seen'):
        role = 'owner' if u.username == dataset.owner else ('reviewer' if u.username in reviewers else 'member')
        rows.append({'username': u.username, 'name': u.name or '', 'role': role,
                     'last_seen': u.last_seen.isoformat() + 'Z' if u.last_seen else None})
    order = {'owner': 0, 'reviewer': 1, 'member': 2}
    rows.sort(key=lambda r: (order[r['role']], r['username'].lower()))
    return rows


@api.route('/<int:dataset_id>/members')
class DatasetMemberList(Resource):

    @login_required
    def get(self, dataset_id):
        """ Members with their role, and whether I may invite / remove """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        return {'members': _member_rows(dataset), 'can_manage': dataset.can_share(current_user)}

    @api.expect(members_args)
    @login_required
    def post(self, dataset_id):
        """ Add and / or remove members (the owner only) """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        if not dataset.can_share(current_user):
            return {"message": "Only the owner can invite or remove members"}, 403
        args = members_args.parse_args()
        add = [u.strip() for u in (args.get('add') or []) if isinstance(u, str) and u.strip()]
        remove = {u for u in (args.get('remove') or []) if isinstance(u, str)}
        # usernames are matched without case (student IDs are typed either way)
        found = {u.username.lower(): u.username for u in
                 UserModel.objects(username__in=add).only('username')} if add else {}
        for u in add:
            if u.lower() not in found:
                hit = UserModel.objects(username__iexact=u).only('username').first()
                if hit is not None:
                    found[u.lower()] = hit.username
        unknown = [u for u in add if u.lower() not in found]
        if unknown:
            return {"message": "No such accounts: " + ", ".join(unknown), "unknown": unknown}, 400

        before = list(dataset.users or [])
        users = [u for u in before if u not in remove]
        added = []
        for u in add:
            name = found[u.lower()]
            if name != dataset.owner and name not in users:
                users.append(name)
                added.append(name)
        removed = sorted(set(before) - set(users))
        reviewers = [r for r in (dataset.reviewers or []) if r in users or r == dataset.owner]
        dataset.update(users=users, reviewers=reviewers)
        if added or removed:
            from ..util import activity
            activity.record('dataset_share', current_user, dataset_id=dataset.id,
                            detail={'added': sorted(added), 'removed': removed},
                            text=" ".join(sorted(added) + removed))
        dataset.reload()
        return {'members': _member_rows(dataset), 'added': added, 'removed': removed}


@api.route('/<int:dataset_id>/candidates')
class DatasetCandidates(Resource):

    @api.expect(candidates_args)
    @login_required
    def get(self, dataset_id):
        """ Accounts the owner can invite (username or name contains q) """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        if not dataset.can_share(current_user):
            return {"message": "Only the owner can invite members"}, 403
        q = (candidates_args.parse_args().get('q') or '').strip()
        taken = set(dataset.users or []) | {dataset.owner}
        query = UserModel.objects(username__nin=list(taken))
        if q:
            query = query.filter(Q(username__icontains=q) | Q(name__icontains=q))
        rows = query.only('username', 'name').order_by('username').limit(20)
        return {'users': [{'username': u.username, 'name': u.name or ''} for u in rows]}


@api.route('/<int:dataset_id>/reset/metadata')
class DatasetCleanMeta(Resource):

    @login_required
    def get(self, dataset_id):
        """ All users in the dataset """

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        AnnotationModel.objects(dataset_id=dataset.id)\
            .update(metadata=dataset.default_annotation_metadata)
        ImageModel.objects(dataset_id=dataset.id)\
            .update(metadata={})

        return {'success': True}


def _exportable(exclude=None):
    """The user's datasets they may export, with image counts and categories."""
    out = []
    query = current_user.datasets.filter(deleted=False)
    if exclude is not None:
        query = query.filter(id__ne=exclude)
    for other in query.order_by('name'):
        if not current_user.can_download(other):
            continue
        # in the dataset's order (the export's default class order)
        cats = {c['id']: c for c in query_util.fix_ids(CategoryModel.objects(id__in=other.categories or [], deleted=False))}
        images = ImageModel.objects(dataset_id=other.id, deleted=False)
        first = images.order_by('file_name').only('file_name').first()
        out.append({
            'id': other.id, 'name': other.name, 'task': other.task or '',
            'images': images.count(),
            'sample': first.file_name if first else None,
            'categories': [cats[i] for i in (other.categories or []) if i in cats],
        })
    return out


@api.route('/exportable')
class DatasetsExportable(Resource):

    @login_required
    def get(self):
        """ Datasets the user may export (the datasets page picks several to
        export into one file) """
        return {'datasets': _exportable()}


@api.route('/<int:dataset_id>/merge_candidates')
class DatasetMergeCandidates(Resource):

    @login_required
    def get(self, dataset_id):
        """ Other datasets that can be exported together with this one, with
        their categories (the export dialog merges them by name) """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        return {'datasets': _exportable(exclude=dataset.id)}


@api.route('/<int:dataset_id>/category_counts')
class DatasetCategoryCounts(Resource):

    @login_required
    def get(self, dataset_id):
        """ Per category: annotations, images, and how many are boxes, rotated
        boxes, polygons or have keypoints; plus the categories of each
        annotated image and the image total (for the export dialog) """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        image_rows = list(ImageModel.objects(dataset_id=dataset.id, deleted=False)
                          .only('id', 'image_class').as_pymongo())
        image_ids = [i['_id'] for i in image_rows]
        explicit = {i['_id']: i['image_class'] for i in image_rows if i.get('image_class') is not None}
        counts = {}
        images = {}
        rows = AnnotationModel.objects(image_id__in=image_ids, deleted=False) \
            .only('category_id', 'image_id', 'segmentation', 'keypoints', 'isbbox', 'isrbbox').as_pymongo()
        for a in rows:
            has_shape = bool(a.get('segmentation'))
            has_keypoints = any(v > 0 for v in (a.get('keypoints') or [])[2::3])
            if not has_shape and not has_keypoints:
                continue  # empty annotations are not exported
            c = counts.setdefault(a['category_id'], {
                'annotations': 0, 'images': 0, 'boxes': 0, 'rotated': 0, 'polygons': 0, 'keypoints': 0})
            c['annotations'] += 1
            if a.get('isrbbox'):
                c['rotated'] += 1
            elif a.get('isbbox'):
                c['boxes'] += 1
            elif has_shape:
                c['polygons'] += 1
            if has_keypoints:
                c['keypoints'] += 1
            images.setdefault(a['category_id'], set()).add(a['image_id'])
        empty = {'annotations': 0, 'images': 0, 'boxes': 0, 'rotated': 0, 'polygons': 0, 'keypoints': 0}
        per_image = {}
        for category_id, ids in images.items():
            counts[category_id]['images'] = len(ids)
            for image_id in ids:
                per_image.setdefault(image_id, []).append(category_id)
        # whole-image classes (image classification)
        for category_id in explicit.values():
            c = counts.setdefault(category_id, dict(empty))
            c['classified'] = c.get('classified', 0) + 1
        return {
            'categories': {str(k): v for k, v in counts.items()},
            # categories of each annotated image (to estimate split sizes)
            'image_categories': list(per_image.values()),
            # classify estimate: whole-image class of each classified image, and
            # the annotation categories of the images without one
            'image_classes': list(explicit.values()),
            'unclassified_image_categories': [cats for i, cats in per_image.items() if i not in explicit],
            'total_images': len(image_ids),
        }


@api.route('/<int:dataset_id>/health')
class DatasetHealth(Resource):

    @login_required
    def get(self, dataset_id):
        """ Class balance, distributions and likely labelling problems """
        from ..util.health import dataset_health
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        return dataset_health(dataset)


@api.route('/<int:dataset_id>/stats')
class DatasetStats(Resource):

    @login_required
    def get(self, dataset_id):
        """ All users in the dataset """

        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        images = ImageModel.objects(dataset_id=dataset.id, deleted=False)
        annotated_images = images.filter(annotated=True)
        annotations = AnnotationModel.objects(dataset_id=dataset_id, deleted=False)

        # Calculate annotation counts by category in this dataset
        category_count = dict()
        image_category_count = dict()



        user_stats, sources = _annotation_sources(dataset)

        names = {c.id: c.name for c in CategoryModel.objects(id__in=list(dataset.categories)).only('id', 'name')}
        for category in dataset.categories:
            if category not in names:
                continue  # permanently deleted since

            # Calculate the annotation count in the current category in this dataset
            cat_name = names[category]
            cat_count = AnnotationModel.objects(dataset_id=dataset_id, category_id=category, deleted=False).count()
            category_count.update({str(cat_name): cat_count})

            # Calculate the annotated images count in the current category in this dataset
            image_count = len(AnnotationModel.objects(dataset_id=dataset_id, category_id=category, deleted=False).distinct('image_id'))
            image_category_count.update({str(cat_name): image_count})

        stats = {
            'total': {
                'Users': dataset.get_users().count(),
                'Images': images.count(),
                'Annotated Images': annotated_images.count(),
                'Annotations': annotations.count(),
                'Categories': len(dataset.categories),
                'Time Annotating (s)': (images.sum('milliseconds') or 0) / 1000
            },
            'average': {
                'Image Size (px)': images.average('width'),
                'Image Height (px)': images.average('height'),
                'Annotation Area (px)': annotations.average('area'),
                'Time (ms) per Image': images.average('milliseconds') or 0,
                'Time (ms) per Annotation': annotations.average('milliseconds') or 0
            },
            'categories': category_count,
            'images_per_category': image_category_count,
            'users': user_stats,
            'time': _time_per_member(images),
            # annotations not drawn by a member: model runs and imports
            'sources': sources
        }
        return stats


def _time_per_member(images, recent_days=7):
    """Time each person had the dataset's images open in the annotator:
    {username: {seconds, recent_seconds, images, last}}"""
    since = datetime.datetime.utcnow() - datetime.timedelta(days=recent_days)
    out = {}
    for row in images.only('id', 'events').as_pymongo():
        for e in row.get('events') or []:
            user = e.get('user')
            if not user or 'milliseconds' not in e:
                continue
            t = out.setdefault(user, {'ms': 0, 'recent_ms': 0, 'images': set(), 'last': None})
            ms = e.get('milliseconds') or 0
            t['ms'] += ms
            t['images'].add(row['_id'])
            at = e.get('created_at')
            if at is not None:
                if at >= since:
                    t['recent_ms'] += ms
                if t['last'] is None or at > t['last']:
                    t['last'] = at
    return {user: {'seconds': t['ms'] / 1000, 'recent_seconds': t['recent_ms'] / 1000,
                   'images': len(t['images']),
                   'last': t['last'].isoformat() + 'Z' if t['last'] else None}
            for user, t in out.items()}


def _mark_sources(dataset_id):
    from ..util.activity import mark_sources
    mark_sources(dataset_id)


def _annotation_sources(dataset):
    """Annotations per member (drawn by hand), per model, and imported."""
    live = AnnotationModel.objects(dataset_id=dataset.id, deleted=False)
    _mark_sources(dataset.id)

    def summary(query):
        return {'annotations': query.count(), 'images': len(query.distinct('image_id'))}

    members = [u.username for u in dataset.get_users()]
    by_hand = live.filter(source__nin=['model', 'import'])
    users = {name: summary(by_hand.filter(creator=name)) for name in members}

    sources = []
    models = live.filter(source='model')
    for name in sorted(n for n in models.distinct('model') if n) + [None]:
        query = models.filter(model=name) if name else models.filter(model__exists=False)
        if query.count():
            sources.append({'kind': 'model', 'name': name, **summary(query),
                            'by': sorted(c for c in query.distinct('creator') if c and c != 'system')})
    imported = live.filter(Q(source='import') | (Q(source__nin=['model', 'import']) & Q(creator__nin=members)))
    if imported.count():
        sources.append({'kind': 'import', 'name': None, **summary(imported)})
    return users, sources


@api.route('/<int:dataset_id>')
class DatasetId(Resource):

    @login_required
    def delete(self, dataset_id):
        """ Deletes dataset by ID (only owners)"""

        dataset = DatasetModel.objects(id=dataset_id, deleted=False).first()

        if dataset is None:
            return {"message": "Invalid dataset id"}, 400
        
        if not current_user.can_delete(dataset):
            return {"message": "You do not have permission to delete the dataset"}, 403

        from ..util.trash import soft_delete
        soft_delete(dataset, current_user)
        return {"success": True}

    @api.expect(update_dataset)
    @login_required
    def post(self, dataset_id):

        """ Updates dataset by ID """

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        args = update_dataset.parse_args()
        categories = args.get('categories')
        before = {'task': dataset.task or '', 'categories': list(dataset.categories or [])}
        if args.get('task') is not None:
            if not dataset.is_owner(current_user):
                return {"message": "Only the owner can change the planned task"}, 403
            dataset.update(set__task=args['task'])
        default_annotation_metadata = args.get('default_annotation_metadata')
        set_default_annotation_metadata = args.get('set_default_annotation_metadata')

        if categories is not None:
            try:
                dataset.categories = CategoryModel.bulk_create(
                    categories, create=current_user.has_perm('create_categories'))
            except CategoryCreateDenied as e:
                return _no_create_categories(e.name)

        if default_annotation_metadata is not None:

            update = {}
            for key, value in default_annotation_metadata.items():
                if key not in dataset.default_annotation_metadata:
                    update[f'set__metadata__{key}'] = value

            dataset.default_annotation_metadata = default_annotation_metadata
            
            if len(update.keys()) > 0:
                AnnotationModel.objects(dataset_id=dataset.id, deleted=False)\
                    .update(**update)

        dataset.update(
            categories=dataset.categories,
            default_annotation_metadata=dataset.default_annotation_metadata
        )

        changes = {}
        if args.get('task') is not None and args['task'] != before['task']:
            changes['task'] = args['task'] or None
            changes['old_task'] = before['task'] or None
        if categories is not None:
            added = [c for c in dataset.categories if c not in before['categories']]
            removed = [c for c in before['categories'] if c not in dataset.categories]
            names = {c.id: c.name for c in CategoryModel.objects(id__in=added + removed).only('id', 'name')}
            if added:
                changes['categories_added'] = [names.get(c, '?') for c in added]
            if removed:
                changes['categories_removed'] = [names.get(c, '?') for c in removed]
        if default_annotation_metadata is not None:
            changes['metadata'] = True
        if changes:
            from ..util import activity
            activity.record('dataset_update', current_user, dataset_id=dataset.id, detail=changes,
                            text=" ".join(changes.get('categories_added', []) + changes.get('categories_removed', [])))

        return {"success": True}


@api.route('/<int:dataset_id>/share')
class DatasetIdShare(Resource):
    @api.expect(share)
    @login_required
    def post(self, dataset_id):
        args = share.parse_args()

        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset id"}, 400

        if not dataset.is_owner(current_user):
            return {"message": "You do not have permission to share this dataset"}, 403

        users = [u for u in (args.get('users') or []) if isinstance(u, str) and u]
        known = {u.username for u in UserModel.objects(username__in=users).only('username')}
        unknown = [u for u in users if u not in known]
        if unknown:
            return {"message": "No such accounts: " + ", ".join(unknown), "unknown": unknown}, 400
        before = set(dataset.users or [])
        after = set(users)
        # someone taken off the dataset is no longer one of its reviewers either
        reviewers = [r for r in (dataset.reviewers or []) if r in after or r == dataset.owner]
        dataset.update(users=users, reviewers=reviewers)
        if before != after:
            from ..util import activity
            activity.record('dataset_share', current_user, dataset_id=dataset.id,
                            detail={'added': sorted(after - before), 'removed': sorted(before - after)},
                            text=" ".join(sorted(after ^ before)))

        return {"success": True}


@api.route('/data')
class DatasetData(Resource):
    @api.expect(page_data)
    @login_required
    def get(self):
        """ Endpoint called by dataset viewer client """

        args = page_data.parse_args()
        limit = args['limit']
        page = args['page']
        folder = args['folder']

        datasets = list(current_user.datasets.filter(deleted=False).order_by('id'))

        # parent categories of each dataset's categories (for the tabs)
        category_ids = {c for d in datasets for c in (d.categories or [])}
        parents_of = {c.id: c.parents() for c in CategoryModel.objects(id__in=list(category_ids))
                      .only('id', 'supercategory', 'supercategories')}
        # a parent path counts for each of its levels ("Vehicles" and "Vehicles/Land")
        dataset_parents = {d.id: sorted({a for c in (d.categories or []) for p in parents_of.get(c, [])
                                         for a in CategoryModel.ancestors(p)})
                           for d in datasets}
        names = [d.name for d in datasets]
        q = (args.get('q') or '').strip().lower()
        if q:
            datasets = [d for d in datasets if q in d.name.lower()]
        parent_counts = {}
        for d in datasets:
            for p in dataset_parents[d.id]:
                parent_counts[p] = parent_counts.get(p, 0) + 1
        no_parent = sum(1 for d in datasets if not dataset_parents[d.id])
        total_shown = len(datasets)

        parent = args.get('parent') or ''
        if parent == '-':
            datasets = [d for d in datasets if not dataset_parents[d.id]]
        elif parent:
            datasets = [d for d in datasets if parent in dataset_parents[d.id]]

        pagination = Pagination(len(datasets), limit, page)
        datasets = datasets[pagination.start:pagination.end]

        datasets_json = []
        for dataset in datasets:
            dataset_json = query_util.fix_ids(dataset)
            images = ImageModel.objects(dataset_id=dataset.id, deleted=False)

            dataset_json['numberImages'] = images.count()
            dataset_json['numberAnnotated'] = images.filter(annotated=True).count()
            # the same statuses as the dataset's progress bar
            status_counts = {s: 0 for s in ImageModel.STATUSES}
            for row in images.aggregate([{'$group': {'_id': '$status', 'n': {'$sum': 1}}}]):
                key = row['_id'] or 'unlabeled'
                status_counts[key] = status_counts.get(key, 0) + row['n']
            dataset_json['statusCounts'] = status_counts
            dataset_json['permissions'] = dataset.permissions(current_user)
            dataset_json['parents'] = dataset_parents[dataset.id]

            first = images.first()
            if first is not None:
                dataset_json['first_image_id'] = images.first().id
            datasets_json.append(dataset_json)

        return {
            "pagination": pagination.export(),
            "folder": folder,
            "datasets": datasets_json,
            "categories": query_util.fix_ids(current_user.categories.filter(deleted=False).all()),
            "parents": [{"name": n, "count": parent_counts[n]} for n in sorted(parent_counts)],
            "no_parent": no_parent,
            "total": total_shown,
            "names": names,
            # deleted datasets the user could restore or replace: name -> images
            "trashed": _trashed_datasets(current_user),
        }


def _trashed_datasets(user):
    """Deleted datasets the user owns (all of them for an admin), with their
    image counts from one aggregation instead of a count per dataset."""
    trashed = DatasetModel.objects(deleted=True).only('id', 'name', 'owner')
    if not user.is_admin:
        trashed = trashed.filter(owner__iexact=user.username)
    trashed = list(trashed)
    if not trashed:
        return []
    counts = {row['_id']: row['n'] for row in ImageModel.objects(dataset_id__in=[d.id for d in trashed])
              .aggregate([{'$group': {'_id': '$dataset_id', 'n': {'$sum': 1}}}])}
    return [{"id": d.id, "name": d.name, "images": counts.get(d.id, 0)} for d in trashed]

@api.route('/<int:dataset_id>/data')
class DatasetDataId(Resource):

    @profile
    @api.expect(page_data)
    @login_required
    def get(self, dataset_id):
        """ Endpoint called by image viewer client """

        parsed_args = page_data.parse_args()
        per_page = parsed_args.get('limit')
        page = parsed_args.get('page') - 1
        folder = parsed_args.get('folder')
        order = parsed_args.get('order')

        args = dict(request.args)

        # Check if dataset exists
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
                
        # Make sure folder starts with is in proper format
        if len(folder) > 0:
            folder = folder[0].strip('/') + folder[1:]
            if folder[-1] != '/':
                folder = folder + '/'

        # Get directory
        directory = os.path.join(dataset.directory, folder)
        if not os.path.exists(directory):
            return {'message': 'Directory does not exist.'}, 400

        # Remove parsed arguments
        for key in parsed_args:
            args.pop(key, None)
        
        # Generate query from remaining arugments
        query = {}
        for key, value in args.items():
            lower = value.lower()
            if lower in ["true", "false"]:
                value = json.loads(lower)
            
            if len(lower) != 0:
                query[key] = value

        # review workflow filters: assignee=me / none / <username>, status=<status>
        assignee = query.pop('assignee', None)
        status = query.pop('status', None)
        image_class = query.pop('image_class', None)

        # Change category_ids__in to list
        if 'category_ids__in' in query.keys():
            query['category_ids__in'] = [int(x) for x in query['category_ids__in'].split(',')]

        # Initialize mongo query with required elements:
        query_build = Q(dataset_id=dataset_id)
        query_build &= Q(path__startswith=directory)
        query_build &= Q(deleted=False)

        # Define query names that should use complex logic:
        complex_query = ['annotated', 'category_ids__in']

        # Add additional 'and' arguments to mongo query that do not require complex_query logic
        for key in query.keys():
            if key not in complex_query:
                query_dict = {}
                query_dict[key] = query[key]
                query_build &= Q(**query_dict)

        # Add additional arguments to mongo query that require more complex logic to construct
        if 'annotated' in query.keys():

            if 'category_ids__in' in query.keys() and query['annotated']:

                # Only show annotated images with selected category_ids
                query_dict = {}
                query_dict['category_ids__in'] = query['category_ids__in']
                query_build &= Q(**query_dict)

            else:

                # Only show non-annotated images
                query_dict = {}
                query_dict['annotated'] = query['annotated']
                query_build &= Q(**query_dict)

        elif 'category_ids__in' in query.keys():

            # Ahow annotated images with selected category_ids or non-annotated images
            query_dict_1 = {}
            query_dict_1['category_ids__in'] = query['category_ids__in']

            query_dict_2 = {}
            query_dict_2['annotated'] = False
            query_build &= (Q(**query_dict_1) | Q(**query_dict_2))

        if assignee == 'me':
            query_build &= Q(assignee=current_user.username)
        elif assignee == 'none':
            query_build &= (Q(assignee=None) | Q(assignee=''))
        elif assignee:
            query_build &= Q(assignee=str(assignee))
        if image_class == 'none':
            query_build &= Q(image_class=None)
        elif image_class not in (None, ''):
            query_build &= Q(image_class=int(image_class))
        if status == 'annotated':
            # has any annotation, whatever its review status
            query_build &= Q(annotated=True)
        elif status == 'ai':
            # has annotations a model made (still there, maybe edited since)
            _mark_sources(dataset_id)
            ai_images = AnnotationModel.objects(dataset_id=dataset_id, deleted=False, source='model').distinct('image_id')
            query_build &= Q(id__in=ai_images)
        elif status == 'unlabeled':
            query_build &= (Q(status=None) | Q(status='unlabeled'))
        elif status in ImageModel.STATUSES:
            query_build &= Q(status=status)

        # Perform mongodb query
        images = current_user.images \
            .filter(query_build) \
            .order_by(order).only('id', 'file_name', 'annotating', 'annotated', 'num_annotations',
                                  'status', 'assignee', 'review_note', 'image_class')
        
        total = images.count()
        pages = int(total/per_page) + 1
        
        images = images.skip(page*per_page).limit(per_page)
        images_json = query_util.fix_ids(images)
        # which of these have model-made annotations (an "AI" tag on the card)
        ai_ids = set(AnnotationModel.objects(image_id__in=[i['id'] for i in images_json], deleted=False,
                                             source='model').distinct('image_id'))
        for image_json in images_json:
            image_json['ai'] = image_json['id'] in ai_ids
        # for image in images:
        #     image_json = query_util.fix_ids(image)

        #     query = AnnotationModel.objects(image_id=image.id, deleted=False)
        #     category_ids = query.distinct('category_id')
        #     categories = CategoryModel.objects(id__in=category_ids).only('name', 'color')

        #     image_json['annotations'] = query.count()
        #     image_json['categories'] = query_util.fix_ids(categories)

        #     images_json.append(image_json)


        subdirectories = [f for f in sorted(os.listdir(directory))
                          if os.path.isdir(directory + f) and not f.startswith('.')]
        
        categories = CategoryModel.objects(id__in=dataset.categories).only('id', 'name', 'color')

        return {
            "total": total,
            "per_page": per_page,
            "pages": pages,
            "page": page,
            "images": images_json,
            "folder": folder,
            "directory": directory,
            "dataset": query_util.fix_ids(dataset),
            "categories": query_util.fix_ids(categories),
            "subdirectories": subdirectories
        }


@api.route('/<int:dataset_id>/exports')
class DatasetExports(Resource):

    @login_required
    def get(self, dataset_id):
        """ Returns exports of images and annotations in the dataset (only owners) """
        dataset = current_user.datasets.filter(id=dataset_id).first()

        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        
        if not current_user.can_download(dataset):
            return {"message": "You do not have permission to download the dataset's annotations"}, 403
        
        # merged exports show up in each of their datasets (for those who may
        # export all of them)
        exports = ExportModel.objects(Q(dataset_id=dataset.id) | Q(dataset_ids=dataset.id)) \
            .order_by('-created_at').limit(50)

        from .exports import export_dataset
        dict_export = []
        for export in exports:
            if getattr(export, 'dataset_ids', None) and export_dataset(export) is None:
                continue

            time_delta = datetime.datetime.utcnow() - export.created_at
            tags = list(export.tags or [])
            # tags: ["COCO", *categories] or ["YOLO", task, *categories]
            if tags[:1] == ["YOLO"]:
                fmt, task, names = "YOLO", (tags[1] if len(tags) > 1 else ""), tags[2:]
            else:
                fmt, task, names = "COCO", "", tags[1:] if tags[:1] == ["COCO"] else tags
            exists = bool(export.path) and os.path.isfile(export.path)
            dict_export.append({
                'id': export.id,
                'ago': query_util.td_format(time_delta),
                'tags': tags,
                'format': fmt,
                'yolo_task': task,
                'categories': names,
                'created_at': export.created_at.replace(microsecond=0).isoformat() + 'Z',
                'size': os.path.getsize(export.path) if exists else None,
                'split': getattr(export, 'split', None),
                'split_counts': getattr(export, 'split_counts', None),
                'seed': getattr(export, 'seed', None),
                'prefix_dataset': bool(getattr(export, 'prefix_dataset', False)),
                'folder': getattr(export, 'folder', None),
                'only_approved': bool(getattr(export, 'only_approved', False)),
                'augment': getattr(export, 'augment', None),
                'merged': list(getattr(export, 'dataset_names', None) or []) or None,
                'exists': exists,
            })

        return dict_export


@api.route('/<int:dataset_id>/export')
class DatasetExport(Resource):

    @api.expect(export)
    @login_required
    def get(self, dataset_id):

        args = export.parse_args()
        categories = args.get('categories') or ''
        with_empty_images = args.get('with_empty_images', False)
        
        if len(categories) == 0:
            categories = []

        if len(categories) > 0 or isinstance(categories, str):
            categories = [int(c) for c in categories.split(',')]

        dataset = current_user.datasets.filter(id=dataset_id).first()

        if not dataset:
            return {'message': 'Invalid dataset ID'}, 400

        if not current_user.can_download(dataset):
            return {"message": "You do not have permission to download the dataset's annotations"}, 403

        from geometry.yolo_format import parse_split
        try:
            split = parse_split(args.get('split'))
        except ValueError as e:
            return {'message': str(e)}, 400

        # other datasets merged into this export: each must be one the user may export
        merge = []
        for part in str(args.get('with_datasets') or '').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                other_id = int(part)
            except ValueError:
                return {'message': 'with_datasets must be dataset ids'}, 400
            if other_id == dataset.id or other_id in merge:
                continue
            other = current_user.datasets.filter(id=other_id, deleted=False).first()
            if other is None or not current_user.can_download(other):
                return {'message': f'You can not export dataset {other_id}'}, 403
            merge.append(other_id)
        if merge and categories:
            allowed = set(dataset.categories or [])
            for other in DatasetModel.objects(id__in=merge).only('categories'):
                allowed |= set(other.categories or [])
            categories = [c for c in categories if c in allowed]
            if not categories:
                return {'message': 'None of these categories belong to the datasets'}, 400

        augment = None
        if args.get('augment'):
            from geometry.augment import parse_options
            try:
                augment = parse_options(json.loads(args['augment']))
            except ValueError:
                return {'message': 'augment must be JSON'}, 400

        return dataset.export_coco(categories=categories, with_empty_images=with_empty_images,
                                   split=split, seed=args.get('seed') if args.get('seed') is not None else 42,
                                   fmt=args.get('format') or 'coco',
                                   yolo_task=args.get('yolo_task') or 'detect',
                                   with_images=bool(args.get('with_images')),
                                   folder=args.get('folder') or None,
                                   only_approved=bool(args.get('only_approved')),
                                   augment=augment,
                                   user=current_user,
                                   merge=merge)
    
    @api.expect(coco_upload)
    @login_required
    def post(self, dataset_id):
        """ Adds coco formatted annotations to the dataset """
        args = coco_upload.parse_args()
        coco = args['coco']

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400

        return dataset.import_coco(json.load(coco), user=current_user,
                                   create_categories=current_user.has_perm('create_categories'))


@api.route('/<int:dataset_id>/coco')
class DatasetCoco(Resource):

    @login_required
    def get(self, dataset_id):
        """ Returns coco of images and annotations in the dataset (only owners) """
        dataset = current_user.datasets.filter(id=dataset_id).first()

        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        
        if not current_user.can_download(dataset):
            return {"message": "You do not have permission to download the dataset's annotations"}, 403

        return coco_util.get_dataset_coco(dataset)

    @api.expect(coco_upload)
    @login_required
    def post(self, dataset_id):
        """ Adds coco formatted annotations to the dataset """
        args = coco_upload.parse_args()
        coco = args['coco']

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400

        return dataset.import_coco(json.load(coco), user=current_user,
                                   create_categories=current_user.has_perm('create_categories'))



@api.route('/<int:dataset_id>/yolo')
class DatasetYolo(Resource):

    @api.expect(yolo_upload)
    @login_required
    def post(self, dataset_id):
        """ Adds YOLO labels (zip) to the dataset, matching images by file name """
        import zipfile
        from geometry.yolo_format import read_zip, yolo_to_coco

        args = yolo_upload.parse_args()
        dataset = current_user.datasets.filter(id=dataset_id).first()
        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400
        if not current_user.can_edit(dataset):
            return {'message': 'You do not have permission to edit this dataset'}, 403

        try:
            label_texts, names, kpt_shape = read_zip(args['yolo'].stream)
        except zipfile.BadZipFile:
            return {'message': 'Not a zip file'}, 400
        if not label_texts:
            return {'message': 'No YOLO label (.txt) files found in the zip'}, 400

        images = [{"id": i.id, "file_name": i.file_name, "width": i.width, "height": i.height}
                  for i in ImageModel.objects(dataset_id=dataset.id, deleted=False)
                  .only('id', 'file_name', 'width', 'height')]
        try:
            from geometry.yolo_format import safe_prefix
            coco, stats = yolo_to_coco(label_texts, images, names=names,
                                       task=args.get('task'), kpt_shape=kpt_shape,
                                       prefixes=[safe_prefix(dataset.name)])
        except ValueError as e:
            return {'message': str(e)}, 400

        if stats['matched'] == 0:
            return {'message': 'None of the label files match an image in this dataset '
                               '(labels are matched to images by file name without the extension)',
                    'stats': _yolo_stats(stats)}, 400

        result = dataset.import_coco(coco, style=f"YOLO {stats['task']}", user=current_user,
                                     create_categories=current_user.has_perm('create_categories'))
        result['stats'] = _yolo_stats(stats)
        result['names_found'] = names is not None
        return result


def _yolo_stats(stats):
    return {
        'task': stats['task'],
        'matched': stats['matched'],
        'annotations': stats['annotations'],
        'invalid': stats['invalid'],
        'unmatched': len(stats['unmatched']),
        'unmatched_examples': stats['unmatched'][:5],
        'ambiguous': stats['ambiguous'][:5],
    }


@api.route('/<int:dataset_id>/video')
class DatasetVideo(Resource):

    @api.expect(video_upload)
    @login_required
    def post(self, dataset_id):
        """ Upload a video; frames at a fixed interval become dataset images (a task) """
        import uuid
        from config import Config
        from ..util.video import VIDEO_EXTENSIONS, import_video
        from ..sockets import socketio

        args = video_upload.parse_args()
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset ID'}, 400
        if not current_user.can_edit(dataset):
            return {'message': 'You do not have permission to edit this dataset'}, 403

        video = args.get('video')
        found = None
        if video is None:
            from ..util.video import staged
            found = staged(args.get('upload_id'), current_user)
            if found is None:
                return {'message': 'Send a video file or the upload_id of an uploaded video'}, 400
            name = found[1]['name']
        else:
            name = os.path.basename((video.filename or 'video').replace('\\', '/'))
            ext = os.path.splitext(name)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                return {'message': 'Unsupported video type: ' + (ext or name)}, 400
        every = args.get('every_seconds') or 1.0
        every_frames = args.get('every_frames')
        if every_frames is not None:
            if not 1 <= every_frames <= 100000:
                return {'message': 'every_frames must be between 1 and 100000'}, 400
        elif not 0.04 <= every <= 3600:
            return {'message': 'every_seconds must be between 0.04 and 3600'}, 400
        start_seconds = args.get('start_seconds') or 0.0
        end_seconds = args.get('end_seconds')
        if start_seconds < 0 or (end_seconds is not None and end_seconds <= start_seconds):
            return {'message': 'start_seconds must be >= 0 and end_seconds after it'}, 400
        max_frames = args.get('max_frames') or 1000
        if not 1 <= max_frames <= 20000:
            return {'message': 'max_frames must be between 1 and 20000'}, 400

        if found is not None:
            path = found[0]
            try:
                os.remove(os.path.join(os.path.dirname(path), args['upload_id'] + '.json'))
            except OSError:
                pass
        else:
            # kept in a hidden folder until the frames are extracted, then deleted
            upload_dir = os.path.join(dataset.directory, '.uploads')
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, uuid.uuid4().hex + ext)
            video.save(path)

        return import_video(dataset, path, name, every_seconds=every, every_frames=every_frames,
                            start_seconds=start_seconds, end_seconds=end_seconds,
                            max_frames=max_frames,
                            user=current_user, socket=socketio,
                            background=not Config.CELERY_TASK_ALWAYS_EAGER)


stage_upload = reqparse.RequestParser()
stage_upload.add_argument('video', location='files', type=FileStorage, required=True, help='Video file')


@api.route('/video/stage')
class VideoStage(Resource):

    @api.expect(stage_upload)
    @login_required
    def post(self):
        """ Upload a video before importing it: returns its length, fps and frame count """
        from ..util.video import stage
        args = stage_upload.parse_args()
        try:
            return stage(args['video'], current_user)
        except ValueError as e:
            return {'message': str(e)}, 400


chunk_start_args = reqparse.RequestParser()
chunk_start_args.add_argument('name', location='json', required=True)
chunk_start_args.add_argument('size', location='json', type=int, required=True)


@api.route('/video/stage/start')
class VideoStageStart(Resource):

    @api.expect(chunk_start_args)
    @login_required
    def post(self):
        """ Start uploading a video in pieces (PUT .../<upload_id>/chunk?offset=, then POST .../finish) """
        from ..util.video import chunk_start
        args = chunk_start_args.parse_args()
        try:
            return chunk_start(args['name'], args['size'], current_user)
        except ValueError as e:
            return {'message': str(e)}, 400


@api.route('/video/stage/<string:upload_id>/chunk')
class VideoStageChunk(Resource):

    @login_required
    def put(self, upload_id):
        """ One piece of the video (raw bytes) at ?offset= """
        from flask import request
        from ..util.video import chunk_append
        try:
            offset = int(request.args.get('offset', -1))
            return {'received': chunk_append(upload_id, current_user, offset, request.get_data(cache=False))}
        except LookupError as e:
            return {'message': str(e)}, 404
        except ValueError as e:
            return {'message': str(e)}, 409


@api.route('/video/stage/<string:upload_id>/finish')
class VideoStageFinish(Resource):

    @login_required
    def post(self, upload_id):
        """ All pieces sent: returns the video's length, fps and frame count """
        from ..util.video import chunk_finish
        try:
            return chunk_finish(upload_id, current_user)
        except LookupError as e:
            return {'message': str(e)}, 404
        except ValueError as e:
            return {'message': str(e)}, 400


@api.route('/video/stage/<string:upload_id>')
class VideoStageId(Resource):

    @login_required
    def delete(self, upload_id):
        """ Drop an uploaded video that will not be imported """
        from ..util.video import discard
        return {'success': discard(upload_id, current_user, complete=None)}


@api.route('/<int:dataset_id>/scan')
class DatasetScan(Resource):
    
    @login_required
    def get(self, dataset_id):

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        
        if not dataset:
            return {'message': 'Invalid dataset ID'}, 400
        
        return dataset.scan(user=current_user)



def _ai_annotations(dataset, model=None, category_id=None, image_id=None, keep_edited=True):
    """Annotations a model made in the dataset (still there). ``keep_edited``
    leaves out those someone worked on in the annotator since: selecting one
    there records an editing session (so "touched", even if not moved)."""
    query = AnnotationModel.objects(dataset_id=dataset.id, deleted=False, source='model')
    if model:
        query = query.filter(model=model)
    if category_id:
        query = query.filter(category_id=int(category_id))
    if image_id:
        query = query.filter(image_id=int(image_id))
    if keep_edited:
        query = query.filter(Q(events__size=0) | Q(events__exists=False))
    return query


def _ai_filters(source):
    def number(key):
        try:
            return int(source.get(key)) if source.get(key) not in (None, '', 'null') else None
        except (TypeError, ValueError):
            raise ValueError(f"{key}: a number")
    keep = source.get('keep_edited', True)
    keep = keep if isinstance(keep, bool) else str(keep).lower() not in ('0', 'false', 'no')
    return {"model": source.get('model') or None, "category_id": number('category_id'),
            "image_id": number('image_id'), "keep_edited": keep}


@api.route('/<int:dataset_id>/ai')
class DatasetAiAnnotations(Resource):

    @login_required
    def get(self, dataset_id):
        """ How many annotations models made here: per model and category, and
        how many match the filters (?model, category_id, image_id, keep_edited) """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        try:
            filters = _ai_filters(request.args)
        except ValueError as e:
            return {'message': str(e)}, 400
        _mark_sources(dataset.id)  # older runs: mark what models made
        everything = _ai_annotations(dataset, keep_edited=False)
        edited = everything.count() - _ai_annotations(dataset).count()
        models, categories = {}, {}
        for row in everything.only('model', 'category_id').as_pymongo():
            models[row.get('model') or ''] = models.get(row.get('model') or '', 0) + 1
            categories[row['category_id']] = categories.get(row['category_id'], 0) + 1
        names = {c.id: c.name for c in CategoryModel.objects(id__in=list(categories)).only('id', 'name')}
        matching = _ai_annotations(dataset, **filters)
        return {
            'total': everything.count(), 'edited': edited,
            'models': [{'name': k, 'count': v} for k, v in sorted(models.items(), key=lambda kv: -kv[1])],
            'categories': [{'id': k, 'name': names.get(k, str(k)), 'count': v}
                           for k, v in sorted(categories.items(), key=lambda kv: -kv[1])],
            'matching': matching.count(), 'matching_images': len(matching.distinct('image_id')),
            'can_edit': current_user.can_edit(dataset),
        }


@api.route('/<int:dataset_id>/ai/delete')
class DatasetAiAnnotationsDelete(Resource):

    @login_required
    def post(self, dataset_id):
        """ Send annotations models made to the trash (they can be restored);
        filters as above, in the JSON body """
        dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        if not current_user.can_edit(dataset):
            return {'message': 'You do not have permission to edit this dataset'}, 403
        try:
            filters = _ai_filters(request.get_json(silent=True) or {})
        except ValueError as e:
            return {'message': str(e)}, 400
        _mark_sources(dataset.id)
        query = _ai_annotations(dataset, **filters)
        image_ids = query.distinct('image_id')
        count = query.count()
        if not count:
            return {'success': True, 'deleted': 0, 'images': 0}
        from ..util.trash import soft_delete, refresh_image
        batch = soft_delete(query, current_user)  # one line in the activity log, restorable
        for image_id in image_ids:
            refresh_image(image_id)
        return {'success': True, 'deleted': count, 'images': len(image_ids), 'batch': batch}
