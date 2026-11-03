"""Dataset health: distributions and likely labelling problems in one pass."""
from collections import Counter

import numpy as np

from database import AnnotationModel, CategoryModel, ImageModel

OBJECT_BUCKETS = [(0, 0, "0"), (1, 1, "1"), (2, 2, "2"), (3, 3, "3"), (4, 5, "4-5"),
                  (6, 10, "6-10"), (11, 20, "11-20"), (21, 50, "21-50"), (51, None, "51+")]
# share of the image area covered by a box
RELATIVE_BUCKETS = [(0, 0.001, "<0.1%"), (0.001, 0.01, "0.1-1%"), (0.01, 0.05, "1-5%"),
                    (0.05, 0.2, "5-20%"), (0.2, 0.5, "20-50%"), (0.5, None, ">50%")]
# box width / height
ASPECT_BUCKETS = [(0, 0.25, "<1:4"), (0.25, 0.5, "1:4-1:2"), (0.5, 1, "1:2-1:1"),
                  (1, 2, "1:1-2:1"), (2, 4, "2:1-4:1"), (4, None, ">4:1")]
HEATMAP_SIZE = 20
FEW_ANNOTATIONS = 10
IMBALANCE_RATIO = 10


def _bucket(value, buckets):
    """Half-open float buckets: low <= value < high (high None = no limit)."""
    for low, high, label in buckets:
        if value >= low and (high is None or value < high):
            return label
    return buckets[-1][2]


