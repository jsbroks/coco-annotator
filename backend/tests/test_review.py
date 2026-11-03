"""Review workflow: submit / approve / reject, reviewers, assignment, progress."""
import os

import pytest


@pytest.fixture(scope="module")
def review_world(world, dataset_directory):
    from PIL import Image
    from webserver import app
    from webserver.util.passwords import hash_password
    from database import UserModel

    owner = world["client"]
    UserModel.objects(username="smoke").update(set__is_admin=False)
    r = owner.post("/api/dataset/", json={"name": "review_ds", "categories": ["ship"]})
    assert r.status_code == 200, r.data
    ds = r.get_json()["id"]
    folder = os.path.join(dataset_directory, "review_ds")
    os.makedirs(folder, exist_ok=True)
    for i in range(4):
        Image.new("RGB", (64, 48), (10 * i, 80, 120)).save(os.path.join(folder, f"r{i}.jpg"))
    assert owner.get(f"/api/dataset/{ds}/scan").status_code == 200

    clients = {}
    for name in ("labeler1", "labeler2"):
        if UserModel.objects(username=name).first() is None:
            UserModel(username=name, password=hash_password("pw"), name=name, is_admin=False).save()
        c = app.test_client()
        assert c.post("/api/user/login", json={"username": name, "password": "pw"}).status_code == 200
        clients[name] = c
    assert owner.post(f"/api/dataset/{ds}/share", json={"users": ["labeler1", "labeler2"]}).status_code == 200
    images = sorted(owner.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])
    return {"owner": owner, "ds": ds, "images": images, **clients}


def test_submit_approve_reject(review_world):
    w = review_world
    img = w["images"][0]["id"]
    l1, owner = w["labeler1"], w["owner"]

    assert owner.get(f"/api/review/image/{img}").get_json()["status"] == "unlabeled"
    r = l1.post(f"/api/review/image/{img}", json={"action": "submit"})
    assert r.status_code == 200 and r.get_json()["status"] == "labeled"
    assert r.get_json()["labeled_by"] == "labeler1"

    # a labeler cannot approve
    assert l1.post(f"/api/review/image/{img}", json={"action": "approve"}).status_code == 403

    r = owner.post(f"/api/review/image/{img}", json={"action": "reject", "note": "missed a boat"})
    assert r.get_json()["status"] == "rejected" and r.get_json()["review_note"] == "missed a boat"
    data = l1.get(f"/api/annotator/data/{img}").get_json()
    assert data["review"]["status"] == "rejected" and data["review"]["review_note"] == "missed a boat"
    assert data["permissions"]["dataset"]["review"] is False

    l1.post(f"/api/review/image/{img}", json={"action": "submit"})
    r = owner.post(f"/api/review/image/{img}", json={"action": "approve"})
    assert r.get_json()["status"] == "approved" and r.get_json()["review_note"] == ""
    # an approved image can only be reopened by a reviewer
    l1.post(f"/api/review/image/{img}", json={"action": "reopen"})
    assert owner.get(f"/api/review/image/{img}").get_json()["status"] == "approved"

    # labeler2 becomes a reviewer
    r = owner.post(f"/api/review/dataset/{w['ds']}/reviewers", json={"reviewers": ["labeler2", "nobody"]})
    assert r.get_json()["reviewers"] == ["labeler2"]
    img2 = w["images"][1]["id"]
    l1.post(f"/api/review/image/{img2}", json={"action": "submit"})
    assert w["labeler2"].post(f"/api/review/image/{img2}", json={"action": "approve"}).status_code == 200
    assert l1.post(f"/api/review/dataset/{w['ds']}/reviewers", json={"reviewers": []}).status_code == 403


