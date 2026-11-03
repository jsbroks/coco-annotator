from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage
from flask_login import login_required, current_user

from database import ActivityModel, ImageModel, ModelInfoModel
from flask import send_file
from ..util.sam import sam
from ..util.yolo import yolo
from ..util import mediapipe_models
from ..util import preannotate
from ..sockets import socketio

import logging

logger = logging.getLogger('gunicorn.error')

api = Namespace('model', description='AI-assisted annotation (Segment Anything, your YOLO models)')


sam_args = reqparse.RequestParser()
sam_args.add_argument('points', location='json', type=list, default=[],
                      help='[[x, y], ...] prompt points in image pixels')
sam_args.add_argument('labels', location='json', type=list, default=[],
                      help='1 = foreground, 0 = background, one per point')
sam_args.add_argument('box', location='json', type=list, default=None,
                      help='[x1, y1, x2, y2] prompt box in image pixels')


@api.route('/')
class ModelStatus(Resource):

    @login_required
    def get(self):
        """ Which AI-assist models are available """
        return {"sam": sam.status(), "yolo": yolo.status()}


@api.route('/sam/<int:image_id>')
class SegmentAnything(Resource):

    @login_required
    @api.expect(sam_args)
    def post(self, image_id):
        """ Segment an object from point and/or box prompts """
        if not sam.available:
            return {"disabled": True, "message": "SAM is not available on this server"}, 400

        args = sam_args.parse_args()
        points = args.get('points') or []
        labels = args.get('labels') or []
        box = args.get('box')

        if not points and not box:
            return {"message": "Provide at least one point or a box"}, 400
        if labels and len(labels) != len(points):
            return {"message": "labels must match points"}, 400
        if box is not None and len(box) != 4:
            return {"message": "box must be [x1, y1, x2, y2]"}, 400

        # only images this user can open
        image_model = current_user.images.filter(id=image_id, deleted=False).first()
        if not image_model:
            return {"message": "Invalid image ID"}, 400

        try:
            polygons, score, area = sam.predict(
                image_id, image_model.path, points=points, labels=labels, box=box
            )
        except Exception as e:
            logger.exception("SAM prediction failed")
            return {"message": f"SAM prediction failed: {e}"}, 500

        return {"segmentation": polygons, "score": score, "area": area}


@api.route('/sam/<int:image_id>/prepare')
class SegmentAnythingPrepare(Resource):

    @login_required
    def post(self, image_id):
        """ Start computing the SAM image embedding in the background """
        if not sam.available:
            return {"disabled": True, "message": "SAM is not available on this server"}, 400

        image_model = current_user.images.filter(id=image_id, deleted=False).first()
        if not image_model:
            return {"message": "Invalid image ID"}, 400

        sam.prepare_async(image_id, image_model.path)
        return {"success": True}


yolo_args = reqparse.RequestParser()
yolo_args.add_argument('model', location='json', required=True, help='Model file (.pt) name')
yolo_args.add_argument('conf', location='json', type=float, default=0.25,
                       help='Minimum confidence (0-1)')
yolo_args.add_argument('create_categories', location='json', type=bool, default=True,
                       help='Create categories for classes the dataset does not have')
yolo_args.add_argument('skip_annotated', location='json', type=bool, default=True,
                       help='Dataset only: skip images that already have annotations')


def _check_model(name):
    if not yolo.installed:
        return {"disabled": True, "message": "Model support is not installed on this server"}, 400
    try:
        yolo.path_for(name)
    except ValueError:
        return {"message": "Unknown model"}, 400
    meta = ModelInfoModel.objects(name=name).first()
    if meta is not None and not meta.enabled:
        return {"message": "This model is turned off (Models page)"}, 400
    return None


def _usage():
    """Per model: runs, annotations made, last run (from the activity log)."""
    usage = {}
    for entry in ActivityModel.objects(action='auto_annotate').only('detail', 'counts', 'user', 'updated_at'):
        name = (entry.detail or {}).get('model')
        if not name:
            continue
        u = usage.setdefault(name, {'runs': 0, 'annotations': 0, 'last_used': None, 'last_user': None})
        u['runs'] += 1
        u['annotations'] += (entry.counts or {}).get('annotations', 0) or 0
        if u['last_used'] is None or entry.updated_at > u['last_used']:
            u['last_used'], u['last_user'] = entry.updated_at, entry.user
    return usage


def _iso(value):
    return value.replace(microsecond=0).isoformat() + 'Z' if value else None


