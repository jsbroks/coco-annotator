"""Asking for help while annotating: see whether the dataset's creator /
reviewers are online, send them the question (pushed to their open pages),
answer on the image."""
import datetime

from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
from mongoengine import Q

from database import AnnotationModel, DatasetModel, HelpModel, ImageModel, UserModel
from ..util import activity

api = Namespace('help', description='Questions while annotating')

ask_args = reqparse.RequestParser()
ask_args.add_argument('image_id', type=int, required=True, location='json')
ask_args.add_argument('message', default='', location='json')
ask_args.add_argument('to', type=list, default=None, location='json')
ask_args.add_argument('annotation_id', type=int, default=None, location='json')
ask_args.add_argument('region', type=dict, default=None, location='json',
                      help='Where the asker zoomed to: {x, y, w, h} in image pixels')

reply_args = reqparse.RequestParser()
reply_args.add_argument('message', default='', location='json')
reply_args.add_argument('resolve', type=bool, default=False, location='json')

ONLINE_SECONDS = 120


def _image(image_id):
    image = current_user.images.filter(id=image_id, deleted=False).first()
    if image is None:
        return None, None
    return image, DatasetModel.objects(id=image.dataset_id).first()


def _helpers(dataset):
    """The dataset's creator and reviewers (not the asker), online first."""
    from ..sockets import is_online
    names = [dataset.owner] + [r for r in (dataset.reviewers or [])
                               if r != dataset.owner and r in (dataset.users or [])]
    users = {u.username: u for u in UserModel.objects(username__in=names).only('username', 'name', 'last_seen')}
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    out = []
    for name in names:
        if name == current_user.username or name not in users:
            continue
        u = users[name]
        recent = u.last_seen and (now - u.last_seen).total_seconds() < ONLINE_SECONDS
        out.append({'username': name, 'name': u.name or name,
                    'role': 'creator' if name == dataset.owner else 'reviewer',
                    'online': bool(is_online(name) or recent),
                    'last_seen': u.last_seen.isoformat() + 'Z' if u.last_seen else None})
    out.sort(key=lambda h: (not h['online'], h['role'] != 'creator'))
    return out


def _can_answer(req, dataset):
    """The dataset's creator and reviewers as they are now (someone taken off
    the dataset can no longer answer, even if they were asked)."""
    if dataset is None or getattr(dataset, 'deleted', False):
        return False
    return dataset.can_review(current_user)


def _push(names, event, req):
    from ..sockets import notify_user
    data = _out(req)
    for name in set(names):
        try:
            notify_user(name, event, data)
        except Exception:  # pragma: no cover - a push must not fail the request
            pass


def _out(req):
    data = req.to_dict()
    names = {u.username: u.name for u in UserModel.objects(
        username__in=list({req.user, *[r.get('user') for r in req.replies or []]})).only('username', 'name')}
    data['user_name'] = names.get(req.user) or req.user
    for r in data['replies']:
        r['name'] = names.get(r.get('user')) or r.get('user')
    dataset = DatasetModel.objects(id=req.dataset_id).only('name').first()
    data['dataset_name'] = dataset.name if dataset else ''
    return data


@api.route('/helpers/<int:image_id>')
class Helpers(Resource):
    @login_required
    def get(self, image_id):
        """ Who can be asked about this image, and who is online """
        image, dataset = _image(image_id)
        if image is None or dataset is None:
            return {'message': 'Invalid image id'}, 400
        return {'helpers': _helpers(dataset)}


@api.route('/')
class Ask(Resource):
    @login_required
    @api.expect(ask_args)
    def post(self):
        """ Ask for help on an image (pushed to the people asked) """
        args = ask_args.parse_args()
        image, dataset = _image(args['image_id'])
        if image is None or dataset is None:
            return {'message': 'Invalid image id'}, 400
        message = (args.get('message') or '').strip()[:2000]
        region = None
        raw = args.get('region') or {}
        try:
            x, y, w, h = (float(raw[k]) for k in ('x', 'y', 'w', 'h'))
            x, y = max(0.0, x), max(0.0, y)
            w, h = min(w, image.width - x), min(h, image.height - y)
            if w > 0 and h > 0:
                region = {'x': round(x, 1), 'y': round(y, 1), 'w': round(w, 1), 'h': round(h, 1)}
        except (KeyError, TypeError, ValueError):
            region = None
        if not message and region is None and not args.get('annotation_id'):
            return {'message': 'Zoom to the part you are not sure about (or write a note).'}, 400
        allowed = {h['username'] for h in _helpers(dataset)}
        wanted = args.get('to') if isinstance(args.get('to'), list) else None
        to = [u for u in (wanted or allowed) if isinstance(u, str) and u in allowed]
        annotation_id = args.get('annotation_id')
        if annotation_id is not None and AnnotationModel.objects(
                id=annotation_id, image_id=image.id).only('id').first() is None:
            annotation_id = None
        if not to:
            return {'message': 'Nobody to ask: the dataset has no creator or reviewers besides you.'}, 400
        req = HelpModel(image_id=image.id, dataset_id=dataset.id, file_name=image.file_name,
                        user=current_user.username, to=to, message=message,
                        annotation_id=annotation_id, region=region)
        req.save()
        activity.record('help_request', current_user, dataset_id=dataset.id, image_id=image.id,
                        detail={'file_name': image.file_name, 'to': to, 'message': message[:200]},
                        text=f"{image.file_name} {message[:200]}")
        _push(to, 'helpRequest', req)
        return _out(req)


