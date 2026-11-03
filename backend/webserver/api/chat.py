"""Chat: one room per dataset. Members (anyone who can open the dataset)
read and write; a message can point at one of the dataset's images."""
import datetime
import os
import uuid

from flask import send_file
from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from config import Config
from database import ChatMessageModel, ChatPhotoModel, ChatReadModel, ImageModel, UserModel

api = Namespace('chat', description='Chat per dataset')

MAX_TEXT = 1000
PAGE = 50

list_args = reqparse.RequestParser()
list_args.add_argument('before', type=int, default=None, location='args')
list_args.add_argument('limit', type=int, default=PAGE, location='args')

post_args = reqparse.RequestParser()
post_args.add_argument('text', default='', location='json')
post_args.add_argument('image_id', type=int, default=None, location='json')
post_args.add_argument('photos', type=list, default=None, location='json', help='Uploaded photo ids')

photo_args = reqparse.RequestParser()
photo_args.add_argument('file', location='files', type=FileStorage, required=True)

MAX_PHOTOS = 6
MAX_PHOTO_BYTES = 20 * 1024 * 1024
# photos are stored at most this wide / high (and without their metadata)
PHOTO_SIDE = 2560
THUMB_SIDE = 640

read_args = reqparse.RequestParser()
read_args.add_argument('last_id', type=int, required=True, location='json')


def _dataset(dataset_id):
    return current_user.datasets.filter(id=dataset_id, deleted=False).first()


def _names(usernames):
    return {u.username: u.name or u.username
            for u in UserModel.objects(username__in=list(set(usernames))).only('username', 'name')}


def photo_dir(dataset_id):
    # hidden: not taken for a dataset's images
    return os.path.join(Config.DATASET_DIRECTORY, '.chat', str(int(dataset_id)))


def _photos(messages):
    ids = [p for m in messages for p in (m.photos or [])]
    return {p.id: p.to_dict() for p in ChatPhotoModel.objects(id__in=ids)} if ids else {}


def _last_read(dataset_id):
    row = ChatReadModel.objects(user=current_user.username, dataset_id=dataset_id).first()
    return row.last_id if row else 0


def _unread(dataset_id):
    return ChatMessageModel.objects(dataset_id=dataset_id, id__gt=_last_read(dataset_id),
                                    user__ne=current_user.username).count()


@api.route('/dataset/<int:dataset_id>')
class DatasetChat(Resource):

    @login_required
    def get(self, dataset_id):
        """Messages, oldest first (``before`` pages back)"""
        if _dataset(dataset_id) is None:
            return {'message': 'Invalid dataset id'}, 400
        args = list_args.parse_args()
        limit = max(1, min(args['limit'] or PAGE, 200))
        query = ChatMessageModel.objects(dataset_id=dataset_id)
        if args['before']:
            query = query.filter(id__lt=args['before'])
        rows = list(query.order_by('-id').limit(limit + 1))
        more = len(rows) > limit
        rows = list(reversed(rows[:limit]))
        names = _names([m.user for m in rows])
        photos = _photos(rows)
        return {
            'messages': [m.to_dict(names, photos) for m in rows],
            'more': more,
            'last_read': _last_read(dataset_id),
            'unread': _unread(dataset_id),
            'me': current_user.username,
        }

    @login_required
    def post(self, dataset_id):
        """Send a message to the dataset's room"""
        if _dataset(dataset_id) is None:
            return {'message': 'Invalid dataset id'}, 400
        args = post_args.parse_args()
        text = (args.get('text') or '').strip()
        image = None
        if args.get('image_id') is not None:
            image = ImageModel.objects(id=args['image_id'], dataset_id=dataset_id, deleted=False) \
                .only('id', 'file_name').first()
            if image is None:
                return {'message': 'Image not in this dataset'}, 400
        photo_ids = [str(p) for p in (args.get('photos') or [])][:MAX_PHOTOS]
        photos = list(ChatPhotoModel.objects(id__in=photo_ids, dataset_id=dataset_id,
                                             user=current_user.username, message_id=None))
        if len(photos) != len(set(photo_ids)):
            return {'message': 'Unknown photo'}, 400
        photos.sort(key=lambda p: photo_ids.index(p.id))
        if not text and image is None and not photos:
            return {'message': 'Empty message'}, 400
        if len(text) > MAX_TEXT:
            return {'message': f'At most {MAX_TEXT} characters'}, 400

        message = ChatMessageModel(dataset_id=dataset_id, user=current_user.username, text=text,
                                   image_id=image.id if image else None,
                                   file_name=image.file_name if image else '',
                                   photos=[p.id for p in photos])
        message.save()
        for p in photos:
            p.update(set__message_id=message.id)
        data = message.to_dict({current_user.username: current_user.name}, {p.id: p.to_dict() for p in photos})
        # it counts as read for the sender
        ChatReadModel.objects(user=current_user.username, dataset_id=dataset_id) \
            .update_one(set__last_id=message.id, upsert=True)

        from ..sockets import socketio, chat_room
        socketio.emit('chat', data, room=chat_room(dataset_id))
        return data