def test_assign_filters_progress_and_export(review_world):
    from database import ExportModel
    w = review_world
    owner, l1 = w["owner"], w["labeler1"]
    ds = w["ds"]

    assert l1.post(f"/api/review/dataset/{ds}/assign", json={"usernames": ["labeler1"]}).status_code == 403
    assert owner.post(f"/api/review/dataset/{ds}/assign",
                      json={"usernames": ["stranger_x"]}).status_code == 400
    r = owner.post(f"/api/review/dataset/{ds}/assign", json={"usernames": ["labeler1", "labeler2"], "scope": "all"})
    assert r.get_json()["assigned"] == {"labeler1": 2, "labeler2": 2}

    mine = l1.get(f"/api/dataset/{ds}/data?assignee=me").get_json()["images"]
    assert [i["file_name"] for i in mine] == ["r0.jpg", "r1.jpg"]   # a contiguous block
    assert all(i["assignee"] == "labeler1" for i in mine)
    approved = owner.get(f"/api/dataset/{ds}/data?status=approved").get_json()["images"]
    assert {i["file_name"] for i in approved} == {"r0.jpg", "r1.jpg"}
    assert len(owner.get(f"/api/dataset/{ds}/data?status=unlabeled").get_json()["images"]) == 2

    # unassign one image, then "unassigned" scope only touches that one
    owner.post(f"/api/review/dataset/{ds}/assign", json={"usernames": [], "image_ids": [w["images"][3]["id"]]})
    assert len(owner.get(f"/api/dataset/{ds}/data?assignee=none").get_json()["images"]) == 1
    r = owner.post(f"/api/review/dataset/{ds}/assign", json={"usernames": ["labeler1"]})
    assert r.get_json()["assigned"] == {"labeler1": 1}

    p = owner.get(f"/api/review/dataset/{ds}/progress").get_json()
    assert p["images"] == 4 and p["total"]["approved"] == 2 and p["total"]["unlabeled"] == 2
    people = {x["username"]: x for x in p["people"]}
    assert people["labeler1"]["approved"] == 2 and people["labeler1"]["unlabeled"] == 1
    assert p["reviewers"] == ["labeler2"] and p["can_review"]

    # next image to work on / review
    nxt = l1.get(f"/api/review/dataset/{ds}/next?mode=work").get_json()["id"]
    assert nxt == w["images"][3]["id"]
    l1.post(f"/api/review/image/{nxt}", json={"action": "submit"})
    assert owner.get(f"/api/review/dataset/{ds}/next?mode=review").get_json()["id"] == nxt

    # export only approved images
    r = owner.get(f"/api/dataset/{ds}/export?only_approved=true&with_empty_images=true")
    assert r.status_code == 200, r.data
    export = ExportModel.objects(dataset_id=ds).order_by("-id").first()
    import json
    with open(export.path) as f:
        coco = json.load(f)
    assert sorted(i["file_name"] for i in coco["images"]) == ["r0.jpg", "r1.jpg"]
    row = owner.get(f"/api/dataset/{ds}/exports").get_json()[0]
    assert row["only_approved"] is True


def test_submit_skip_empty(world):
    from database import ImageModel
    c = world["client"]
    image = ImageModel.objects(dataset_id=world["dataset"]["id"], deleted=False).first()
    ImageModel.objects(id=image.id).update(set__num_annotations=0, unset__image_class=True, set__status="unlabeled")
    r = c.post(f"/api/review/image/{image.id}", json={"action": "submit", "skip_empty": True})
    assert r.status_code == 200 and r.get_json()["skipped"] is True
    assert ImageModel.objects(id=image.id).first().status == "unlabeled"
    ImageModel.objects(id=image.id).update(set__num_annotations=2)
    r = c.post(f"/api/review/image/{image.id}", json={"action": "submit", "skip_empty": True})
    assert r.status_code == 200 and not r.get_json().get("skipped")
    # the owner reviews: their own submit is an approval
    assert ImageModel.objects(id=image.id).first().status == "approved"
    ImageModel.objects(id=image.id).update(set__status="unlabeled")



