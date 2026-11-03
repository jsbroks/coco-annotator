"""Trash: soft delete with who / when / batch, grouped listing, restore,
permanent delete, previews and automatic cleanup after ``Config.TRASH_DAYS``.

Everything deleted in one action (e.g. "clear this image's annotations")
shares a ``delete_batch`` id and is shown as one entry. Entries deleted
before batches existed are grouped by image and second.
"""
import datetime
import io
import logging
import os
import shutil
import threading
import uuid

from mongoengine import Q
from PIL import Image, ImageDraw

from config import Config
from database import AnnotationModel, CategoryModel, DatasetModel, ImageModel

logger = logging.getLogger('gunicorn.error')

TYPES = {
    "annotation": AnnotationModel,
    "image": ImageModel,
    "category": CategoryModel,
    "dataset": DatasetModel,
}
SCAN_LIMIT = 20000  # deleted items looked at per listing


def now():
    return datetime.datetime.utcnow()


# ------------------------------------------------------------- deleting

def soft_delete(target, user=None, batch=None, log=True):
    """Move a document or a queryset to the trash (and write it to the
    activity log). Returns the batch id."""
    from mongoengine.queryset import QuerySet
    batch = batch or uuid.uuid4().hex[:16]
    docs = list(target) if isinstance(target, QuerySet) else [target]
    target.update(set__deleted=True, set__deleted_date=now(),
                  set__deleted_by=getattr(user, 'username', None), set__delete_batch=batch)
    if log and docs:
        kind = next((k for k, m in TYPES.items() if isinstance(docs[0], m)), None)
        if kind:
            from . import activity
            try:
                activity.deleted(user, kind, docs, batch)
            except Exception:  # pragma: no cover - the delete itself worked
                logger.exception("Could not record a delete")
    return batch


def refresh_image(image_id):
    """Recount an image's annotations and categories after a delete / restore."""
    annotations = AnnotationModel.objects(
        Q(image_id=image_id) & Q(deleted=False) & (Q(area__gt=0) | Q(keypoints__0__exists=True))
    ).only('category_id')
    category_ids = sorted({a.category_id for a in annotations})
    count = len(annotations)
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        return
    annotated = count > 0 or getattr(image, 'image_class', None) is not None
    image.update(set__num_annotations=count, set__category_ids=category_ids, set__annotated=annotated)
    try:
        image.flag_thumbnail()
    except Exception:  # pragma: no cover - thumbnails are best effort
        pass


# ------------------------------------------------------------- visibility

def _dataset_ids(user):
    if user.is_admin:
        return None
    return [d.id for d in DatasetModel.objects(Q(owner=user.username) | Q(users__contains=user.username)).only('id')]


def _ids(item):
    """The ids of one {"type", "ids"} item; anything that is not a number is skipped."""
    if not isinstance(item, dict):
        return []
    out = []
    for i in item.get('ids') or []:
        try:
            out.append(int(i))
        except (TypeError, ValueError):
            continue
    return out


def visible(model, user, deleted=True):
    """Trashed documents of this type that the user may see, restore or purge."""
    query = model.objects(deleted=True) if deleted else model.objects
    if user.is_admin:
        return query
    if model is DatasetModel:
        return query.filter(owner=user.username)
    if model is CategoryModel:
        return query.filter(creator=user.username)
    ids = _dataset_ids(user)
    if model is ImageModel:
        return query.filter(dataset_id__in=ids)
    image_ids = [i['_id'] for i in ImageModel.objects(dataset_id__in=ids).only('id').as_pymongo()]
    return query.filter(image_id__in=image_ids)


# ------------------------------------------------------------- listing

def _iso(value):
    return value.replace(microsecond=0).isoformat() + 'Z' if value else None


def _expires(value):
    if not value or not Config.TRASH_DAYS:
        return None
    return _iso(value + datetime.timedelta(days=Config.TRASH_DAYS))