@api.route('/inbox')
class Inbox(Resource):
    @login_required
    def get(self):
        """ Open questions asked to me, and my questions (answered or not) """
        name = current_user.username
        incoming = list(HelpModel.objects(to=name, status='open').order_by('-created_at')[:100])
        datasets = {d.id: d for d in DatasetModel.objects(id__in=list({r.dataset_id for r in incoming}))}
        incoming = [r for r in incoming if _can_answer(r, datasets.get(r.dataset_id))][:50]
        # answered ones stay until the asker has looked at them
        mine = HelpModel.objects(user=name, status__in=['open', 'resolved'], seen__ne=True).order_by('-updated_at')[:20]
        return {'incoming': [_out(r) for r in incoming], 'mine': [_out(r) for r in mine]}


@api.route('/image/<int:image_id>')
class ImageHelp(Resource):
    @login_required
    def get(self, image_id):
        """ Questions about this image (open ones, and answered ones of the last days) """
        image, dataset = _image(image_id)
        if image is None:
            return {'message': 'Invalid image id'}, 400
        # open ones, and answered ones the asker has not looked at yet
        reqs = HelpModel.objects(Q(image_id=image_id) & (Q(status='open') | (Q(status='resolved') & Q(seen__ne=True))))\
            .order_by('created_at')
        out = []
        for r in reqs:
            if r.status == 'resolved' and r.user != current_user.username:
                continue  # done: only the asker still sees it (until they close it)
            data = _out(r)
            data['can_answer'] = _can_answer(r, dataset) and r.user != current_user.username
            data['mine'] = r.user == current_user.username
            out.append(data)
        return {'requests': out}


@api.route('/<int:help_id>/reply')
class Reply(Resource):
    @login_required
    @api.expect(reply_args)
    def post(self, help_id):
        """ Answer (and optionally close) a question; the asker is told right away """
        req = HelpModel.objects(id=help_id).first()
        if req is None:
            return {'message': 'Invalid id'}, 400
        dataset = DatasetModel.objects(id=req.dataset_id).first()
        mine = req.user == current_user.username
        if not mine and not _can_answer(req, dataset):
            return {'message': 'Only the people asked can answer'}, 403
        if req.status == 'cancelled':
            return {'message': 'This question was withdrawn'}, 400
        args = reply_args.parse_args()
        message = (args.get('message') or '').strip()[:2000]
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        update = {'set__updated_at': now}
        if message:
            update['push__replies'] = {'user': current_user.username, 'message': message, 'at': now}
        if not mine:
            update['set__seen'] = False  # a new answer for the asker
        if args.get('resolve'):
            update['set__status'] = 'resolved'
            update['set__resolved_by'] = current_user.username
        if len(update) == 1:
            return {'message': 'Nothing to send'}, 400
        req.update(**update)
        req.reload()
        if not mine:
            activity.record('help_reply', current_user, dataset_id=req.dataset_id, image_id=req.image_id,
                            detail={'file_name': req.file_name, 'to': req.user, 'resolved': bool(args.get('resolve')),
                                    'message': message[:200]}, text=f"{req.file_name} {message[:200]}")
        # tell the others in the conversation
        others = [u for u in [req.user, *(req.to or [])] if u != current_user.username]
        _push(others, 'helpReply', req)
        return _out(req)


@api.route('/<int:help_id>/seen')
class Seen(Resource):
    @login_required
    def post(self, help_id):
        """ The asker has read the answer: it leaves their lists """
        n = HelpModel.objects(id=help_id, user=current_user.username).update(set__seen=True)
        return {'success': bool(n)}


@api.route('/<int:help_id>/cancel')
class Cancel(Resource):
    @login_required
    def post(self, help_id):
        """ The asker withdraws a question """
        req = HelpModel.objects(id=help_id, user=current_user.username).first()
        if req is None:
            return {'message': 'Invalid id'}, 400
        req.update(set__status='cancelled', set__updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        req.reload()
        _push(req.to or [], 'helpReply', req)
        return {'success': True}
