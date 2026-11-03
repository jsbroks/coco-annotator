"""Parent categories: several per category, COCO round trip."""
import io
import json


def test_parents_create_update_import_export(world):
    from database import CategoryModel
    c = world["client"]
    r = c.post("/api/category/", json={"name": "sedan", "supercategories": ["car", " vehicle ", "car"]})
    cat = r.get_json()
    assert cat["supercategories"] == ["car", "vehicle"] and cat["supercategory"] == "car"

    # the old single field still works, a list in one string is split
    r = c.post("/api/category/", json={"name": "cablecar", "supercategory": "rail, vehicle"})
    assert r.get_json()["supercategories"] == ["rail", "vehicle"]

    r = c.put(f"/api/category/{cat['id']}", json={"name": "sedan", "supercategories": ["vehicle"]})
    assert r.status_code == 200
    model = CategoryModel.objects(id=cat["id"]).first()
    assert model.parents() == ["vehicle"] and model.supercategory == "vehicle"
    # nothing else changed: parents alone count as a change
    r = c.put(f"/api/category/{cat['id']}", json={"name": "sedan", "supercategories": []})
    assert r.get_json().get("success") and CategoryModel.objects(id=cat["id"]).first().supercategory == ""

    # import: new categories take their parents from the file
    d = world["dataset"]["id"]
    coco = {"images": [], "annotations": [],
            "categories": [{"id": 1, "name": "ferry", "supercategory": "boat"},
                           {"id": 2, "name": "kayak", "supercategories": ["boat", "small"]}]}
    r = c.post(f"/api/dataset/{d}/coco", data={"coco": (io.BytesIO(json.dumps(coco).encode()), "c.json")},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    assert CategoryModel.objects(name="ferry").first().parents() == ["boat"]
    assert CategoryModel.objects(name="kayak").first().parents() == ["boat", "small"]

    # export carries both fields
    from webserver.util import coco_util
    from database import DatasetModel
    out = coco_util.get_dataset_coco(DatasetModel.objects(id=d).first())
    kayak = next(x for x in out["categories"] if x["name"] == "kayak")
    assert kayak["supercategory"] == "boat" and kayak["supercategories"] == ["boat", "small"]


def test_datasets_grouped_by_parent(world):
    c = world["client"]
    c.post("/api/category/", json={"name": "lion", "supercategories": ["beast"]})
    c.post("/api/category/", json={"name": "rock", "supercategories": []})
    c.post("/api/dataset/", json={"name": "safari", "categories": ["lion"]})
    c.post("/api/dataset/", json={"name": "quarry", "categories": ["rock"]})
    body = c.get("/api/dataset/data", query_string={"limit": 50}).get_json()
    assert {"name": "beast", "count": 1} in body["parents"] and body["no_parent"] >= 1
    assert "safari" in body["names"]
    names = [d["name"] for d in c.get("/api/dataset/data", query_string={"parent": "beast"}).get_json()["datasets"]]
    assert names == ["safari"]
    none = [d["name"] for d in c.get("/api/dataset/data", query_string={"parent": "-", "limit": 50}).get_json()["datasets"]]
    assert "quarry" in none and "safari" not in none
    found = c.get("/api/dataset/data", query_string={"q": "SAF"}).get_json()
    assert [d["name"] for d in found["datasets"]] == ["safari"] and found["total"] == 1


def test_recreate_deleted_dataset(world, dataset_directory):
    import os
    from PIL import Image
    from database import DatasetModel, ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "again"}).get_json()["id"]
    folder = os.path.join(dataset_directory, "again")
    Image.new("RGB", (40, 30)).save(os.path.join(folder, "x.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    c.delete(f"/api/dataset/{ds}")

    listed = c.get("/api/dataset/data").get_json()["trashed"]
    assert {"id": ds, "name": "again", "images": 1} in listed

    r = c.post("/api/dataset/", json={"name": "again"})
    assert r.status_code == 409 and r.get_json()["code"] == "in_trash" and r.get_json()["images"] == 1

    r = c.post("/api/dataset/", json={"name": "again", "replace_trashed": True})
    assert r.status_code == 200 and r.get_json()["scanned"] is True
    new_id = r.get_json()["id"]
    assert new_id != ds and DatasetModel.objects(id=ds).first() is None
    assert os.path.exists(os.path.join(folder, "x.jpg"))
    assert ImageModel.objects(dataset_id=new_id, deleted=False).count() == 1

    # a live dataset of that name: plain "exists"
    r = c.post("/api/dataset/", json={"name": "again"})
    assert r.status_code == 400 and r.get_json()["code"] == "exists"


def test_recreate_deleted_category(world):
    from database import CategoryModel
    c = world["client"]
    cat = c.post("/api/category/", json={"name": "phoenix"}).get_json()
    c.delete(f"/api/category/{cat['id']}")
    r = c.post("/api/category/", json={"name": "phoenix", "supercategories": ["myth"]})
    body = r.get_json()
    assert r.status_code == 200 and body["restored"] and body["id"] == cat["id"]
    assert CategoryModel.objects(id=cat["id"]).first().parents() == ["myth"]
    # picking a deleted category by name for a new dataset brings it back
    c.delete(f"/api/category/{cat['id']}")
    c.post("/api/dataset/", json={"name": "myths", "categories": ["phoenix"]})
    assert CategoryModel.objects(id=cat["id"]).first().deleted is False


def test_parent_paths_and_same_name_under_other_parents(world):
    """Parent paths of any depth: a name can repeat under another parent."""
    from database import CategoryModel
    c = world["client"]
    made = []
    for group in ("路口", "走廊"):
        r = c.post("/api/category/", json={"name": "人", "supercategories": [f" 場景 / {group} "]})
        assert r.status_code == 200, r.get_json()
        made.append(r.get_json()["id"])
    assert made[0] != made[1]
    first = CategoryModel.objects(id=made[0]).first()
    assert first.supercategories == ["場景/路口"] and first.supercategory == "場景/路口"
    # the same name twice under one parent is still refused
    assert c.post("/api/category/", json={"name": "人", "supercategories": ["場景/路口"]}).status_code == 400
    assert CategoryModel.ancestors("a/b/c") == ["a", "a/b", "a/b/c"]

    # a dataset made from ids keeps exactly those categories
    r = c.post("/api/dataset/", json={"name": "scene_hall", "categories": [made[1]]})
    assert r.status_code == 200 and r.get_json()["categories"] == [made[1]]

    # Datasets page: tabs for each level of the path
    data = c.get("/api/dataset/data", query_string={"limit": 50}).get_json()
    names = {p["name"] for p in data["parents"]}
    assert {"場景", "場景/走廊"} <= names
    shown = c.get("/api/dataset/data", query_string={"limit": 50, "parent": "場景"}).get_json()
    assert [d["name"] for d in shown["datasets"]] == ["scene_hall"]
    CategoryModel.objects(id__in=made).delete()


def test_old_unique_index_dropped():
    from database import CategoryModel
    collection = CategoryModel._get_collection()
    collection.create_index([("name", 1), ("creator", 1)], name="name_1_creator_1")
    CategoryModel.drop_old_unique_index()
    assert "name_1_creator_1" not in collection.index_information()
