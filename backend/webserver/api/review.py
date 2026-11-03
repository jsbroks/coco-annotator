"""Review workflow: image status, assignment of images to members, progress.

Status of an image:

* ``unlabeled`` - nobody has submitted it yet (default)
* ``labeled``   - an annotator pressed "done" (waiting for review)
* ``approved``  - a reviewer accepted it
* ``rejected``  - a reviewer sent it back, with a note

Reviewers are the dataset owner, admins and the members listed in
``dataset.reviewers``. Anyone who can edit the dataset can submit.
"""
import datetime

from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
from mongoengine.queryset.visitor import Q

from database import AnnotationModel, CategoryModel, DatasetModel, ImageModel

api = Namespace('review', description='Image status, assignment and review')

status_args = reqparse.RequestParser()
status_args.add_argument('action', location='json', required=True,
                         choices=('submit', 'approve', 'reject', 'reopen'))
status_args.add_argument('note', location='json', default='')
status_args.add_argument('regions', location='json', type=list, default=None,
                         help='reject: problem areas [[x, y, w, h], ...] in image pixels')
status_args.add_argument('skip_empty', location='json', type=bool, default=False,
                         help='submit: do nothing for an image without annotations or image class')
status_args.add_argument('confirm_empty', location='json', type=bool, default=False,
                         help='submit: the image has nothing to annotate (a background image)')
status_args.add_argument('image_ids', location='json', type=list, default=None,
                         help='Apply to several images of the same dataset')

assign_args = reqparse.RequestParser()
assign_args.add_argument('usernames', location='json', type=list, default=[],
                         help='Members to assign to (empty: unassign)')
assign_args.add_argument('image_ids', location='json', type=list, default=None,
                         help='Images to assign (default: every image that matches "scope")')
assign_args.add_argument('scope', location='json', default='unassigned',
                         choices=('unassigned', 'all', 'unlabeled'),
                         help='Which images when image_ids is not given')
assign_args.add_argument('from_user', location='json', default=None,
                         help='Only images now assigned to this person ("scope" all or unlabeled)')
assign_args.add_argument('folders', location='json', type=dict, default=None,
                         help='{"folder": "username", ...}: each folder (e.g. the frames of one video) '
                              'goes whole to one person ("" unassigns it); "scope" still applies')

reviewers_args = reqparse.RequestParser()
reviewers_args.add_argument('reviewers', location='json', type=list, default=[])


def _dataset(dataset_id):
    return current_user.datasets.filter(id=dataset_id, deleted=False).first()


def _has_nothing(image):
    """No shapes or keypoints drawn and no whole-image class."""
    if getattr(image, 'image_class', None) is not None:
        return False
    for a in AnnotationModel.objects(image_id=image.id, deleted=False).only('segmentation', 'keypoints').as_pymongo():
        if a.get('segmentation') or any(v > 0 for v in (a.get('keypoints') or [])[2::3]):
            return False
    return True


def image_review_info(image):
    def iso(value):
        return value.isoformat() + 'Z' if value else None
    return {
        'status': image.status or 'unlabeled',
        'assignee': image.assignee,
        'labeled_by': image.labeled_by,
        'labeled_at': iso(image.labeled_at),
        'reviewed_by': image.reviewed_by,
        'reviewed_at': iso(image.reviewed_at),
        'review_note': image.review_note,
        'review_regions': list(getattr(image, 'review_regions', None) or []),
    }


def clean_regions(regions, image=None):
    """At most 20 boxes of four numbers, clipped to the image."""
    out = []
    for r in (regions or [])[:20]:
        try:
            x, y, w, h = (float(v) for v in r)
        except (TypeError, ValueError):
            continue
        if image is not None and image.width and image.height:
            x2, y2 = min(x + w, image.width), min(y + h, image.height)
            x, y = max(0.0, x), max(0.0, y)
            w, h = x2 - x, y2 - y
        if w > 0 and h > 0:
            out.append([round(x, 1), round(y, 1), round(w, 1), round(h, 1)])
    return out


def _int_list(values):
    """[1, "2", ...] -> [1, 2]; None when something is not a number."""
    if not isinstance(values, list):
        return None
    out = []
    for v in values:
        if isinstance(v, (list, dict, bool)):
            return None
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            return None
    return out


