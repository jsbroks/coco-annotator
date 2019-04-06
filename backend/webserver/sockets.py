import functools
import time

from flask import session
from flask_socketio import (
    SocketIO,
    disconnect,
    join_room,
    leave_room,
    emit
)
from flask_login import current_user

from database import ImageModel, SessionEvent
from config import Config

import logging
logger = logging.getLogger('gunicorn.error')


socketio = SocketIO()


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated or Config.LOGIN_DISABLED:
            return f(*args, **kwargs)
        else:
            disconnect()
    return wrapped


@socketio.on('annotation')
@authenticated_only
def annotation(data):
    emit('annotation', data, broadcast=True)


@socketio.on('annotating')
@authenticated_only
def annotating(data):
    """
    Socket for handling image locking and time logging
    """

    image_id = data.get('image_id')
    active = data.get('active')
    
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        # invalid image ID
        return
    
    emit('annotating', {
        'image_id': image_id,
        'active': active,
        'username': current_user.username
    }, broadcast=True, include_self=False)

    if active:
        logger.info(f'{current_user.username} has started annotating image {image_id}')
        # Remove user from pervious room
        previous = session.get('annotating')
        if previous is not None:
            leave_room(previous)
            previous_image = ImageModel.objects(id=previous).first()

            if previous_image is not None:

                start = session.get('annotating_time', time.time())
                event = SessionEvent.create(start, current_user)

                previous_image.add_event(event)
                previous_image.update(
                    pull__annotating=current_user.username
                )

                emit('annotating', {
                    'image_id': previous,
                    'active': False,
                    'username': current_user.username
                }, broadcast=True, include_self=False)

        join_room(image_id)
        session['annotating'] = image_id
        session['annotating_time'] = time.time()
        image.update(add_to_set__annotating=current_user.username)
    else:
        leave_room(image_id)

        start = session.get('annotating_time', time.time())
        event = SessionEvent.create(start, current_user)

        image.add_event(event)
        image.update(
            pull__annotating=current_user.username
        )

        session['annotating'] = None
        session['time'] = None


@socketio.on('connect')
def connect():
    logger.info(f'Socket connection created with {current_user.username}')


@socketio.on('disconnect')
def disconnect():
    if current_user.is_authenticated:
        logger.info(f'Socket connection has been disconnected with {current_user.username}')
        image_id = session.get('annotating')

        # Remove user from room
        if image_id is not None:
            image = ImageModel.objects(id=image_id).first()
            if image is not None:
                start = session.get('annotating_time', time.time())
                event = SessionEvent.create(start, current_user)
        
                image.add_event(event)
                image.update(
                    pull__annotating=current_user.username
                )
                emit('annotating', {
                    'image_id': image_id,
                    'active': False,
                    'username': current_user.username
                }, broadcast=True, include_self=False)
               
