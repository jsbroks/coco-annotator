from flask import send_file
from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required, current_user

import datetime
from ..util import query_util

from database import (
    ExportModel,
    DatasetModel,
    fix_ids
)


api = Namespace('export', description='Export related operations')


@api.route('/<int:export_id>')
class DatasetExports(Resource):

    @login_required
    def get(self, export_id):
        """ Returns exports """
        export = ExportModel.objects(id=export_id).first()
        if export is None:
            return {"message": "Invalid export ID"}, 400

        dataset = current_user.datasets.filter(id=export.dataset_id).first()
        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        
        time_delta = datetime.datetime.utcnow() - export.created_at
        d = fix_ids(export)
        d['ago'] = query_util.td_format(time_delta)
        return d
    
    @login_required
    def delete(self, export_id):
        """ Returns exports """
        export = ExportModel.objects(id=export_id).first()
        if export is None:
            return {"message": "Invalid export ID"}, 400

        dataset = current_user.datasets.filter(id=export.dataset_id).first()
        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        
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

        dataset = current_user.datasets.filter(id=export.dataset_id).first()
        if dataset is None:
            return {"message": "Invalid dataset ID"}, 400
        
        if not current_user.can_download(dataset):
            return {"message": "You do not have permission to download the dataset's annotations"}, 403

        return send_file(export.path, attachment_filename=f"{dataset.name.encode('utf-8')}-{'-'.join(export.tags).encode('utf-8')}.json", as_attachment=True)