def test_reviewer_submit_is_approved(review_world):
    w = review_world
    img = w["images"][3]["id"]
    owner, l1, l2 = w["owner"], w["labeler1"], w["labeler2"]
    r = owner.post(f"/api/review/image/{img}", json={"action": "submit"}).get_json()
    assert r["status"] == "approved" and r["labeled_by"] == "smoke" and r["reviewed_by"] == "smoke"
    owner.post(f"/api/review/image/{img}", json={"action": "reopen"})
    # a member who is a reviewer: the same; a plain member: waits for review
    owner.post(f"/api/review/dataset/{w['ds']}/reviewers", json={"reviewers": ["labeler2"]})
    assert l2.post(f"/api/review/image/{img}", json={"action": "submit"}).get_json()["status"] == "approved"
    owner.post(f"/api/review/image/{img}", json={"action": "reopen"})
    assert l1.post(f"/api/review/image/{img}", json={"action": "submit"}).get_json()["status"] == "labeled"
    owner.post(f"/api/review/dataset/{w['ds']}/reviewers", json={"reviewers": []})
    owner.post(f"/api/review/image/{img}", json={"action": "reopen"})


def test_admin_is_not_a_reviewer(review_world):
    from webserver import app
    from webserver.util.passwords import hash_password
    from database import UserModel
    w = review_world
    img = w["images"][2]["id"]
    if UserModel.objects(username="boss").first() is None:
        UserModel(username="boss", password=hash_password("pw"), name="Boss", is_admin=True).save()
    admin = app.test_client()
    assert admin.post("/api/user/login", json={"username": "boss", "password": "pw"}).status_code == 200

    w["labeler1"].post(f"/api/review/image/{img}", json={"action": "submit"})
    assert admin.post(f"/api/review/image/{img}", json={"action": "approve"}).status_code == 403
    assert admin.post(f"/api/review/dataset/{w['ds']}/reviewers", json={"reviewers": ["boss"]}).status_code == 403
    progress = admin.get(f"/api/review/dataset/{w['ds']}/progress").get_json()
    assert progress["can_review"] is False and progress["is_creator"] is False and progress["can_assign"] is True
    # the creator can let someone review
    w["owner"].post(f"/api/review/image/{img}", json={"action": "approve"})
    assert w["owner"].get(f"/api/review/image/{img}").get_json()["status"] == "approved"
    w["owner"].post(f"/api/review/image/{img}", json={"action": "reopen"})


def test_quick_review_queue(world, dataset_directory):
    import os
    from PIL import Image
    from database import CategoryModel, ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "quickrev", "categories": ["qr_cat"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "quickrev")
    os.makedirs(folder, exist_ok=True)
    for i in range(5):
        Image.new("RGB", (40, 30)).save(os.path.join(folder, f"q{i}.jpg"))
    c.get(f"/api/dataset/{ds}/scan")
    images = sorted(ImageModel.objects(dataset_id=ds), key=lambda i: i.file_name)
    cat = CategoryModel.objects(name="qr_cat").first().id
    c.post("/api/annotation/", json={"image_id": images[0].id, "category_id": cat,
                                     "segmentation": [[1, 1, 20, 1, 20, 20, 1, 20]]})
    ImageModel.objects(id__in=[i.id for i in images[:4]]).update(set__status="labeled", set__labeled_by="smoke")

    q = c.get(f"/api/review/dataset/{ds}/queue", query_string={"per_page": 3}).get_json()
    assert q["total"] == 4 and q["pages"] == 2 and len(q["images"]) == 3
    first = next(i for i in q["images"] if i["id"] == images[0].id)
    assert first["annotations"][0]["category_id"] == cat and first["width"] == 40
    assert q["labelers"] == ["smoke"] and q["categories"][0]["name"] == "qr_cat"
    # approve a whole page at once
    ids = [i["id"] for i in q["images"]]
    r = c.post(f"/api/review/image/{ids[0]}", json={"action": "approve", "image_ids": ids})
    assert r.status_code in (200, 403)


