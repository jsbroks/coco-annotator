import functools
import json

from flask import session
from flask_socketio import SocketIO, disconnect, join_room, leave_room, emit
from flask_login import current_user

from .models import ImageModel


socketio = SocketIO()


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


@socketio.on('annotating')
@authenticated_only
def annotate(image):

    image_id = image.get('image_id')
    active = image.get('active')
    
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        # invalid image ID
        return True
    
    emit('annotate', {
        'image_id': image_id,
        'active': active,
        'username': current_user.username
    }, broadcast=True)

    if active:
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

        # Remove user from room
        if session.get('annotating') is not None:
            image = ImageModel.objects(id=image_id).first()
            if image is not None:
                image.update(pull__annotating=current_user.username)
               
