"""SAM service: checkpoint choice, and SAM 2.1 predictions when weights are given
(SAM2_TEST_WEIGHTS=/path/to/sam2.1_t.pt, needs torch + ultralytics)."""
import os

import numpy as np
import pytest


def test_checkpoint_fallback(tmp_path):
    from webserver.util.sam import SamService, is_sam2
    service = SamService(str(tmp_path / "sam2.1_b.pt"), "vit_b", "cpu", models_dir=str(tmp_path))
    assert service.checkpoint == str(tmp_path / "sam2.1_b.pt")   # nothing there yet
    assert service.available is False

    (tmp_path / "sam_vit_b_01ec64.pth").write_bytes(b"x")
    assert os.path.basename(service.checkpoint) == "sam_vit_b_01ec64.pth"   # older install keeps working
    assert service.model_name == "SAM vit_b"

    (tmp_path / "sam2.1_t.pt").write_bytes(b"x")
    assert os.path.basename(service.checkpoint) == "sam2.1_t.pt"            # SAM 2.1 preferred
    assert service.model_name == "SAM 2.1 t" and is_sam2(service.checkpoint)

    (tmp_path / "sam2.1_b.pt").write_bytes(b"x")
    assert os.path.basename(service.checkpoint) == "sam2.1_b.pt"            # the configured one wins


def test_yolo_list_skips_sam2(tmp_path):
    from webserver.util.yolo import YoloService
    (tmp_path / "sam2.1_b.pt").write_bytes(b"x")
    (tmp_path / "boats.pt").write_bytes(b"x")
    service = YoloService.__new__(YoloService)
    service.directory = str(tmp_path)
    assert service.model_names() == ["boats.pt"]


@pytest.mark.skipif(not os.environ.get("SAM2_TEST_WEIGHTS"), reason="set SAM2_TEST_WEIGHTS to run")
def test_sam2_predict(tmp_path):
    import cv2
    from webserver.util.sam import SamService
    weights = os.environ["SAM2_TEST_WEIGHTS"]
    img = np.full((240, 320, 3), 30, np.uint8)
    cv2.rectangle(img, (60, 50), (160, 150), (60, 60, 220), -1)
    cv2.circle(img, (240, 170), 40, (60, 200, 60), -1)
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    cv2.imwrite(a, img)
    cv2.imwrite(b, np.zeros_like(img))

    service = SamService(weights, "vit_b", "cpu", cache_size=4, models_dir=os.path.dirname(weights))
    assert service.available and service.status()["model_type"].startswith("SAM 2")

    def bbox(polygons):
        pts = np.concatenate([np.array(p).reshape(-1, 2) for p in polygons])
        return pts.min(0).tolist() + pts.max(0).tolist()

    polygons, score, area = service.predict(1, a, points=[[110, 100]], labels=[1])
    assert score > 0.8 and abs(area - 101 * 101) < 400
    assert bbox(polygons) == pytest.approx([60, 50, 160, 150], abs=3)

    service.predict(2, b, points=[[10, 10]], labels=[1])           # another image in between
    polygons, _, _ = service.predict(1, a, box=[195, 125, 285, 215])  # back to image 1 from the cache
    assert bbox(polygons) == pytest.approx([200, 130, 280, 210], abs=4)

    # a background point next to the square keeps the result the square
    polygons, _, _ = service.predict(1, a, points=[[110, 100], [240, 170]], labels=[1, 0])
    assert bbox(polygons) == pytest.approx([60, 50, 160, 150], abs=3)