def change_status(images, dataset, action, note='', regions=None):
    """Apply ``action`` to the images. Returns (count, error message or None)."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    me = current_user.username
    if action in ('approve', 'reject'):
        if not dataset.can_review(current_user):
            return 0, 'Only reviewers can approve or reject images'
    elif not current_user.can_edit(dataset):
        return 0, 'You do not have permission to edit this dataset'

    # a reviewer's own work needs no review: submitting approves it
    self_approve = action == 'submit' and dataset.can_review(current_user)
    count = 0
    for image in images:
        if self_approve:
            image.update(set__status='approved', set__labeled_by=me, set__labeled_at=now,
                         set__reviewed_by=me, set__reviewed_at=now, set__review_note='', set__review_regions=[])
        elif action == 'submit':
            # an approved image stays approved: only a reviewer can reopen it
            if image.status == 'approved':
                continue
            image.update(set__status='labeled', set__labeled_by=me, set__labeled_at=now)
        elif action == 'approve':
            image.update(set__status='approved', set__reviewed_by=me, set__reviewed_at=now,
                         set__review_note='', set__review_regions=[])
        elif action == 'reject':
            image.update(set__status='rejected', set__reviewed_by=me, set__reviewed_at=now,
                         set__review_note=(note or '').strip()[:2000],
                         set__review_regions=clean_regions(regions, image))
        elif action == 'reopen':
            # back to work; an approved image can only be reopened by a reviewer
            if image.status == 'approved' and not dataset.can_review(current_user):
                continue
            image.update(set__status='unlabeled')
        count += 1
    return count, None


@api.route('/image/<int:image_id>')
class ImageStatus(Resource):

    @login_required
    def get(self, image_id):
        image = current_user.images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {'message': 'Invalid image id'}, 400
        return image_review_info(image)

    @api.expect(status_args)
    @login_required
    def post(self, image_id):
        """ submit / approve / reject / reopen one image (or several with image_ids) """
        args = status_args.parse_args()
        image = current_user.images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {'message': 'Invalid image id'}, 400
        dataset = _dataset(image.dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset'}, 400

        if args.get('skip_empty') and args['action'] == 'submit' and not args.get('image_ids') \
                and not (image.num_annotations or 0) and getattr(image, 'image_class', None) is None:
            return {'success': True, 'count': 0, 'skipped': True, **image_review_info(image)}

        images = [image]
        if args.get('image_ids'):
            ids = _int_list(args['image_ids'])
            if ids is None:
                return {'message': 'image_ids must be a list of numbers'}, 400
            images = list(ImageModel.objects(id__in=ids, dataset_id=dataset.id, deleted=False))

        count, error = change_status(images, dataset, args['action'], args.get('note'),
                                     args.get('regions'))
        if error:
            return {'message': error}, 403
        if args['action'] == 'submit' and args.get('confirm_empty') and not args.get('image_ids') \
                and count and _has_nothing(image):
            # the statistics no longer list it as "not annotated"
            image.update(set__confirmed_empty=True)
        elif args['action'] == 'reject':
            # a rejected image is not "confirmed empty" any more
            ImageModel.objects(id__in=[i.id for i in images]).update(set__confirmed_empty=False)
        if count:
            from ..util import activity
            single = len(images) == 1
            activity.record('review', current_user, dataset_id=dataset.id,
                            image_id=images[0].id if single else None, counts={'images': count},
                            detail={'review_action': 'self_approve' if args['action'] == 'submit'
                                    and dataset.can_review(current_user) else args['action'],
                                    'note': args.get('note') or None,
                                    'regions': len(args.get('regions') or []) or None,
                                    'file_name': images[0].file_name if single else None},
                            text=" ".join(i.file_name for i in images[:50]))
        image.reload()
        return {'success': True, 'count': count, **image_review_info(image)}


def image_folder(dataset, path):
    """The image's folder inside the dataset ("" for the dataset's own folder)."""
    import os
    base = (dataset.directory or '').rstrip('/')
    rel = os.path.relpath(path or '', base) if base and (path or '').startswith(base + '/') else (path or '')
    folder = os.path.dirname(rel)
    return '' if folder in ('.', '') else folder


def _in_scope(row, scope):
    if scope == 'unassigned':
        return not row.get('assignee')
    if scope == 'unlabeled':
        return (row.get('status') or 'unlabeled') in ('unlabeled', 'rejected')
    return True


@api.route('/dataset/<int:dataset_id>/folders')
class DatasetFolders(Resource):

    @login_required
    def get(self, dataset_id):
        """ Folders of the dataset (one per imported video): image counts per status,
        how many have annotations, and who they are assigned to """
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        folders = {}
        for row in ImageModel.objects(dataset_id=dataset.id, deleted=False) \
                .only('path', 'status', 'assignee', 'num_annotations').as_pymongo():
            name = image_folder(dataset, row.get('path'))
            f = folders.setdefault(name, {'folder': name, 'images': 0, 'unassigned': 0,
                                          'unlabeled': 0, 'annotated': 0, 'assignees': {},
                                          'status': {s: 0 for s in ImageModel.STATUSES}})
            f['images'] += 1
            status = row.get('status') or 'unlabeled'
            f['status'][status] = f['status'].get(status, 0) + 1
            if row.get('num_annotations'):
                f['annotated'] += 1
            if _in_scope(row, 'unassigned'):
                f['unassigned'] += 1
            else:
                f['assignees'][row['assignee']] = f['assignees'].get(row['assignee'], 0) + 1
            if _in_scope(row, 'unlabeled'):
                f['unlabeled'] += 1
        return {'folders': sorted(folders.values(), key=lambda f: f['folder'])}


@api.route('/dataset/<int:dataset_id>/assign')
class DatasetAssign(Resource):

    @api.expect(assign_args)
    @login_required
    def post(self, dataset_id):
        """ Split images evenly between members (or unassign with no usernames) """
        args = assign_args.parse_args()
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        if not dataset.can_assign(current_user):
            return {'message': 'Only the owner or reviewers can assign images'}, 403

        members = {u.username for u in dataset.get_users()}
        usernames = [u for u in (args.get('usernames') or []) if isinstance(u, str) and u]
        unknown = [u for u in usernames if u not in members]
        if unknown:
            return {'message': 'Not members of this dataset: ' + ', '.join(unknown)}, 400

        if args.get('folders') is not None:
            return self.by_folder(dataset, members, args)

        query = ImageModel.objects(dataset_id=dataset.id, deleted=False)
        if args.get('image_ids') is not None:
            ids = _int_list(args['image_ids'])
            if ids is None:
                return {'message': 'image_ids must be a list of numbers'}, 400
            query = query.filter(id__in=ids)
        elif args.get('from_user'):
            # one person's images (e.g. to clear what they still have to do)
            query = query.filter(assignee=args['from_user'])
            if args['scope'] == 'unlabeled':
                query = query.filter(Q(status=None) | Q(status__in=['unlabeled', 'rejected']))
        elif args['scope'] == 'unassigned':
            query = query.filter(Q(assignee=None) | Q(assignee=''))
        elif args['scope'] == 'unlabeled':
            query = query.filter(Q(status=None) | Q(status__in=['unlabeled', 'rejected']))
        images = list(query.order_by('file_name').only('id'))

        from ..util import activity
        if not usernames:
            ImageModel.objects(id__in=[i.id for i in images]).update(unset__assignee=True)
            if images:
                activity.record('assign', current_user, dataset_id=dataset.id,
                                counts={'images': len(images)},
                                detail={'unassigned': True, 'from': args.get('from_user') or None})
            return {'success': True, 'assigned': {}, 'unassigned': len(images)}

        # contiguous blocks in file name order: each person gets a range
        counts = {}
        per_person = -(-len(images) // len(usernames)) if images else 0
        for n, username in enumerate(usernames):
            block = images[n * per_person:(n + 1) * per_person]
            if block:
                ImageModel.objects(id__in=[i.id for i in block]).update(set__assignee=username)
            counts[username] = len(block)
        if images:
            activity.record('assign', current_user, dataset_id=dataset.id,
                            counts={'images': len(images)}, detail={'people': counts},
                            text=" ".join(counts))
        return {'success': True, 'assigned': counts, 'unassigned': 0}

    @staticmethod
    def by_folder(dataset, members, args):
        """Each folder goes whole to one person."""
        plan = args['folders']
        if not isinstance(plan, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in plan.items()):
            return {'message': 'folders must map folder names to usernames'}, 400
        unknown = sorted({u for u in plan.values() if u and u not in members})
        if unknown:
            return {'message': 'Not members of this dataset: ' + ', '.join(unknown)}, 400

        targets = {}  # username ("" = unassign) -> image ids
        for row in ImageModel.objects(dataset_id=dataset.id, deleted=False) \
                .only('id', 'path', 'status', 'assignee').as_pymongo():
            folder = image_folder(dataset, row.get('path'))
            if folder in plan and _in_scope(row, args['scope']):
                targets.setdefault(plan[folder], []).append(row['_id'])

        counts, unassigned = {}, 0
        for username, ids in targets.items():
            if username:
                ImageModel.objects(id__in=ids).update(set__assignee=username)
                counts[username] = counts.get(username, 0) + len(ids)
            else:
                ImageModel.objects(id__in=ids).update(unset__assignee=True)
                unassigned += len(ids)
        if counts or unassigned:
            from ..util import activity
            activity.record('assign', current_user, dataset_id=dataset.id,
                            counts={'images': sum(counts.values()) + unassigned},
                            detail={'people': counts, 'folders': {k: v for k, v in plan.items()}},
                            text=" ".join(list(counts) + list(plan)))
        return {'success': True, 'assigned': counts, 'unassigned': unassigned}


@api.route('/dataset/<int:dataset_id>/progress')
class DatasetProgress(Resource):

    @login_required
    def get(self, dataset_id):
        """ Images per status, overall and per assignee """
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400

        statuses = ImageModel.STATUSES
        total = {s: 0 for s in statuses}
        people = {}
        for row in ImageModel.objects(dataset_id=dataset.id, deleted=False) \
                .only('status', 'assignee', 'labeled_by', 'num_annotations').as_pymongo():
            status = row.get('status') or 'unlabeled'
            total[status] = total.get(status, 0) + 1
            who = row.get('assignee') or ''
            person = people.setdefault(who, {s: 0 for s in statuses})
            person[status] += 1

        members = [u.username for u in dataset.get_users()]
        return {
            'total': total,
            'images': sum(total.values()),
            'people': [{'username': name, **counts} for name, counts in sorted(people.items()) if name],
            'unassigned': people.get('', {s: 0 for s in statuses}),
            'members': members,
            'reviewers': list(dataset.reviewers or []),
            'can_review': dataset.can_review(current_user),
            'is_owner': dataset.is_owner(current_user),
            'is_creator': dataset.is_creator(current_user),
            'can_assign': dataset.can_assign(current_user),
            'me': current_user.username,
            'owner': dataset.owner,
        }


@api.route('/dataset/<int:dataset_id>/reviewers')
class DatasetReviewers(Resource):

    @api.expect(reviewers_args)
    @login_required
    def post(self, dataset_id):
        """ Set which members may approve / reject (owner only) """
        args = reviewers_args.parse_args()
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        if not dataset.is_creator(current_user):
            return {'message': 'Only the creator of the dataset can choose reviewers'}, 403
        members = {u.username for u in dataset.get_users()}
        reviewers = sorted({u for u in args.get('reviewers') or [] if u in members})
        before = sorted(dataset.reviewers or [])
        dataset.update(set__reviewers=reviewers)
        if before != reviewers:
            from ..util import activity
            activity.record('reviewers', current_user, dataset_id=dataset.id,
                            detail={'reviewers': reviewers}, text=" ".join(reviewers))
        return {'success': True, 'reviewers': reviewers}


@api.route('/dataset/<int:dataset_id>/next')
class DatasetNextImage(Resource):

    @login_required
    def get(self, dataset_id):
        """ Next image to work on: for reviewers the next "labeled" one, for
        others the next of their own unlabeled / rejected images """
        from flask import request
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        mode = request.args.get('mode', 'review')
        after = request.args.get('after', '')
        query = ImageModel.objects(dataset_id=dataset.id, deleted=False)
        if mode == 'review':
            query = query.filter(status='labeled')
        else:
            query = query.filter(assignee=current_user.username) \
                .filter(Q(status=None) | Q(status__in=['unlabeled', 'rejected']))
        image = query.filter(file_name__gt=after).order_by('file_name').only('id').first() \
            or query.order_by('file_name').only('id').first()
        return {'id': image.id if image else None}


__all__ = ['api', 'image_review_info', 'change_status']


queue_args = reqparse.RequestParser()
queue_args.add_argument('status', location='args', default='labeled',
                        choices=('labeled', 'approved', 'rejected', 'unlabeled', 'all'))
queue_args.add_argument('user', location='args', default='', help='only images labeled by this member')
queue_args.add_argument('order', location='args', default='file_name', choices=('file_name', 'submitted'),
                        help='file name (as on the dataset page) or when it was submitted')
queue_args.add_argument('page', location='args', type=int, default=1)
queue_args.add_argument('per_page', location='args', type=int, default=9)


@api.route('/dataset/<int:dataset_id>/queue')
class ReviewQueue(Resource):

    @api.expect(queue_args)
    @login_required
    def get(self, dataset_id):
        """ Quick review: a page of images with their annotations, in file name order """
        dataset = _dataset(dataset_id)
        if dataset is None:
            return {'message': 'Invalid dataset id'}, 400
        args = queue_args.parse_args()
        per_page = max(1, min(int(args.get('per_page') or 9), 50))
        page = max(1, int(args.get('page') or 1))

        query = ImageModel.objects(dataset_id=dataset.id, deleted=False)
        status = args.get('status') or 'labeled'
        if status == 'unlabeled':
            query = query.filter(Q(status=None) | Q(status='unlabeled'))
        elif status != 'all':
            query = query.filter(status=status)
        if args.get('user'):
            query = query.filter(labeled_by=args['user'])
        total = query.count()
        order = ('labeled_at', 'file_name') if args.get('order') == 'submitted' else ('file_name',)
        images = list(query.order_by(*order).skip((page - 1) * per_page).limit(per_page)
                      .only('id', 'file_name', 'width', 'height', 'status', 'labeled_by', 'labeled_at',
                            'reviewed_by', 'review_note', 'review_regions', 'assignee'))
        annotations = AnnotationModel.objects(image_id__in=[i.id for i in images], deleted=False)\
            .only('id', 'image_id', 'category_id', 'segmentation', 'bbox', 'isbbox', 'isrbbox', 'color', 'keypoints')
        by_image = {}
        for a in annotations:
            by_image.setdefault(a.image_id, []).append({
                'id': a.id, 'category_id': a.category_id, 'segmentation': a.segmentation or [],
                'bbox': a.bbox or [], 'isbbox': bool(a.isbbox), 'isrbbox': bool(getattr(a, 'isrbbox', False)),
                'keypoints': a.keypoints or []})
        in_dataset = set(dataset.categories or [])
        used = {a['category_id'] for anns in by_image.values() for a in anns}
        categories = CategoryModel.objects(id__in=list(set(dataset.categories or []) | used))\
            .only('id', 'name', 'color', 'supercategory', 'supercategories')
        members = sorted({i for i in ImageModel.objects(dataset_id=dataset.id, deleted=False,
                                                         labeled_by__ne=None).distinct('labeled_by') if i})
        out = []
        for image in images:
            info = image_review_info(image)
            out.append({'id': image.id, 'file_name': image.file_name, 'width': image.width,
                        'height': image.height, **info, 'annotations': by_image.get(image.id, [])})
        return {
            'total': total, 'page': page, 'per_page': per_page,
            'pages': max(1, (total + per_page - 1) // per_page),
            'images': out,
            'categories': [{'id': c.id, 'name': c.name, 'color': c.color, 'parents': c.parents(),
                            'in_dataset': c.id in in_dataset}
                           for c in categories],
            'labelers': members,
            'can_review': dataset.can_review(current_user),
            'dataset_name': dataset.name,
        }
