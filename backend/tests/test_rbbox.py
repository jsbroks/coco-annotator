import pytest

from geometry import rbbox_to_polygon, polygon_to_rbbox


@pytest.mark.parametrize("rbbox", [
    [100, 50, 40, 20, 0],
    [100, 50, 40, 20, 30],
    [10.5, 20.25, 7, 3, -45],
    [300, 200, 80, 10, 179],
    [300, 200, 80, 10, -170],
])
def test_roundtrip(rbbox):
    poly = rbbox_to_polygon(rbbox)
    assert len(poly) == 8
    back = polygon_to_rbbox(poly)
    for a, b in zip(rbbox, back):
        assert a == pytest.approx(b, abs=0.02)


def test_axis_aligned_corners():
    poly = rbbox_to_polygon([100, 50, 40, 20, 0])
    assert poly == [80, 40, 120, 40, 120, 60, 80, 60]


def test_clockwise_angle_in_image_coordinates():
    # first edge pointing straight down (+y) is +90 degrees
    rb = polygon_to_rbbox([0, 0, 0, 10, -5, 10, -5, 0])
    assert rb[4] == pytest.approx(90)
    assert rb[2] == pytest.approx(10)
    assert rb[3] == pytest.approx(5)


def test_fallback_min_area_rect():
    rb = polygon_to_rbbox([0, 0, 10, 0, 10, 5, 5, 6, 0, 5])
    assert rb[2] * rb[3] > 0
