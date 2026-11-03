"""COCO import from other tools: box-only annotations, folders in file
names, RLE masks and categories that exist outside the dataset."""
import io
import json

import pytest

pytestmark = pytest.mark.order(-1)


def _import(client, dataset_id, coco):
    data = {"coco": (io.BytesIO(json.dumps(coco).encode()), "coco.json")}
    return client.post(f"/api/dataset/{dataset_id}/coco", data=data,
                       content_type="multipart/form-data")


def test_import_from_other_tools(world):
    from database import AnnotationModel, CategoryModel, DatasetModel, TaskModel

    c = world["client"]
    ds = world["dataset"]["id"]
    image = world["images"][0]
    # a category that exists but is not part of this dataset
    c.post("/api/category/", json={"name": "buoy"})
    buoy = CategoryModel.objects(name="buoy").first()
    assert buoy.id not in DatasetModel.objects(id=ds).first().categories

    before = AnnotationModel.objects(image_id=image["id"], deleted=False).count()
    coco = {
        "images": [{"id": 7, "file_name": "train/images/" + image["file_name"],
                    "width": 320, "height": 200}],
        "categories": [{"id": 1, "name": "buoy"}],
        "annotations": [
            # box only, as exported by detectors / Roboflow / YOLO converters
            {"id": 1, "image_id": 7, "category_id": 1, "bbox": [10, 20, 30, 40],
             "segmentation": [], "area": 1200},
            # uncompressed RLE mask
            {"id": 2, "image_id": 7, "category_id": 1, "iscrowd": 1,
             "segmentation": {"size": [200, 320], "counts": [200 * 50, 200 * 20, 200 * 250]},
             "bbox": [50, 0, 20, 200]},
        ],
    }
    r = _import(c, ds, coco)
    assert r.status_code == 200, r.data
    task = TaskModel.objects(id=r.get_json()["id"]).first()
    assert task.completed and task.errors == 0, task.logs

    anns = AnnotationModel.objects(image_id=image["id"], deleted=False, category_id=buoy.id)
    assert anns.count() == 2, task.logs
    box = [a for a in anns if a.isbbox][0]
    assert box.segmentation == [[10, 20, 40, 20, 40, 60, 10, 60]]
    mask = [a for a in anns if not a.isbbox][0]
    assert len(mask.segmentation[0]) >= 8
    assert buoy.id in DatasetModel.objects(id=ds).first().categories
    assert AnnotationModel.objects(image_id=image["id"], deleted=False).count() == before + 2
    from database import ImageModel
    assert ImageModel.objects(id=image["id"]).first().num_annotations >= 2
