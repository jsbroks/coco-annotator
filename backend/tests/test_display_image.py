"""The annotator gets the original file when a browser can show it as is."""
import io
import os


def test_annotator_image_is_the_file(world, dataset_directory):
    from PIL import Image
    from database import ImageModel
    c = world["client"]
    ds = c.post("/api/dataset/", json={"name": "display"}).get_json()["id"]
    folder = os.path.join(dataset_directory, "display")
    os.makedirs(folder, exist_ok=True)
    Image.new("RGB", (64, 48), (200, 10, 10)).save(os.path.join(folder, "plain.jpg"))
    rotated = Image.new("RGB", (64, 48), (10, 200, 10))
    exif = rotated.getexif()
    exif[0x0112] = 6  # "rotate 90": browsers would turn it, annotations would not
    rotated.save(os.path.join(folder, "rotated.jpg"), exif=exif)
    Image.new("I;16", (64, 48)).save(os.path.join(folder, "deep.png"))
    c.get(f"/api/dataset/{ds}/scan")
    images = {i.file_name: i for i in ImageModel.objects(dataset_id=ds)}

    plain = images["plain.jpg"]
    r = c.get(f"/api/image/{plain.id}")
    assert r.status_code == 200 and r.data == open(plain.path, "rb").read()
    etag = r.headers["ETag"]
    assert c.get(f"/api/image/{plain.id}", headers={"If-None-Match": etag}).status_code == 304

    for name in ("rotated.jpg", "deep.png"):
        r = c.get(f"/api/image/{images[name].id}")
        assert r.status_code == 200 and r.data != open(images[name].path, "rb").read()
        shown = Image.open(io.BytesIO(r.data))
        assert shown.format == "JPEG" and shown.size == (64, 48)
        assert shown.getexif().get(0x0112) in (None, 1)

    # thumbnails are unchanged
    r = c.get(f"/api/image/{plain.id}", query_string={"thumbnail": "true", "width": 32})
    assert r.status_code == 200 and Image.open(io.BytesIO(r.data)).size[0] <= 32