def list_groups(user, kind="all", dataset_id=None, deleted_by=None, q="", page=1, per_page=20):
    """Trash entries (one per delete action), newest first, plus counts per type."""
    kinds = list(TYPES) if kind in (None, "", "all") else [kind]
    q = (q or "").strip().lower()
    rows = []
    for name in TYPES:
        model = TYPES[name]
        query = visible(model, user)
        if deleted_by:
            query = query.filter(deleted_by=None if deleted_by == '-' else deleted_by)
        rows.append((name, list(query.order_by('-deleted_date').limit(SCAN_LIMIT).as_pymongo())))

    image_ids = {r['image_id'] for name, items in rows if name == 'annotation' for r in items}
    image_ids |= {r['_id'] for name, items in rows if name == 'image' for r in items}
    images = {i['_id']: i for i in ImageModel.objects(id__in=list(image_ids))
              .only('id', 'file_name', 'dataset_id', 'deleted', 'width', 'height').as_pymongo()}
    dataset_ids = {i.get('dataset_id') for i in images.values()} | \
        {r['_id'] for name, items in rows if name == 'dataset' for r in items}
    datasets = {d['_id']: d for d in DatasetModel.objects(id__in=[i for i in dataset_ids if i is not None])
                .only('id', 'name', 'deleted').as_pymongo()}
    category_ids = {r.get('category_id') for name, items in rows if name == 'annotation' for r in items}
    categories = {c['_id']: c for c in CategoryModel.objects(id__in=[i for i in category_ids if i is not None])
                  .only('id', 'name', 'color').as_pymongo()}

    groups = {}
    for name, items in rows:
        for r in items:
            date = r.get('deleted_date')
            if name == 'annotation':
                image = images.get(r.get('image_id'), {})
                ds = image.get('dataset_id')
                key = r.get('delete_batch') or f"legacy-{r.get('image_id')}-{date.replace(microsecond=0) if date else ''}"
                key = f"annotation:{key}"
            else:
                ds = r['_id'] if name == 'dataset' else r.get('dataset_id')
                key = f"{name}:{r['_id']}"
            group = groups.get(key)
            if group is None:
                group = groups[key] = {
                    'key': key, 'type': name, 'ids': [], 'deleted_by': r.get('deleted_by'),
                    'deleted_at': _iso(date), 'expires_at': _expires(date), '_date': date or datetime.datetime.min,
                    'dataset': None, 'image': None, 'categories': {}, 'items': [],
                }
                if ds is not None and ds in datasets:
                    d = datasets[ds]
                    group['dataset'] = {'id': ds, 'name': d.get('name'), 'deleted': bool(d.get('deleted'))}
            group['ids'].append(r['_id'])
            if name == 'annotation':
                image = images.get(r.get('image_id'))
                if image and group['image'] is None:
                    group['image'] = {'id': image['_id'], 'file_name': image.get('file_name'),
                                      'deleted': bool(image.get('deleted'))}
                cat = categories.get(r.get('category_id'), {})
                summary = group['categories'].setdefault(r.get('category_id'), {
                    'name': cat.get('name', '?'), 'color': cat.get('color'), 'n': 0})
                summary['n'] += 1
                group['items'].append({'id': r['_id'], 'category': cat.get('name', '?'), 'color': cat.get('color')})
            elif name == 'image':
                group['title'] = r.get('file_name')
                group['image'] = {'id': r['_id'], 'file_name': r.get('file_name'), 'deleted': True}
            elif name == 'category':
                group['title'] = r.get('name')
                group['color'] = r.get('color')
            else:
                group['title'] = r.get('name')
                group['images'] = ImageModel.objects(dataset_id=r['_id']).count()

    all_groups = sorted(groups.values(), key=lambda g: g['_date'], reverse=True)

    def matches(g):
        if dataset_id and (not g['dataset'] or g['dataset']['id'] != dataset_id):
            return False
        if q:
            text = " ".join(filter(None, [g.get('title'), (g.get('image') or {}).get('file_name'),
                                          (g.get('dataset') or {}).get('name'),
                                          *[c['name'] for c in g['categories'].values()]])).lower()
            return q in text
        return True

    filtered = [g for g in all_groups if matches(g)]
    counts = {name: 0 for name in TYPES}
    for g in filtered:
        counts[g['type']] += 1
    shown = [g for g in filtered if g['type'] in kinds]
    deleters = sorted({g['deleted_by'] or '-' for g in all_groups})
    dataset_options = sorted({(g['dataset']['id'], g['dataset']['name']) for g in all_groups if g['dataset']},
                             key=lambda d: d[1] or '')

    per_page = max(1, min(per_page, 100))
    pages = max(1, -(-len(shown) // per_page))
    page = max(1, min(page, pages))
    out = []
    for g in shown[(page - 1) * per_page: page * per_page]:
        g = dict(g)
        g.pop('_date')
        g['count'] = len(g['ids'])
        g['categories'] = sorted(g['categories'].values(), key=lambda c: -c['n'])
        g['items'] = g['items'][:100]
        out.append(g)
    return {
        'groups': out, 'total': len(shown), 'page': page, 'pages': pages,
        'counts': counts, 'all': sum(counts.values()),
        'deleters': deleters, 'datasets': [{'id': i, 'name': n} for i, n in dataset_options],
        'days': Config.TRASH_DAYS,
    }


# ------------------------------------------------------------- restoring

class NeedsParents(Exception):
    def __init__(self, parents):
        super().__init__("Their image or dataset is in the trash too")
        self.parents = parents


def _parents(kind, docs):
    """Trashed images / datasets the documents depend on."""
    parents = {'image': set(), 'dataset': set()}
    if kind == 'annotation':
        image_ids = {d.image_id for d in docs}
        for image in ImageModel.objects(id__in=list(image_ids)).only('id', 'deleted', 'dataset_id'):
            if image.deleted:
                parents['image'].add(image.id)
            dataset = DatasetModel.objects(id=image.dataset_id).only('id', 'deleted').first()
            if dataset is not None and dataset.deleted:
                parents['dataset'].add(dataset.id)
    elif kind == 'image':
        for d in docs:
            dataset = DatasetModel.objects(id=d.dataset_id).only('id', 'deleted').first()
            if dataset is not None and dataset.deleted:
                parents['dataset'].add(dataset.id)
    return {k: sorted(v) for k, v in parents.items() if v}


def restore(user, items, include_parents=False):
    """items: [{"type": ..., "ids": [...]}]. Returns how many were restored."""
    plan = []
    missing_parents = {}
    for item in items or []:
        model = TYPES.get(item.get('type')) if isinstance(item, dict) else None
        if model is None:
            continue
        docs = list(visible(model, user).filter(id__in=_ids(item)))
        if not docs:
            continue
        for kind, ids in _parents(item['type'], docs).items():
            missing_parents.setdefault(kind, set()).update(ids)
        plan.append((item['type'], model, docs))

    if missing_parents and not include_parents:
        raise NeedsParents({k: sorted(v) for k, v in missing_parents.items()})

    restored = 0
    if include_parents:
        for kind in ('dataset', 'image'):
            ids = missing_parents.get(kind)
            if ids:
                parent_docs = visible(TYPES[kind], user).filter(id__in=list(ids))
                restored += parent_docs.count()
                parent_docs.update(set__deleted=False, unset__deleted_date=True,
                                   unset__deleted_by=True, unset__delete_batch=True)

    touched_images = set()
    for kind, model, docs in plan:
        model.objects(id__in=[d.id for d in docs]).update(
            set__deleted=False, unset__deleted_date=True, unset__deleted_by=True, unset__delete_batch=True)
        restored += len(docs)
        if kind == 'annotation':
            touched_images |= {d.image_id for d in docs}
    for image_id in touched_images:
        refresh_image(image_id)
    return restored


# ------------------------------------------------------------- purging

def _purge_docs(kind, docs):
    count = 0
    for doc in docs:
        try:
            if kind == 'image':
                if doc.path and os.path.isfile(doc.path):
                    os.remove(doc.path)
                doc.delete()  # also deletes its annotations and thumbnail
            elif kind == 'dataset':
                purge_dataset(doc)
            elif kind == 'category':
                # no dataset may keep pointing at it (stats, exports look it up)
                DatasetModel.objects(categories=doc.id).update(pull__categories=doc.id)
                doc.delete()
            else:
                doc.delete()
            count += 1
        except Exception:
            logger.exception(f"Could not permanently delete {kind} {doc.id}")
    return count


def purge_dataset(dataset, keep_files=False):
    """Delete a dataset's records for good (and its folder unless keep_files)."""
    image_ids = [i['_id'] for i in ImageModel.objects(dataset_id=dataset.id).only('id').as_pymongo()]
    AnnotationModel.objects(image_id__in=image_ids).delete()
    ImageModel.objects(dataset_id=dataset.id).delete()
    if not keep_files and dataset.directory and os.path.isdir(dataset.directory):
        shutil.rmtree(dataset.directory, ignore_errors=True)
    dataset.delete()


def _purgeable(model, user, docs):
    """Images (and their files) go for good: only the dataset owner (or an
    admin) may do that; members can still restore them."""
    if model is not ImageModel or user.is_admin:
        return docs
    owned = {d.id for d in DatasetModel.objects(owner=user.username).only('id')}
    return [d for d in docs if d.dataset_id in owned]


def purge(user, items):
    """Permanently delete trashed items (files on disk too)."""
    count = 0
    for item in items or []:
        model = TYPES.get(item.get('type')) if isinstance(item, dict) else None
        if model is None:
            continue
        docs = _purgeable(model, user, list(visible(model, user).filter(id__in=_ids(item))))
        count += _purge_docs(item['type'], docs)
    return count


def empty(user):
    count = 0
    for kind, model in TYPES.items():
        count += _purge_docs(kind, _purgeable(model, user, list(visible(model, user))))
    return count


_last_cleanup = [None]
_cleanup_lock = threading.Lock()


def purge_expired(force=False):
    """Permanently delete what has been in the trash longer than TRASH_DAYS
    (checked at most once an hour)."""
    days = Config.TRASH_DAYS
    if not days:
        return 0
    with _cleanup_lock:
        if not force and _last_cleanup[0] and (now() - _last_cleanup[0]).total_seconds() < 3600:
            return 0
        _last_cleanup[0] = now()
    limit = now() - datetime.timedelta(days=days)
    count = 0
    for kind, model in TYPES.items():
        docs = list(model.objects(deleted=True, deleted_date__lt=limit))
        count += _purge_docs(kind, docs)
    if count:
        logger.info(f"Trash: permanently deleted {count} items older than {days} days")
    from . import activity
    activity.expire()
    return count


# ------------------------------------------------------------- previews

def preview(image, annotations, size=160, crop=False):
    """JPEG bytes: the image (or the area around the annotations) with their
    shapes outlined."""
    with Image.open(image.path) as im:
        im = im.convert("RGB")
        polys = [[float(v) for v in p] for a in annotations for p in (a.segmentation or [])
                 if isinstance(p, list) and len(p) >= 6]
        x0, y0, x1, y1 = 0, 0, im.width, im.height
        if crop and polys:
            xs = [v for p in polys for v in p[0::2]]
            ys = [v for p in polys for v in p[1::2]]
            bw, bh = max(xs) - min(xs), max(ys) - min(ys)
            margin = max(bw, bh) * 0.25 + 8
            x0, y0 = max(0, int(min(xs) - margin)), max(0, int(min(ys) - margin))
            x1, y1 = min(im.width, int(max(xs) + margin)), min(im.height, int(max(ys) + margin))
            im = im.crop((x0, y0, x1, y1))
        scale = size / max(im.width, im.height)
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))))
        draw = ImageDraw.Draw(im)
        width = max(2, int(size / 80))
        for a in annotations:
            color = getattr(a, 'color', None) or "#ff3b30"
            for p in a.segmentation or []:
                if not isinstance(p, list) or len(p) < 6:
                    continue
                pts = [((p[i] - x0) * scale, (p[i + 1] - y0) * scale) for i in range(0, len(p) - 1, 2)]
                draw.line(pts + [pts[0]], fill=color, width=width)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85)
        return out.getvalue()
