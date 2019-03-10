from flask_restplus import Namespace, Resource, reqparse
from flask_login import login_required

import datetime

api = Namespace('model', description='Model related operations')


@api.route('/')
class Annotation(Resource):

    @login_required
    def get(self):
        """ COCO data test """
        return {
            "coco": {
                "images": [
                    {
                        "id": 1653,
                        "path": "/datasets/66666/c/1467808_f8c0.jpg",
                        "dataset_id": 50,
                        "width": 750,
                        "height": 422,
                        "file_name": "1467808_f8c0.jpg",
                        "annotating": ["123"],
                        "annotated": True,
                        "category_ids": [8, 33],
                        "metadata": {}
                    }
                ],
                "categories": [
                    {
                        "id": 8,
                        "name": "asdf",
                        "supercategory": "",
                        "color": "#959b4c",
                        "metadata": {},
                        "creator": "unknown",
                        "keypoints": [
                            "left foot",
                            "right foot",
                            "left hip",
                            "right hip",
                            "chest",
                            "left shold",
                            "right shold",
                            "head"
                        ],
                        "skeleton": [
                            [5, 2],
                            [4, 7],
                            [4, 5],
                            [6, 8],
                            [7, 5],
                            [7, 6],
                            [3, 5],
                            [1, 3],
                            [11, 12]
                        ]
                    },
                    {
                        "id": 33,
                        "name": "dddddddddddddddd",
                        "supercategory": "",
                        "color": "#24acc4",
                        "metadata": {},
                        "creator": "unknown",
                        "keypoints": ["cat", "dog"],
                        "skeleton": []
                    }
                ],
                "annotations": [
                    {
                        "id": 1081,
                        "image_id": 1653,
                        "category_id": 8,
                        "dataset_id": 50,
                        "segmentation": [
                            [
                            116.4,
                            89,
                            124,
                            79.2,
                            392.7,
                            0,
                            401.9,
                            0,
                            417.9,
                            0,
                            430.3,
                            50.4,
                            462.2,
                            213.4,
                            360.6,
                            256.2,
                            177.3,
                            329.2,
                            158.7,
                            264.4,
                            117,
                            88.8
                            ]
                        ],
                        "area": 74644,
                        "bbox": [117, 0, 345, 329],
                        "iscrowd": False,
                        "creator": "test",
                        "width": 750,
                        "height": 422,
                        "color": "#575bdd",
                        "metadata": {},
                        "paper_object": []
                    },
                    {
                        "id": 1082,
                        "image_id": 1653,
                        "category_id": 33,
                        "dataset_id": 50,
                        "segmentation": [
                            [
                            659.3,
                            186.7,
                            668.5,
                            188.2,
                            676.6,
                            192.2,
                            688,
                            194.8,
                            698.3,
                            202.9,
                            672.4,
                            219.4,
                            660.1,
                            237.8,
                            635.6,
                            255.6,
                            624.7,
                            261.7,
                            612.1,
                            272.1,
                            606.3,
                            268.1,
                            599.8,
                            258.6,
                            597.5,
                            246.9,
                            598.9,
                            237.7,
                            603,
                            229.6,
                            609.2,
                            223.1,
                            630.5,
                            208.3,
                            634.6,
                            199.7,
                            641.1,
                            192.8,
                            649.6,
                            188.3
                            ]
                        ],
                        "area": 3996,
                        "bbox": [598, 187, 100, 85],
                        "iscrowd": False,
                        "creator": "test",
                        "width": 750,
                        "height": 422,
                        "color": "#63ef65",
                        "metadata": {},
                        "paper_object": []
                    },
                    {
                        "id": 1083,
                        "image_id": 1653,
                        "category_id": 33,
                        "dataset_id": 50,
                        "segmentation": [
                            [
                                320.6,
                                291.2,
                                333.5,
                                294.1,
                                343.6,
                                302,
                                360.1,
                                304.9,
                                372.2,
                                311.6,
                                401.7,
                                347.4,
                                408.4,
                                359.7,
                                411.6,
                                373.3,
                                409,
                                397.9,
                                409.4,
                                422,
                                332.5,
                                421.1,
                                329.3,
                                416.4,
                                310.9,
                                399.3,
                                283.6,
                                365.4,
                                278.4,
                                353.1,
                                276.9,
                                343.7,
                                278.9,
                                329.3,
                                281.8,
                                322.4,
                                292.8,
                                309.8,
                                297.3,
                                302.3,
                                303.7,
                                296.4,
                                311.6,
                                292.5
                            ]
                        ],
                        "area": 12803,
                        "bbox": [277, 291, 135, 131],
                        "iscrowd": False,
                        "creator": "test",
                        "width": 750,
                        "height": 422,
                        "color": "#e2bd34",
                        "metadata": {},
                        "paper_object": []
                    }
                ]
            }
        }