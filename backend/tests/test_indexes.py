from database import ImageModel, AnnotationModel, ensure_indexes


def _indexed_fields(model):
    info = model._get_collection().index_information()
    return {tuple(k for k, _ in spec["key"]) for spec in info.values()}


def test_indexes_for_hot_queries():
    ensure_indexes()
    images = _indexed_fields(ImageModel)
    annotations = _indexed_fields(AnnotationModel)
    assert ("path",) in images
    assert ("dataset_id", "deleted", "file_name") in images
    assert ("image_id", "deleted") in annotations
    assert ("dataset_id", "deleted") in annotations