@api.route('/dataset/<int:dataset_id>/read')
class DatasetChatRead(Resource):

    @login_required
    def post(self, dataset_id):
        """Everything up to ``last_id`` has been seen"""
        if _dataset(dataset_id) is None:
            return {'message': 'Invalid dataset id'}, 400
        last_id = read_args.parse_args()['last_id']
        if last_id > _last_read(dataset_id):
            ChatReadModel.objects(user=current_user.username, dataset_id=dataset_id) \
                .update_one(set__last_id=last_id, upsert=True)
        return {'unread': _unread(dataset_id)}


@api.route('/dataset/<int:dataset_id>/photo')
class DatasetChatPhoto(Resource):

    @api.expect(photo_args)
    @login_required
    def post(self, dataset_id):
        """ Upload a photo to send (then post the message with its id). It
        is stored at most 2560 px, without its metadata (place, camera). """
        if _dataset(dataset_id) is None:
            return {'message': 'Invalid dataset id'}, 400
        from PIL import Image, ImageOps, UnidentifiedImageError
        upload = photo_args.parse_args()['file']
        data = upload.stream.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES:
            return {'message': 'At most 20 MB'}, 400
        import io
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return {'message': 'Not an image'}, 400
        _clean_unsent()
        folder = photo_dir(dataset_id)
        os.makedirs(folder, exist_ok=True)
        photo_id = uuid.uuid4().hex
        animated = getattr(img, 'is_animated', False) and img.format in ('GIF', 'WEBP')
        if animated:
            # moving pictures as they are
            ext = '.gif' if img.format == 'GIF' else '.webp'
            path = os.path.join(folder, photo_id + ext)
            with open(path, 'wb') as fp:
                fp.write(data)
            width, height = img.size
        else:
            img = ImageOps.exif_transpose(img)  # upright, as the phone showed it
            img.thumbnail((PHOTO_SIDE, PHOTO_SIDE))
            alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            if alpha:
                ext, img = '.png', img.convert('RGBA')
            else:
                ext, img = '.jpg', img.convert('RGB')
            path = os.path.join(folder, photo_id + ext)
            img.save(path, quality=88, optimize=True) if ext == '.jpg' else img.save(path, optimize=True)
            width, height = img.size
        photo = ChatPhotoModel(id=photo_id, dataset_id=dataset_id, user=current_user.username,
                               filename=os.path.basename(path), width=width, height=height,
                               size=os.path.getsize(path))
        photo.save()
        return photo.to_dict()


def _clean_unsent():
    """Photos uploaded but never sent, after a day."""
    old = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=1)
    for p in ChatPhotoModel.objects(message_id=None, created_at__lt=old):
        try:
            os.remove(os.path.join(photo_dir(p.dataset_id), p.filename))
        except OSError:
            pass
        p.delete()


@api.route('/photo/<photo_id>')
class ChatPhoto(Resource):

    @login_required
    def get(self, photo_id):
        """ A photo of a chat (?thumb=1: a small copy) """
        from flask import request
        photo = ChatPhotoModel.objects(id=str(photo_id)).first()
        if photo is None or _dataset(photo.dataset_id) is None:
            return {'message': 'Unknown photo'}, 404
        if photo.message_id is None and photo.user != current_user.username:
            return {'message': 'Unknown photo'}, 404
        path = os.path.join(photo_dir(photo.dataset_id), photo.filename)
        if not os.path.isfile(path):
            return {'message': 'Unknown photo'}, 404
        if request.args.get('thumb') and not path.endswith(('.gif', '.webp')) and \
                max(photo.width, photo.height) > THUMB_SIDE:
            thumb = os.path.join(photo_dir(photo.dataset_id), 'thumbs', photo.filename)
            if not os.path.isfile(thumb):
                from PIL import Image
                os.makedirs(os.path.dirname(thumb), exist_ok=True)
                with Image.open(path) as img:
                    img.thumbnail((THUMB_SIDE, THUMB_SIDE))
                    img.save(thumb, quality=82) if thumb.endswith('.jpg') else img.save(thumb)
            path = thumb
        response = send_file(path, conditional=True, max_age=86400 * 30)
        response.headers['Cache-Control'] = 'private, max-age=2592000, immutable'
        return response
