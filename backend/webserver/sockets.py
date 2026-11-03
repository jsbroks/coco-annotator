import functools
import time

from flask import session, request
from flask_socketio import (
    SocketIO,
    disconnect,
    join_room,
    leave_room,
    emit
)
from flask_login import current_user

from database import ImageModel, AnnotationModel, SessionEvent
from config import Config

import logging
logger = logging.getLogger('gunicorn.error')


# Before the connection is upgraded to a websocket (and when a proxy keeps it
# on long-polling), the browser sends its queued messages in one request. The
# annotator emits an event per edit, so 16 (Engine.IO's default limit) is
# easily passed: "Too many packets in payload" and the socket is dropped.
from engineio.payload import Payload
Payload.max_decode_packets = 1000

socketio = SocketIO(async_mode='threading')

# who has the app open right now: username -> socket ids (one web worker)
ONLINE = {}


def is_online(username):
    return bool(ONLINE.get(username))


def _join_user():
    if not current_user.is_authenticated:
        return
    join_room(user_room(current_user.username))
    ONLINE.setdefault(current_user.username, set()).add(request.sid)


def user_room(username):
    return f"user:{username}"


def notify_user(username, event, data):
    """Push to every page that user has open"""
    socketio.emit(event, data, room=user_room(username))


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated or Config.LOGIN_DISABLED:
            return f(*args, **kwargs)
        else:
            disconnect()
    return wrapped


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@socketio.on('annotation')
@authenticated_only
def annotation(data):
    """A shape was created / changed / deleted: tell the others who have the
    same image open (only if the sender may edit that image)."""
    ann = data.get('annotation') if isinstance(data, dict) else None
    if not isinstance(ann, dict):
        return
    image_id, ann_id = _int(ann.get('image_id')), _int(ann.get('id'))
    if image_id is None or ann_id is None:
        return
    if AnnotationModel.objects(id=ann_id, image_id=image_id).only('id').first() is None:
        return
    if current_user.editable_images.filter(id=image_id).only('id').first() is None:
        return
    # not back to the sender: an echo arriving after a newer local edit
    # would put the older shape back (e.g. a box rotating back)
    emit('annotation', data, room=image_id, include_self=False)


def dataset_room(dataset_id):
    return f"dataset:{dataset_id}"


def _presence(image_id, dataset_id, active):
    """Tell who is working on an image: others on that image, and the
    dataset page (image cards show who is annotating)."""
    payload = {'image_id': image_id, 'active': active, 'username': current_user.username}
    emit('annotating', payload, room=image_id, include_self=False)
    if dataset_id is not None:
        emit('annotating', payload, room=dataset_room(dataset_id), include_self=False)


def _stop_annotating(image_id, idle_seconds=0):
    """Close the annotating session on an image (time log, presence).
    ``idle_seconds``: how long before now the person last did something
    (gone idle): that part is not counted."""
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        return
    start = session.get('annotating_time', time.time())
    end = max(start, time.time() - max(0, idle_seconds))
    image.add_event(SessionEvent.create(start, current_user, end=end))
    image.update(pull__annotating=current_user.username)
    _presence(image_id, image.dataset_id, False)


@socketio.on('watch_dataset')
@authenticated_only
def watch_dataset(data):
    """The dataset page listens for who starts / stops annotating its images."""
    dataset_id = _int(data.get('dataset_id')) if isinstance(data, dict) else None
    previous = session.get('watching')
    if previous is not None and previous != dataset_id:
        leave_room(dataset_room(previous))
        session['watching'] = None
    if dataset_id is None or current_user.datasets.filter(id=dataset_id).only('id').first() is None:
        return False
    join_room(dataset_room(dataset_id))
    session['watching'] = dataset_id
    return True


def chat_room(dataset_id):
    return f"chat:{dataset_id}"


@socketio.on('watch_chat')
@authenticated_only
def watch_chat(data):
    """A page with a dataset's chat open (dataset page, annotator) gets its
    new messages."""
    dataset_id = _int(data.get('dataset_id')) if isinstance(data, dict) else None
    previous = session.get('chatting')
    # a page closing its chat leaves only its own room (the next page may
    # already have joined another one)
    leave = _int(data.get('leave')) if isinstance(data, dict) else None
    if dataset_id is None and leave is not None and leave != previous:
        return False
    if previous is not None and previous != dataset_id:
        leave_room(chat_room(previous))
        session['chatting'] = None
    if dataset_id is None or current_user.datasets.filter(id=dataset_id).only('id').first() is None:
        return False
    join_room(chat_room(dataset_id))
    session['chatting'] = dataset_id
    return True


@socketio.on('annotating')
@authenticated_only
def annotating(data):
    """
    Socket for handling image locking and time logging. Anyone who can open
    the image gets its live updates; only those who may edit it show up as
    annotating it (and have their time logged).
    """
    if not isinstance(data, dict):
        return
    image_id = _int(data.get('image_id'))
    active = bool(data.get('active'))

    image = current_user.images.filter(id=image_id).first() if image_id is not None else None
    if image is None:
        return
    editing = current_user.editable_images.filter(id=image_id).only('id').first() is not None

    if active:
        previous = session.get('annotating')
        if previous is not None and previous != image_id:
            leave_room(previous)
            _stop_annotating(previous)
            session['annotating'] = None
        join_room(image_id)
        if editing and previous != image_id:
            logger.info(f'{current_user.username} has started annotating image {image_id}')
            session['annotating'] = image_id
            session['annotating_time'] = time.time()
            image.update(add_to_set__annotating=current_user.username)
            _presence(image_id, image.dataset_id, True)
    else:
        # idle (no input for a while, tab hidden): the time stops, but the
        # page keeps getting the image's live updates
        if not data.get('idle'):
            leave_room(image_id)
        if session.get('annotating') == image_id:
            idle_ms = _int(data.get('idle_ms')) if data.get('idle') else None
            _stop_annotating(image_id, (idle_ms or 0) / 1000)
            session['annotating'] = None
            session['time'] = None


@socketio.on('connect')
def connect():
    logger.info(f'Socket connection created with {current_user.username}')
    _join_user()


@socketio.on('join_user')
def join_user(data=None):
    """Sent by the page once it knows who is logged in. The socket keeps the
    session it connected with: False tells a page that logged in after
    connecting to reconnect."""
    _join_user()
    return bool(current_user.is_authenticated)


@socketio.on('disconnect')
def disconnect():
    # a web terminal of this page ends with it
    from .terminal import close_for
    close_for(request.sid)
    from .train_live import close_for as stop_watching
    stop_watching(request.sid)
    if current_user.is_authenticated:
        logger.info(f'Socket connection has been disconnected with {current_user.username}')
        sids = ONLINE.get(current_user.username)
        if sids is not None:
            sids.discard(request.sid)
            if not sids:
                ONLINE.pop(current_user.username, None)
        image_id = session.get('annotating')
        if image_id is not None:
            _stop_annotating(image_id)
               
