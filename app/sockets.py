import functools
import json

from flask import session
from flask_socketio import SocketIO, disconnect, join_room, leave_room, emit
from flask_login import current_user

from .models import ImageModel
from .config import Config


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

    image_id = data.get('image_id')
    emit('annotation', data, broadcast=True)

@socketio.on('annotating')
@authenticated_only
def annotating(data):
    """
    Socket for handling image locking
    """

    image_id = data.get('image_id')
    active = data.get('active')
    
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        # invalid image ID
        return True
    
    emit('annotating', {
        'image_id': image_id,
        'active': active,
        'username': current_user.username
    }, broadcast=True, include_self=False)

    if active:
        # Remove user from pervious room
        previous = session.get('annotating')
        if previous is not None:
            leave_room(previous)
            previous_image = ImageModel.objects(id=previous).first()

            if previous_image is not None:
                previous_image.update(pull__annotating=current_user.username)
                emit('annotating', {
                    'image_id': previous,
                    'active': False,
                    'username': current_user.username
                }, broadcast=True, include_self=False)

        join_room(image_id)
        session['annotating'] = image_id
        image.update(add_to_set__annotating=current_user.username)
    else:
        leave_room(image_id)
        session['annotating'] = None
        image.update(pull__annotating=current_user.username)


@socketio.on('disconnect')
def disconnect():
    if current_user.is_authenticated:
        image_id = session.get('annotating')

        # Remove user from room
        if image_id is not None:
            image = ImageModel.objects(id=image_id).first()
            if image is not None:
                image.update(pull__annotating=current_user.username)
               
