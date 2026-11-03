from flask import send_file
from flask_restx import Namespace, Resource, reqparse
from flask_login import login_required, current_user

import datetime
import os
from ..util import query_util

from database import (
    ExportModel,
    DatasetModel,
    fix_ids
)


api = Namespace('export', description='Export related operations')


def export_dataset(export):
    """The dataset an export belongs to, if the user may see / download it.
    A merged export needs every one of its datasets."""
    ids = list(getattr(export, 'dataset_ids', None) or []) or [export.dataset_id]
    if export.dataset_id not in ids:
        ids.insert(0, export.dataset_id)
    primary = None
    for dataset_id in ids:
        dataset = current_user.datasets.filter(id=dataset_id).first()
        if dataset is None or not current_user.can_download(dataset):
            return None
        if dataset_id == export.dataset_id:
            primary = dataset
    return primary


@api.route('/<int:export_id>')
class DatasetExports(Resource):

    @login_required
    def get(self, export_id):
        """ Returns exports """
        export = ExportModel.objects(id=export_id).first()
        if export is None:
            return {"message": "Invalid export ID"}, 400

        dataset = export_dataset(export)
        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400

        time_delta = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - export.created_at
        d = fix_ids(export)
        d['ago'] = query_util.td_format(time_delta)
        return d
    
    @login_required
    def delete(self, export_id):
        """ Returns exports """
        export = ExportModel.objects(id=export_id).first()
        if export is None:
            return {"message": "Invalid export ID"}, 400

        dataset = export_dataset(export)
        if dataset is None:
            return {"message": "You do not have permission to manage this dataset's exports"}, 403

        # remove the file too (only inside the dataset's .exports folder)
        exports_dir = os.path.realpath(os.path.join(dataset.directory, ".exports"))
        path = os.path.realpath(export.path or "")
        if path.startswith(exports_dir + os.sep) and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

        export.delete()
        return {'success': True}


@api.route('/<int:export_id>/download')
class DatasetExports(Resource):

    @login_required
    def get(self, export_id):
        """ Returns exports """

        export = ExportModel.objects(id=export_id).first()
        if export is None:
            return {"message": "Invalid export ID"}, 400

        dataset = export_dataset(export)
        if dataset is None:
            return {"message": "You do not have permission to download the dataset's annotations"}, 403

        if not export.path or not os.path.isfile(export.path):
            return {"message": "The export file no longer exists"}, 404

        ext = os.path.splitext(export.path)[1] or ".json"
        kind = "-".join(export.tags[:2]) if export.tags and export.tags[0] == "YOLO" else "COCO"
        name = "+".join(export.dataset_names) if getattr(export, 'dataset_names', None) else dataset.name
        return send_file(export.path, download_name=f"{name[:120]}-{kind.lower()}-{export.id}{ext}",
                         as_attachment=True)