def _with_meta(models, include_usage=False):
    metas = {m.name: m for m in ModelInfoModel.objects(name__in=[m['name'] for m in models])}
    usage = _usage() if include_usage else {}
    out = []
    for m in models:
        meta = metas.get(m['name'])
        m = dict(m)
        m.update({
            'display_name': (meta.display_name if meta else '') or '',
            'note': (meta.note if meta else '') or '',
            'enabled': meta.enabled if meta else True,
            'default_conf': meta.default_conf if meta else None,
            'uploaded_by': meta.uploaded_by if meta else None,
            'uploaded_at': _iso(meta.uploaded_at) if meta and meta.uploaded_by else None,
        })
        if include_usage:
            u = usage.get(m['name'], {})
            m['usage'] = {'runs': u.get('runs', 0), 'annotations': u.get('annotations', 0),
                          'last_used': _iso(u.get('last_used')), 'last_user': u.get('last_user')}
        out.append(m)
    return out


def _conf(value):
    return min(max(float(value), 0.01), 1.0)


@api.route('/yolo')
class YoloModels(Resource):

    @login_required
    def get(self):
        """ Your models (.pt files in the models folder) with task and classes.
        ?all=1 (Models page): also turned-off models, with usage. """
        from flask import request
        manage = request.args.get('all') in ('1', 'true')
        if manage and not current_user.can_page('models'):
            return {"message": "You do not have access to the Models page", "code": "no_page"}, 403
        if not yolo.installed:
            return {"installed": False, "models": [], "sam": sam.status()}
        models = _with_meta(yolo.list(), include_usage=manage)
        if not manage:
            models = [m for m in models if m['enabled']]
        result = {"installed": True, "models": models, "can_manage": current_user.has_perm('manage_models'),
                  "ultralytics": yolo.ultralytics_installed, "mediapipe": yolo.mediapipe_installed}
        if manage:
            result.update({"device": yolo.device_name(), "directory": yolo.directory, "sam": sam.status()})
        return result


yolo_upload = reqparse.RequestParser()
yolo_upload.add_argument('file', location='files', type=FileStorage, required=True,
                         help='Ultralytics YOLO .pt, or MediaPipe .task / .tflite file')
yolo_upload.add_argument('overwrite', location='form', type=str, default='false')


@api.route('/yolo/upload')
class YoloUpload(Resource):

    @login_required
    @api.expect(yolo_upload)
    def post(self):
        """ Add a model (admins only: loading a .pt file runs code from it) """
        if not current_user.has_perm('manage_models'):
            return {"message": "Only admins can add models"}, 403
        if not yolo.installed:
            return {"disabled": True, "message": "Model support is not installed on this server"}, 400

        args = yolo_upload.parse_args()
        overwrite = str(args.get('overwrite')).lower() in ('1', 'true', 'yes')
        try:
            info = yolo.save_upload(args['file'], overwrite=overwrite)
        except FileExistsError as e:
            return {"exists": True, "message": f"A model named {e} already exists"}, 409
        except ValueError as e:
            return {"message": str(e)}, 400
        logger.info(f"User {current_user.username} added model {info['name']}")
        _record_added(info['name'], info.get('task'), overwrite)
        return {"success": True, "model": info}


def _record_added(name, task, replaced):
    import datetime
    meta = ModelInfoModel.objects(name=name).first() or ModelInfoModel(name=name)
    meta.uploaded_by = current_user.username
    meta.uploaded_at = datetime.datetime.utcnow()
    meta.save()
    from ..util import activity
    activity.record('model_upload', current_user, detail={'name': name, 'task': task, 'replaced': bool(replaced)},
                    text=name)


@api.route('/mediapipe/catalog')
class MediaPipeCatalog(Resource):

    @login_required
    def get(self):
        """ MediaPipe's official models: which are in the models folder """
        if not current_user.can_page('models'):
            return {"message": "You do not have access to the Models page", "code": "no_page"}, 403
        have = set(yolo.model_names())
        return {"installed": yolo.mediapipe_installed, "can_manage": current_user.has_perm('manage_models'),
                "models": [dict(entry, name=mediapipe_models.catalog_name(entry),
                                added=mediapipe_models.catalog_name(entry) in have)
                           for entry in mediapipe_models.CATALOG]}


@api.route('/mediapipe/install/<string:key>')
class MediaPipeInstall(Resource):

    @login_required
    def post(self, key):
        """ Download an official MediaPipe model into the models folder (admins only) """
        if not current_user.has_perm('manage_models'):
            return {"message": "Only admins can add models"}, 403
        if not yolo.mediapipe_installed:
            return {"disabled": True, "message": "MediaPipe is not installed on this server"}, 400
        try:
            info = yolo.install_official(key)
        except FileExistsError as e:
            return {"exists": True, "message": f"{e} is already there"}, 409
        except ValueError as e:
            return {"message": str(e)}, 400
        logger.info(f"User {current_user.username} added MediaPipe model {info['name']}")
        _record_added(info['name'], info.get('task'), False)
        return {"success": True, "model": info}