def _count_bucket(n):
    """Inclusive integer buckets for object counts."""
    for low, high, label in OBJECT_BUCKETS:
        if n >= low and (high is None or n <= high):
            return label
    return OBJECT_BUCKETS[-1][2]


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def dataset_health(dataset):
    images = {row['_id']: row for row in ImageModel.objects(dataset_id=dataset.id, deleted=False)
              .only('id', 'file_name', 'width', 'height', 'status', 'image_class', 'confirmed_empty').as_pymongo()}
    categories = {c.id: c for c in CategoryModel.objects(id__in=dataset.categories or [], deleted=False)}

    per_category = {cid: {'annotations': 0, 'images': set(), 'classified': 0} for cid in categories}
    per_image = Counter()
    sizes = Counter({'small': 0, 'medium': 0, 'large': 0})
    relative = Counter()
    aspect = Counter()
    heat = np.zeros((HEATMAP_SIZE, HEATMAP_SIZE), dtype=np.int64)
    issues_tiny, issues_outside, issues_degenerate = [], [], []
    # annotations that do not fit the dataset's planned task
    not_rotated, no_keypoints, box_only = [], [], []
    boxes_by_image = {}
    total = 0

    rows = AnnotationModel.objects(image_id__in=list(images), deleted=False) \
        .only('id', 'image_id', 'category_id', 'bbox', 'area', 'segmentation', 'keypoints',
              'isbbox', 'isrbbox').as_pymongo()
    for a in rows:
        has_shape = bool(a.get('segmentation'))
        has_keypoints = any(v > 0 for v in (a.get('keypoints') or [])[2::3])
        if not has_shape and not has_keypoints:
            continue
        image = images.get(a['image_id'])
        if image is None:
            continue
        total += 1
        per_image[a['image_id']] += 1
        if not a.get('isrbbox'):
            not_rotated.append(a)
        if not has_keypoints:
            no_keypoints.append(a)
        if a.get('isbbox') and not a.get('isrbbox'):
            box_only.append(a)
        cid = a.get('category_id')
        if cid in per_category:
            per_category[cid]['annotations'] += 1
            per_category[cid]['images'].add(a['image_id'])

        bbox = list(a.get('bbox') or [])
        if (len(bbox) != 4 or bbox[2] < 2 or bbox[3] < 2) and has_shape:
            # some annotations have no stored bbox: use the polygon's extent
            pts = [float(v) for poly in a['segmentation'] if isinstance(poly, list) for v in poly]
            if len(pts) >= 4:
                xs, ys = pts[0::2], pts[1::2]
                bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
        if len(bbox) != 4:
            continue
        x, y, w, h = (float(v) for v in bbox)
        W, H = float(image.get('width') or 0), float(image.get('height') or 0)
        if w < 2 or h < 2:
            issues_degenerate.append(a)
            continue
        area = w * h
        sizes['small' if area < 32 ** 2 else 'medium' if area < 96 ** 2 else 'large'] += 1
        if W and H:
            share = area / (W * H)
            relative[_bucket(share, RELATIVE_BUCKETS)] += 1
            if share < 0.0001:
                issues_tiny.append(a)
            if x < -1 or y < -1 or x + w > W + 1 or y + h > H + 1:
                issues_outside.append(a)
            cx = min(max((x + w / 2) / W, 0), 0.999999)
            cy = min(max((y + h / 2) / H, 0), 0.999999)
            heat[int(cy * HEATMAP_SIZE), int(cx * HEATMAP_SIZE)] += 1
        aspect[_bucket(w / h, ASPECT_BUCKETS)] += 1
        boxes_by_image.setdefault(a['image_id'], []).append((cid, (x, y, w, h), a['_id']))

    for row in images.values():
        if row.get('image_class') in per_category:
            per_category[row['image_class']]['classified'] += 1

    # likely duplicates: same category, almost the same box, same image
    duplicates = []
    for image_id, boxes in boxes_by_image.items():
        if len(boxes) > 200:
            continue  # crowded images: skip the O(n^2) check
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if boxes[i][0] == boxes[j][0] and _iou(boxes[i][1], boxes[j][1]) > 0.95:
                    duplicates.append({'image_id': image_id, 'annotation_ids': [boxes[i][2], boxes[j][2]]})

    objects = Counter(_count_bucket(per_image.get(i, 0)) for i in images)
    no_annotations = [i for i in images if per_image.get(i, 0) == 0 and images[i].get('image_class') is None]
    # background images the annotator confirmed have nothing to annotate
    confirmed_empty = [i for i in no_annotations if images[i].get('confirmed_empty')]
    unannotated = [i for i in no_annotations if not images[i].get('confirmed_empty')]

    class_rows = []
    for cid, c in categories.items():
        stats = per_category[cid]
        class_rows.append({'id': cid, 'name': c.name, 'color': c.color, 'annotations': stats['annotations'],
                           'images': len(stats['images']), 'classified': stats['classified']})
    class_rows.sort(key=lambda r: -r['annotations'])

    resolutions = Counter((r.get('width'), r.get('height')) for r in images.values())
    widths = [r.get('width') or 0 for r in images.values()]
    heights = [r.get('height') or 0 for r in images.values()]
    statuses = Counter(r.get('status') or 'unlabeled' for r in images.values())

    def example(rows, key='image_id'):
        ids = []
        for r in rows:
            image_id = r[key] if isinstance(r, dict) else r
            if image_id not in ids:
                ids.append(image_id)
            if len(ids) == 5:
                break
        return [{'image_id': i, 'file_name': images[i].get('file_name')} for i in ids]

    issues = []
    if unannotated:
        issues.append({'level': 'warning', 'code': 'unannotated', 'n': len(unannotated),
                       'examples': example(unannotated, None)})
    if confirmed_empty:
        issues.append({'level': 'info', 'code': 'confirmedEmpty', 'n': len(confirmed_empty),
                       'examples': example(confirmed_empty, None)})
    empty = [r['name'] for r in class_rows if r['annotations'] == 0 and r['classified'] == 0]
    if empty:
        issues.append({'level': 'warning', 'code': 'emptyClasses', 'n': len(empty), 'names': empty[:10]})
    few = [f"{r['name']} ({r['annotations']})" for r in class_rows if 0 < r['annotations'] < FEW_ANNOTATIONS]
    if few:
        issues.append({'level': 'warning', 'code': 'fewAnnotations', 'n': len(few), 'names': few[:10],
                       'min': FEW_ANNOTATIONS})
    used = [r for r in class_rows if r['annotations'] > 0]
    if len(used) > 1 and used[0]['annotations'] >= IMBALANCE_RATIO * used[-1]['annotations']:
        issues.append({'level': 'warning', 'code': 'imbalance',
                       'ratio': round(used[0]['annotations'] / used[-1]['annotations'], 1),
                       'most': used[0]['name'], 'least': used[-1]['name']})
    if duplicates:
        issues.append({'level': 'warning', 'code': 'duplicates', 'n': len(duplicates),
                       'examples': example(duplicates)})
    if issues_outside:
        issues.append({'level': 'warning', 'code': 'outside', 'n': len(issues_outside),
                       'examples': example(issues_outside)})
    if issues_degenerate:
        issues.append({'level': 'warning', 'code': 'degenerate', 'n': len(issues_degenerate),
                       'examples': example(issues_degenerate)})
    if issues_tiny:
        issues.append({'level': 'info', 'code': 'tiny', 'n': len(issues_tiny),
                       'examples': example(issues_tiny)})
    task = getattr(dataset, 'task', '') or ''
    if task == 'obb' and not_rotated:
        issues.append({'level': 'info', 'code': 'taskNotRotated', 'n': len(not_rotated),
                       'examples': example(not_rotated)})
    if task == 'pose' and no_keypoints:
        issues.append({'level': 'warning', 'code': 'taskNoKeypoints', 'n': len(no_keypoints),
                       'examples': example(no_keypoints)})
    if task in ('segment', 'semantic') and box_only:
        issues.append({'level': 'info', 'code': 'taskBoxOnly', 'n': len(box_only),
                       'examples': example(box_only)})
    if task == 'classify':
        unclassified = [i for i, row in images.items() if row.get('image_class') is None]
        if unclassified:
            issues.append({'level': 'warning', 'code': 'taskNoImageClass', 'n': len(unclassified),
                           'examples': example(unclassified, None)})
    if statuses.get('rejected'):
        issues.append({'level': 'info', 'code': 'rejected', 'n': statuses['rejected']})
    if statuses.get('labeled'):
        issues.append({'level': 'info', 'code': 'toReview', 'n': statuses['labeled']})

    return {
        'task': task,
        'totals': {
            'images': len(images),
            'annotated_images': len(images) - len(no_annotations),
            'annotations': total,
            'categories': len(categories),
            'per_image_avg': round(total / len(images), 2) if images else 0,
        },
        'issues': issues,
        'classes': class_rows,
        'objects_per_image': [{'label': b[2], 'n': objects.get(b[2], 0)} for b in OBJECT_BUCKETS],
        'box_sizes': dict(sizes),
        'relative_sizes': [{'label': b[2], 'n': relative.get(b[2], 0)} for b in RELATIVE_BUCKETS],
        'aspect_ratios': [{'label': b[2], 'n': aspect.get(b[2], 0)} for b in ASPECT_BUCKETS],
        'heatmap': heat.tolist(),
        'resolutions': [{'width': w, 'height': h, 'n': n} for (w, h), n in resolutions.most_common(8)],
        'image_size': {
            'min': [min(widths, default=0), min(heights, default=0)],
            'median': [int(np.median(widths)) if widths else 0, int(np.median(heights)) if heights else 0],
            'max': [max(widths, default=0), max(heights, default=0)],
        },
        'statuses': dict(statuses),
    }
