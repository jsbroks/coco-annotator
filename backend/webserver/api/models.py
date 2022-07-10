from flask_restplus import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage
from imantics import Mask
from flask_login import login_required
from config import Config
from PIL import Image
from database import ImageModel

import os
import logging

logger = logging.getLogger('gunicorn.error')


MASKRCNN_LOADED = os.path.isfile(Config.MASK_RCNN_FILE)
logger.info('MaskRCNN path: {}'.format(Config.MASK_RCNN_FILE))
if MASKRCNN_LOADED:
    from ..util.mask_rcnn import model as maskrcnn
else:
    logger.warning("MaskRCNN model is disabled.")

DEXTR_LOADED = os.path.isfile(Config.DEXTR_FILE)
if DEXTR_LOADED:
    from ..util.dextr import model as dextr
else:
    logger.warning("DEXTR model is disabled.")

api = Namespace('model', description='Model related operations')

DETECTRON2_LOADED = os.path.isfile(Config.DETECTRON2_FILE)
if DETECTRON2_LOADED:
    from ..util.detectron2_coco import model as detectron2_coco
    logger.info("Detectron2 model is enabled. Using model {}".format(Config.DETECTRON2_FILE))
else:
    logger.warning("DETECTRON2 model is disabled.")

MASKFORMER_LOADED = os.path.isfile(Config.MASK_FORMER_FILE)
if MASKFORMER_LOADED:
    from ..util.mask_former import model as maskformer
    logger.info("MaskFormer model is enabled. Using model {}".format(Config.MASK_FORMER_FILE))
else:
    logger.warning("MaskFormer model is disabled.")

MASKCOCO_LOADED = os.path.isfile(Config.MASK_COCO_FILE)
logger.info('MaskRCNN path: {}'.format(Config.MASK_COCO_FILE))
if MASKCOCO_LOADED:
    from ..util.mask_coco import model as maskcoco
else:
    logger.warning("MaskRCNN model is disabled.")

image_upload = reqparse.RequestParser()
image_upload.add_argument('image', location='files', type=FileStorage, required=True, help='Image')

dextr_args = reqparse.RequestParser()
dextr_args.add_argument('points', location='json', type=list, required=True)
dextr_args.add_argument('padding', location='json', type=int, default=50)
dextr_args.add_argument('threshold', location='json', type=int, default=80)


@api.route('/dextr/<int:image_id>')
class MaskRCNN(Resource):

    @login_required
    @api.expect(dextr_args)
    def post(self, image_id):
        """ COCO data test """

        if not DEXTR_LOADED:
            return {"disabled": True, "message": "DEXTR is disabled"}, 400

        args = dextr_args.parse_args()
        points = args.get('points')
        # padding = args.get('padding')
        # threshold = args.get('threshold')

        if len(points) != 4:
            return {"message": "Invalid points entered"}, 400
        
        image_model = ImageModel.objects(id=image_id).first()
        if not image_model:
            return {"message": "Invalid image ID"}, 400
        
        image = Image.open(image_model.path)
        result = dextr.predict_mask(image, points)

        return { "segmentation": Mask(result).polygons().segmentation }


@api.route('/maskrcnn')
class MaskRCNN(Resource):

    @login_required
    @api.expect(image_upload)
    def post(self):
        """ COCO data test """
        if not MASKRCNN_LOADED:
            return {"disabled": True, "coco": {}}

        args = image_upload.parse_args()
        im = Image.open(args.get('image'))
        coco = maskrcnn.detect(im)
        return {"coco": coco}

@api.route('/detectron2')
class MaskRCNN(Resource):

    @login_required
    @api.expect(image_upload)
    def post(self):
        """ COCO data test """
        if not DETECTRON2_LOADED:
            return {"disabled": True, "coco": {}}

        args = image_upload.parse_args()
        im = Image.open(args.get('image'))
        coco = detectron2_coco.detect(im)
        return {"coco": coco}

@api.route('/maskformer')
class MaskRCNN(Resource):

    @login_required
    @api.expect(image_upload)
    def post(self):
        """ COCO data test """
        if not MASKFORMER_LOADED:
            return {"disabled": True, "coco": {}}

        args = image_upload.parse_args()
        im = Image.open(args.get('image'))
        coco = maskformer.detect(im)
        return {"coco": coco}

@api.route('/maskcoco')
class MaskRCNN(Resource):

    @login_required
    @api.expect(image_upload)
    def post(self):
        """ COCO data test """
        if not MASKCOCO_LOADED:
            return {"disabled": True, "coco": {}}

        args = image_upload.parse_args()
        im = Image.open(args.get('image'))
        coco = maskcoco.detect(im)
        return {"coco": coco}