def test_reject_with_regions(review_world):
    w = review_world
    img = w["images"][1]["id"]
    l1, owner = w["labeler1"], w["owner"]
    l1.post(f"/api/review/image/{img}", json={"action": "submit"})
    r = owner.post(f"/api/review/image/{img}", json={
        "action": "reject", "note": "this box",
        "regions": [[10, 20, 30, 40], [-5, -5, 20, 20], ["bad"], [0, 0, 0, 5]]})
    assert r.status_code == 200
    # clipped to the image, broken or empty boxes dropped
    assert r.get_json()["review_regions"] == [[10, 20, 30, 28], [0, 0, 15, 15]]
    data = l1.get(f"/api/annotator/data/{img}").get_json()
    assert data["review"]["review_regions"] == [[10, 20, 30, 28], [0, 0, 15, 15]]
    # approving clears them
    l1.post(f"/api/review/image/{img}", json={"action": "submit"})
    r = owner.post(f"/api/review/image/{img}", json={"action": "approve"})
    assert r.get_json()["review_regions"] == []


def test_reject_reasons(review_world):
    c = review_world["labeler2"]
    assert c.get("/api/user/reject-reasons").get_json()["reasons"] is None
    r = c.put("/api/user/reject-reasons", json={"reasons": [" 類別錯 ", "", "類別錯", "x" * 300] + [str(i) for i in range(20)]})
    reasons = r.get_json()["reasons"]
    assert reasons[0] == "類別錯" and len(reasons[1]) == 200 and len(reasons) == 9
    assert c.get("/api/user/reject-reasons").get_json()["reasons"] == reasons
    assert c.put("/api/user/reject-reasons", json={"reasons": []}).get_json()["reasons"] == []


def test_dataset_list_has_status_counts(review_world):
    w = review_world
    owner, ds = w["owner"], w["ds"]
    listed = [d for d in owner.get("/api/dataset/data?limit=100").get_json()["datasets"] if d["id"] == ds][0]
    progress = owner.get(f"/api/review/dataset/{ds}/progress").get_json()
    # the cards show the same numbers as the dataset's progress
    assert listed["statusCounts"] == progress["total"]
    assert sum(listed["statusCounts"].values()) == listed["numberImages"]


def _n(row):
    return sum(v for k, v in row.items() if k != "username")


def test_clear_one_persons_assignment(review_world, dataset_directory):
    from PIL import Image
    w = review_world
    owner, l1 = w["owner"], w["labeler1"]
    ds = owner.post("/api/dataset/", json={"name": "clear_ds"}).get_json()["id"]
    folder = os.path.join(dataset_directory, "clear_ds")
    os.makedirs(folder, exist_ok=True)
    for i in range(6):
        Image.new("RGB", (16, 16)).save(os.path.join(folder, f"c{i}.jpg"))
    owner.get(f"/api/dataset/{ds}/scan")
    owner.post(f"/api/dataset/{ds}/share", json={"users": ["labeler1", "labeler2"]})
    owner.post(f"/api/review/dataset/{ds}/assign", json={"usernames": ["labeler1", "labeler2"], "scope": "all"})
    images = sorted(owner.get(f"/api/dataset/{ds}/data").get_json()["images"], key=lambda i: i["file_name"])
    # labeler1 (c0-c2) finished one image
    l1.post(f"/api/review/image/{images[0]['id']}", json={"action": "submit"})

    # what labeler1 still has to do goes back; the finished one stays theirs
    r = owner.post(f"/api/review/dataset/{ds}/assign",
                   json={"usernames": [], "from_user": "labeler1", "scope": "unlabeled"})
    assert r.get_json()["unassigned"] == 2
    people = {p["username"]: p for p in owner.get(f"/api/review/dataset/{ds}/progress").get_json()["people"]}
    assert _n(people["labeler1"]) == 1 and _n(people["labeler2"]) == 3

    # everything of labeler2; labeler1 untouched
    r = owner.post(f"/api/review/dataset/{ds}/assign",
                   json={"usernames": [], "from_user": "labeler2", "scope": "all"})
    assert r.get_json()["unassigned"] == 3
    people = {p["username"]: p for p in owner.get(f"/api/review/dataset/{ds}/progress").get_json()["people"]}
    assert "labeler2" not in people and _n(people["labeler1"]) == 1
    # only assigners may do it
    assert l1.post(f"/api/review/dataset/{ds}/assign",
                   json={"usernames": [], "from_user": "labeler1", "scope": "all"}).status_code == 403
