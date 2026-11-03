import os
import tempfile

import pytest

# Tests run fully in-process: in-memory MongoDB (mongomock), Celery tasks
# executed eagerly and an in-memory message queue. Environment variables
# that are already set (e.g. in CI) take precedence.
_DATASETS = tempfile.mkdtemp(prefix="coco-annotator-tests-")
os.environ.setdefault("MONGODB_HOST", "mongomock://localhost/flask")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("DATASET_DIRECTORY", _DATASETS + "/")
os.environ.setdefault("LOGIN_DISABLED", "true")
os.environ.setdefault("SAM_CHECKPOINT", "/nonexistent/sam.pth")
os.environ.setdefault("MODELS_DIRECTORY", tempfile.mkdtemp(prefix="coco-annotator-models-"))

from webserver import app  # noqa: E402


@pytest.fixture
def client():
    test_client = app.test_client()
    return test_client


@pytest.fixture(scope="session")
def dataset_directory():
    return os.environ["DATASET_DIRECTORY"]


@pytest.fixture(scope="session")
def world(dataset_directory):
    """A logged-in client with a dataset of two scanned 320x200 images."""
    from PIL import Image
    WIDTH, HEIGHT = 320, 200
    from webserver import app
    client = app.test_client()

    client.post("/api/user/register", json={"username": "smoke", "password": "pw", "name": "Smoke"})

    r = client.post("/api/dataset/", json={"name": "smoke", "categories": ["ship", "boat"]})
    assert r.status_code == 200, r.data
    dataset = r.get_json()

    folder = os.path.join(dataset_directory, "smoke")
    os.makedirs(folder, exist_ok=True)
    for i in range(2):
        Image.new("RGB", (WIDTH, HEIGHT), (20 * i, 80, 120)).save(os.path.join(folder, f"img_{i}.jpg"))

    r = client.get(f"/api/dataset/{dataset['id']}/scan")
    assert r.status_code == 200, r.data

    r = client.get(f"/api/dataset/{dataset['id']}/data")
    assert r.status_code == 200, r.data
    images = r.get_json()["images"]
    assert len(images) == 2

    categories = {c["name"]: c["id"] for c in client.get("/api/category/").get_json()}
    return {"client": client, "dataset": dataset, "images": images, "categories": categories}
