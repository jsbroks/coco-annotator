"""Fixes from the upgrade-2026 review: thumbnails of same-named files,
purged categories, bulk accounts in another case, copy undo, category
metadata, trashed datasets."""
import os


def test_same_stem_images_get_their_own_cached_files(tmp_path):
    from PIL import Image
    from database import ImageModel
    paths = {}
    for ext, color in ((".jpg", "red"), (".png", "blue")):
        path = str(tmp_path / f"img1{ext}")
        Image.new("RGB", (40, 20), color).save(path)
        image = ImageModel(path=path)
        # the 1024 px thumbnail is there already (no database needed)
        Image.new("RGB", (40, 20), color).save(image.thumbnail_path())
        paths[ext] = image.small_thumbnail(10, 10)
    assert paths[".jpg"] != paths[".png"]
    with Image.open(paths[".jpg"]) as a, Image.open(paths[".png"]) as b:
        assert a.getpixel((0, 0))[0] > 200 and b.getpixel((0, 0))[2] > 200


def test_purged_category_leaves_datasets_and_stats_work(world):
    from database import CategoryModel, DatasetModel
    from webserver.util.trash import _purge_docs
    c = world["client"]
    ds = world["dataset"]["id"]
    cat = CategoryModel(name="review-fix-purged")
    cat.save()
    DatasetModel.objects(id=ds).update(push__categories=cat.id)
    assert _purge_docs("category", [cat]) == 1
    assert cat.id not in DatasetModel.objects(id=ds).first().categories
    # an id left behind by an older purge must not break the stats either
    DatasetModel.objects(id=ds).update(push__categories=987654)
    try:
        assert c.get(f"/api/dataset/{ds}/stats").status_code == 200
    finally:
        DatasetModel.objects(id=ds).update(pull__categories=987654)


def test_bulk_adds_an_existing_account_as_stored(world):
    from database import DatasetModel, UserModel
    from webserver.util.passwords import hash_password
    c = world["client"]
    ds = world["dataset"]["id"]
    UserModel.objects(username__iexact="b55667788").delete()
    UserModel(username="b55667788", password=hash_password("pw"), name="lower").save()
    UserModel.objects(username="smoke").update(set__is_admin=True)
    try:
        r = c.post("/api/admin/users/bulk", json={"datasetId": ds, "users": [{"username": "B55667788"}]})
        assert r.get_json()["existing"] == ["b55667788"]
        assert "b55667788" in DatasetModel.objects(id=ds).first().users
    finally:
        UserModel.objects(username="smoke").update(set__is_admin=False)
        DatasetModel.objects(id=ds).update(pull__users="b55667788")


def test_copy_undo_only_removes_copies(world):
    from database import AnnotationModel, ImageModel
    c = world["client"]
    image = ImageModel.objects(dataset_id=world["dataset"]["id"], deleted=False).order_by("id").first()
    cat = world["dataset"]["categories"][0]
    drawn = c.post("/api/annotation/", json={"image_id": image.id, "category_id": cat,
                                            "segmentation": [[1, 1, 9, 1, 9, 9, 1, 9]]}).get_json()["id"]
    r = c.post(f"/api/image/copy/{image.id}/annotations/undo", json={"ids": [drawn]})
    assert r.get_json()["removed"] == 0
    assert AnnotationModel.objects(id=drawn).first() is not None
    assert c.post(f"/api/image/copy/{image.id}/annotations/undo", json={"ids": ["x"]}).status_code == 400


def test_category_metadata_is_saved(world):
    from database import CategoryModel
    c = world["client"]
    r = c.post("/api/category/", json={"name": "review-fix-meta", "color": "#123456"})
    assert r.status_code == 200, r.data
    cat_id = r.get_json()["id"]
    # only the metadata changes: it used to answer "Nothing to update"
    r = c.put(f"/api/category/{cat_id}", json={"name": "review-fix-meta", "color": "#123456",
                                               "metadata": {"k": "v"}})
    assert r.status_code == 200 and r.get_json().get("success"), r.data
    assert CategoryModel.objects(id=cat_id).first().metadata == {"k": "v"}


def test_trashed_datasets_listed_for_their_owner_only(world):
    from database import DatasetModel, ImageModel
    c = world["client"]
    mine = DatasetModel(name="review-fix-trash-mine", deleted=True)
    mine.save()
    other = DatasetModel(name="review-fix-trash-other", deleted=True)
    other.save()
    # save() sets the owner to the logged-in user (none here)
    mine.update(set__owner="Smoke")  # matched without case, as is_owner does
    other.update(set__owner="someone-else")
    ImageModel(path="/nonexistent/a.jpg", file_name="a.jpg", dataset_id=mine.id, width=1, height=1).save()
    try:
        trashed = {d["name"]: d for d in c.get("/api/dataset/data").get_json()["trashed"]}
        assert trashed["review-fix-trash-mine"]["images"] == 1
        assert "review-fix-trash-other" not in trashed
    finally:
        ImageModel.objects(dataset_id=mine.id).delete()
        mine.delete()
        other.delete()
