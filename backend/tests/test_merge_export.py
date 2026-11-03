"""Several datasets exported together into one file."""
import os
import zipfile

from webserver.util.passwords import hash_password


def _login(username):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, is_admin=False).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def _dataset(client, dataset_directory, name, categories, files):
    from PIL import Image
    ds = client.post("/api/dataset/", json={"name": name, "categories": categories}).get_json()["id"]
    folder = os.path.join(dataset_directory, name)
    os.makedirs(folder, exist_ok=True)
    for f in files:
        Image.new("RGB", (100, 50), (20, 60, 90)).save(os.path.join(folder, f))
    client.get(f"/api/dataset/{ds}/scan")
    images = {i["file_name"]: i["id"] for i in client.get(f"/api/dataset/{ds}/data").get_json()["images"]}
    return ds, images


def test_merged_export(dataset_directory):
    from database import CategoryModel, ExportModel
    alice = _login("mx_alice")
    bob = _login("mx_bob")
    # Alice's two sets; B uses another "Car" category (same name, other id)
    # plus a category only it has; the same file name in both
    a, a_images = _dataset(alice, dataset_directory, "mx A", ["car"], ["same.jpg", "a2.jpg"])
    b, b_images = _dataset(alice, dataset_directory, "mx B", ["truck"], ["same.jpg"])
    c, _ = _dataset(bob, dataset_directory, "mx C", ["car"], ["c.jpg"])
    bob.post(f"/api/dataset/{c}/members", json={"add": ["mx_alice"]})
    from database import DatasetModel
    by_name = lambda ds: {c.name: c.id for c in CategoryModel.objects(id__in=DatasetModel.objects(id=ds).first().categories)}
    car_a = by_name(a)["car"]
    truck = by_name(b)["truck"]
    car_b = CategoryModel(name="Car", creator="mx_bob_" + str(b)).save().id
    DatasetModel.objects(id=b).update(set__categories=[car_b, truck])
    assert car_a != car_b

    def box(client, image_id, cat, x):
        r = client.post("/api/annotation/", json={"image_id": image_id, "category_id": cat,
                                                  "segmentation": [[x, 10, x + 20, 10, x + 20, 30, x, 30]]})
        assert r.status_code == 200, r.data
    box(alice, a_images["same.jpg"], car_a, 5)
    box(alice, b_images["same.jpg"], car_b, 40)
    box(alice, b_images["same.jpg"], truck, 70)

    # B is offered with its categories; C (Bob's, Alice only a member) is not
    cands = alice.get(f"/api/dataset/{a}/merge_candidates").get_json()["datasets"]
    offered = next(d for d in cands if d["id"] == b)
    assert {x["name"] for x in offered["categories"]} == {"Car", "truck"} and offered["images"] == 1
    assert c not in [d["id"] for d in cands]
    mine = [d["id"] for d in alice.get("/api/dataset/exportable").get_json()["datasets"]]
    assert a in mine and b in mine and c not in mine
    r = alice.get(f"/api/dataset/{a}/export", query_string={"format": "yolo", "with_datasets": str(c)})
    assert r.status_code == 403

    r = alice.get(f"/api/dataset/{a}/export", query_string={
        "format": "yolo", "yolo_task": "detect", "with_images": "true", "folder": "both",
        "categories": f"{car_a},{car_b},{truck}", "with_datasets": str(b)})
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=a).order_by("-id").first()
    assert export.dataset_ids == [a, b] and export.dataset_names == ["mx A", "mx B"]
    with zipfile.ZipFile(export.path) as zf:
        names = zf.namelist()
        assert zf.read("classes.txt").decode().split() == ["car", "truck"]  # one "car"
        labels = sorted(n for n in names if n.endswith(".txt") and "/labels/" in n)
        assert labels == ["both/train/labels/mx_A_same.txt", "both/train/labels/mx_B_same.txt"]
        assert [l.split()[0] for l in zf.read("both/train/labels/mx_B_same.txt").decode().splitlines()] == ["0", "1"]
        assert zf.read("both/train/labels/mx_A_same.txt").decode().split()[0] == "0"
        assert any(n.endswith("mx_B_same.jpg") for n in names)

    # listed in both datasets; others can not download it
    for ds in (a, b):
        row = next(x for x in alice.get(f"/api/dataset/{ds}/exports").get_json() if x["id"] == export.id)
        assert row["merged"] == ["mx A", "mx B"]
    assert bob.get(f"/api/export/{export.id}/download").status_code == 403
    r = alice.get(f"/api/export/{export.id}/download")
    assert r.status_code == 200 and "mx A+mx B" in r.headers["Content-Disposition"]

    # categories of other datasets are refused
    stranger_cat = CategoryModel(name="zzz_mx", creator="mx_bob").save().id
    r = alice.get(f"/api/dataset/{a}/export", query_string={"categories": str(stranger_cat), "with_datasets": str(b)})
    assert r.status_code == 400