@api.route('/yolo/model/<path:name>')
class YoloModel(Resource):

    @login_required
    def delete(self, name):
        """ Remove a model file (admins only) """
        if not current_user.has_perm('manage_models'):
            return {"message": "Only admins can remove models"}, 403
        try:
            yolo.delete(name)
        except (ValueError, OSError):
            return {"message": "Unknown model"}, 400
        logger.info(f"User {current_user.username} removed model {name}")
        meta = ModelInfoModel.objects(name=name).first()
        display = meta.display_name if meta else ''
        ModelInfoModel.objects(name=name).delete()
        from ..util import activity
        activity.record('model_delete', current_user, detail={'name': name, 'display_name': display or None},
                        text=f"{name} {display or ''}")
        return {"success": True}

    @login_required
    def put(self, name):
        """ Change a model's display name, note, on/off, default confidence (admins only) """
        from flask import request
        if not current_user.has_perm('manage_models'):
            return {"message": "Only admins can change models"}, 403
        try:
            yolo.path_for(name)
        except ValueError:
            return {"message": "Unknown model"}, 400
        data = request.get_json(silent=True) or {}
        meta = ModelInfoModel.objects(name=name).first() or ModelInfoModel(name=name)
        before = {'display_name': meta.display_name or '', 'note': meta.note or '', 'enabled': meta.enabled,
                  'default_conf': meta.default_conf}
        if 'display_name' in data:
            meta.display_name = str(data['display_name'] or '').strip()[:100]
        if 'note' in data:
            meta.note = str(data['note'] or '').strip()[:2000]
        if 'enabled' in data:
            meta.enabled = bool(data['enabled'])
        if 'default_conf' in data:
            conf = data['default_conf']
            meta.default_conf = None if conf in (None, '') else _conf(conf)
        meta.save()
        after = {'display_name': meta.display_name or '', 'note': meta.note or '', 'enabled': meta.enabled,
                 'default_conf': meta.default_conf}
        changed = [k for k in after if after[k] != before[k]]
        if changed:
            from ..util import activity
            activity.record('model_update', current_user, text=f"{name} {meta.display_name or ''}", detail={
                'name': name, 'display_name': meta.display_name or None, 'changed': changed,
                'enabled': meta.enabled if 'enabled' in changed else None,
                'default_conf': meta.default_conf if 'default_conf' in changed else None})
        return {"success": True, "model": _with_meta([{"name": name}])[0]}


@api.route('/yolo/model/<path:name>/download')
class YoloModelDownload(Resource):

    @login_required
    def get(self, name):
        """ The .pt file (admins only) """
        if not current_user.has_perm('manage_models'):
            return {"message": "Only admins can download models"}, 403
        try:
            path = yolo.path_for(name)
        except ValueError:
            return {"message": "Unknown model"}, 400
        import os
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@api.route('/yolo/image/<int:image_id>')
class YoloImage(Resource):

    @login_required
    @api.expect(yolo_args)
    def post(self, image_id):
        """ Run a model on one image and save the predictions as annotations """
        args = yolo_args.parse_args()
        error = _check_model(args['model'])
        if error:
            return error

        image = current_user.editable_images.filter(id=image_id, deleted=False).first()
        if image is None:
            return {"message": "Invalid image ID"}, 400
        if not current_user.can_edit(image.dataset):
            return {"message": "You do not have permission to edit this dataset"}, 403

        try:
            result = preannotate.annotate_image(
                image, args['model'], conf=_conf(args['conf']),
                create_missing=args['create_categories'] and current_user.has_perm('create_categories'),
                user=current_user._get_current_object())
        except Exception as e:
            logger.exception("Model prediction failed")
            return {"message": f"Model prediction failed: {e}"}, 500
        return result


@api.route('/yolo/dataset/<int:dataset_id>')
class YoloDataset(Resource):

    @login_required
    @api.expect(yolo_args)
    def post(self, dataset_id):
        """ Run a model over a whole dataset in the background (a task) """
        args = yolo_args.parse_args()
        error = _check_model(args['model'])
        if error:
            return error

        dataset = current_user.editable_datasets.filter(id=dataset_id, deleted=False).first()
        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        if not current_user.can_edit(dataset):
            return {"message": "You do not have permission to edit this dataset"}, 403

        return preannotate.annotate_dataset(
            dataset, args['model'], conf=_conf(args['conf']),
            skip_annotated=args['skip_annotated'],
            create_missing=args['create_categories'] and current_user.has_perm('create_categories'),
            user=current_user._get_current_object(),
            socket=socketio)
