from flask_restplus import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage
from imantics import Image as ImanticsImage
from flask_login import login_required
from ..config import Config
from PIL import Image

if len(Config.MASK_RCNN_FILE) != 0:
    from ..util.mask_rcnn import model as maskrcnn

api = Namespace('model', description='Model related operations')


image_upload = reqparse.RequestParser()
image_upload.add_argument('image', location='files', type=FileStorage, required=True, help='Image')

@api.route('/maskrcnn')
class MaskRCNN(Resource):

    @login_required
    @api.expect(image_upload)
    def post(self):
        """ COCO data test """
        if len(Config.MASK_RCNN_FILE) == 0:
            return {"coco": {}}

        args = image_upload.parse_args()
        im = Image.open(args.get('image'))
        coco = maskrcnn.detect(im)
        return {"coco": coco}