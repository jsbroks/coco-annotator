"""Activity log: who did what, when ("tester imported 845 annotations into ships").

Every action that changes data writes one line here. Annotating is merged per
user and image while it goes on (``MERGE_MINUTES``), so drawing ten boxes on
one picture is one line ("added 10 annotations on a.jpg"). Deletes keep the
trash batch they created, so the log can restore them. Imports keep their
task id, so the annotations (or video frames) they created can be taken back.
Lines older than ``Config.TRASH_DAYS`` are removed with the trash.
"""
import datetime
import logging

from mongoengine import Q

from config import Config
from database import ActivityModel, AnnotationModel, CategoryModel, DatasetModel, ImageModel

logger = logging.getLogger('gunicorn.error')

MERGE_MINUTES = 30
MAX_IDS = 500  # ids kept per line (enough for previews and per-item restore)

#: filter tabs -> actions
GROUPS = {
    'annotate': ['annotate', 'copy', 'auto_annotate'],
    'import': ['import', 'video', 'upload', 'scan', 'export'],
    'delete': ['delete', 'restore', 'purge', 'undo_import'],
    'dataset': ['dataset_create', 'dataset_update', 'dataset_share', 'category_create',
                'category_update', 'reviewers'],
    'review': ['review', 'assign', 'help_request', 'help_reply'],
    # accounts, roles, models, tasks
    'admin': ['user_create', 'user_bulk', 'user_update', 'user_delete', 'password_change',
              'role_create', 'role_update', 'role_delete', 'model_upload', 'model_update',
              'model_delete', 'task_delete', 'task_clear', 'train', 'terminal'],
}


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _name(user):
    return getattr(user, 'username', None) if user is not None else None


def _text(*parts):
    return " ".join(str(p) for p in parts if p).lower()


def record(action, user=None, dataset_id=None, image_id=None, category_id=None,
           counts=None, detail=None, text="", **fields):
    """Write one line. Never fails the action it describes."""
    try:
        dataset = DatasetModel.objects(id=dataset_id).only('name').first() if dataset_id else None
        detail = dict(detail or {})
        if dataset is not None:
            detail.setdefault('dataset_name', dataset.name)
        entry = ActivityModel(
            action=action, user=_name(user), dataset_id=dataset_id, image_id=image_id,
            category_id=category_id, counts=counts or {}, detail=detail,
            text=_text(text, detail.get('dataset_name'), detail.get('file_name'), detail.get('name')),
            **fields)
        entry.save()
        return entry
    except Exception:  # pragma: no cover - logging must not break the action
        logger.exception(f"Could not record activity {action}")
        return None


def _recent(action, user, **match):
    since = now() - datetime.timedelta(minutes=MERGE_MINUTES)
    return ActivityModel.objects(action=action, user=_name(user), updated_at__gte=since,
                                 **match).order_by('-updated_at').first()


# ------------------------------------------------------------- annotating

def _annotate_entry(user, image):
    entry = _recent('annotate', user, image_id=image.id)
    if entry is None:
        entry = record('annotate', user, dataset_id=image.dataset_id, image_id=image.id,
                       detail={'file_name': image.file_name}, text=image.file_name,
                       added=[], edited=[], pending=[], hidden=True)
    return entry


def _has_shape(annotation):
    return (annotation.area or 0) > 0 or bool(annotation.keypoints) or bool(annotation.segmentation)


def annotation_created(user, annotation, image=None):
    """A new annotation; it counts once it has a shape (the annotator creates
    an empty one first and draws it later)."""
    try:
        image = image or ImageModel.objects(id=annotation.image_id).first()
        if image is None:
            return
        entry = _annotate_entry(user, image)
        if entry is None:
            return
        if _has_shape(annotation):
            entry.update(push__added=annotation.id, set__hidden=False, set__updated_at=now())
        else:
            entry.update(push__pending=annotation.id)
    except Exception:  # pragma: no cover
        logger.exception("Could not record a new annotation")


def annotation_saved(user, image, annotation_id, has_shape, changed):
    """Called for each annotation the annotator saves."""
    if not has_shape:
        return
    try:
        waiting = ActivityModel.objects(action='annotate', image_id=image.id, pending=annotation_id).first()
        if waiting is not None:
            waiting.update(pull__pending=annotation_id, push__added=annotation_id,
                           set__hidden=False, set__updated_at=now())
            return
        if not changed:
            return
        entry = _annotate_entry(user, image)
        if entry is None or annotation_id in (entry.added or []):
            return
        entry.update(add_to_set__edited=annotation_id, set__hidden=False, set__updated_at=now())
    except Exception:  # pragma: no cover
        logger.exception("Could not record an annotation change")


def annotations_saved(user, image, saved):
    """One annotator save: ``saved`` = [(annotation_id, has_shape, changed)].
    At most three queries, however many annotations the image has."""
    try:
        shaped = [a for a, has_shape, _ in saved if has_shape]
        if not shaped:
            return
        moved = set()
        for waiting in ActivityModel.objects(action='annotate', image_id=image.id, pending__in=shaped):
            ids = [a for a in shaped if a in (waiting.pending or [])]
            if ids:
                waiting.update(pull_all__pending=ids, push__added=ids,
                               set__hidden=False, set__updated_at=now())
                moved.update(ids)
        changed = [a for a, has_shape, ch in saved if has_shape and ch and a not in moved]
        if not changed:
            return
        entry = _annotate_entry(user, image)
        if entry is None:
            return
        changed = [a for a in changed if a not in (entry.added or [])]
        if changed:
            entry.update(add_to_set__edited=changed, set__hidden=False, set__updated_at=now())
    except Exception:  # pragma: no cover
        logger.exception("Could not record annotation changes")


def image_class_set(user, image, category):
    try:
        entry = _annotate_entry(user, image)
        if entry is not None:
            entry.update(set__detail__image_class=category.name if category else None,
                         set__detail__image_class_set=True, set__hidden=False, set__updated_at=now())
    except Exception:  # pragma: no cover
        logger.exception("Could not record an image class")


def images_uploaded(user, dataset, image):
    """Uploads are merged per user and dataset."""
    entry = _recent('upload', user, dataset_id=dataset.id)
    if entry is None:
        record('upload', user, dataset_id=dataset.id, counts={'images': 1},
               detail={'file_name': image.file_name}, text=image.file_name)
    else:
        entry.update(inc__counts__images=1, set__updated_at=now(),
                     set__text=(entry.text or '') + ' ' + image.file_name.lower())


# ------------------------------------------------------------- deletes

def deleted(user, kind, docs, batch):
    """One line for one trip to the trash (docs: the documents just deleted)."""
    if not docs:
        return
    first = docs[0]
    detail, counts, text = {}, {kind + 's': len(docs)}, []
    dataset_id = image_id = category_id = None
    if kind == 'annotation':
        image = ImageModel.objects(id=first.image_id).only('id', 'file_name', 'dataset_id').first()
        if image is not None:
            image_id, dataset_id = image.id, image.dataset_id
            detail['file_name'] = image.file_name
        categories = {c.id: c for c in CategoryModel.objects(id__in=list({d.category_id for d in docs}))
                      .only('id', 'name', 'color')}
        summary = {}
        for d in docs:
            c = categories.get(d.category_id)
            s = summary.setdefault(d.category_id, {'name': c.name if c else '?',
                                                   'color': c.color if c else None, 'n': 0})
            s['n'] += 1
        detail['categories'] = sorted(summary.values(), key=lambda s: -s['n'])
        detail['items'] = [{'id': d.id, 'category': summary[d.category_id]['name'],
                            'color': summary[d.category_id]['color']} for d in docs[:MAX_IDS]]
        text += [s['name'] for s in summary.values()]
    elif kind == 'image':
        image_id, dataset_id = first.id, first.dataset_id
        detail['file_name'] = first.file_name if len(docs) == 1 else None
        text += [d.file_name for d in docs[:50]]
    elif kind == 'category':
        category_id = first.id
        detail['name'], detail['color'] = first.name, first.color
    elif kind == 'dataset':
        dataset_id = first.id
        detail['name'] = first.name
        counts['images'] = ImageModel.objects(dataset_id=first.id).count()
    detail['kind'] = kind
    record('delete', user, dataset_id=dataset_id, image_id=image_id, category_id=category_id,
           counts=counts, detail=detail, text=" ".join(t for t in text if t), batch=batch,
           items=[{'type': kind, 'ids': [d.id for d in docs]}])


def trash_state(entry):
    """How many of a delete's items are still in the trash / restored / gone."""
    state = {'in_trash': 0, 'restored': 0, 'purged': 0, 'ids': []}
    from .trash import TYPES
    for item in entry.items or []:
        model = TYPES.get(item.get('type'))
        ids = item.get('ids', [])
        if model is None or not ids:
            continue
        docs = model.objects(id__in=ids).only('id', 'deleted', 'delete_batch').as_pymongo()
        seen = set()
        for d in docs:
            seen.add(d['_id'])
            if d.get('deleted') and d.get('delete_batch') == entry.batch:
                state['in_trash'] += 1
                state['ids'].append(d['_id'])
            else:
                state['restored'] += 1
        state['purged'] += len(ids) - len(seen)
    return state


def batches_in_trash():
    from .trash import TYPES
    batches = set()
    for model in TYPES.values():
        batches |= set(model.objects(deleted=True).distinct('delete_batch'))
    batches.discard(None)
    return batches


def backfill_trash():
    """Give things deleted before the activity log a line of their own, so the
    log is also the trash."""
    from .trash import list_groups, TYPES
    import uuid

    class Everyone:
        is_admin = True
        username = None

    known = set(ActivityModel.objects(action='delete').distinct('batch'))
    groups = list_groups(Everyone(), per_page=100000)['groups']
    made = 0
    for g in groups:
        model = TYPES[g['type']]
        docs = list(model.objects(id__in=g['ids']))
        if not docs:
            continue
        batch = docs[0].delete_batch if getattr(docs[0], 'delete_batch', None) else None
        if batch and batch in known and all(getattr(d, 'delete_batch', None) == batch for d in docs):
            continue
        if not batch or any(getattr(d, 'delete_batch', None) != batch for d in docs):
            batch = uuid.uuid4().hex[:16]
            model.objects(id__in=[d.id for d in docs]).update(set__delete_batch=batch)
        when = docs[0].deleted_date or now()

        class Who:
            username = docs[0].deleted_by if getattr(docs[0], 'deleted_by', None) else None

        deleted(Who() if Who.username else None, g['type'], docs, batch)
        ActivityModel.objects(batch=batch).update(set__created_at=when, set__updated_at=when)
        known.add(batch)
        made += 1
    return made


# ------------------------------------------------------------- imports

def undo_import(user, entry):
    """Send what an import created to the trash (as one delete line)."""
    from .trash import soft_delete, refresh_image
    batch = None
    count = 0
    if entry.action == 'video':
        images = ImageModel.objects(import_task=entry.task_id, deleted=False)
        docs = list(images)
        if docs:
            batch = soft_delete(images, user)
            count = len(docs)
    else:
        annotations = AnnotationModel.objects(import_task=entry.task_id, deleted=False)
        docs = list(annotations)
        if docs:
            image_ids = {d.image_id for d in docs}
            batch = soft_delete(annotations, user)
            count = len(docs)
            for image_id in image_ids:
                refresh_image(image_id)
    entry.update(set__undone_by=_name(user), set__undone_at=now(), set__undo_batch=batch)
    return count


# ------------------------------------------------------------- listing

def _dataset_ids(user):
    return [d.id for d in DatasetModel.objects(Q(owner=user.username) | Q(users__contains=user.username)).only('id')]


def visible(user):
    if user.is_admin:
        return ActivityModel.objects
    return ActivityModel.objects(Q(user=user.username) | Q(dataset_id__in=_dataset_ids(user)))


def _iso(value):
    return value.replace(microsecond=0).isoformat() + 'Z' if value else None


def _filtered(user, group=None, dataset_id=None, who=None, q=None, trash=None):
    query = visible(user).filter(hidden__ne=True)
    if group == 'trash':
        query = query.filter(action='delete', batch__in=list(trash))
    elif group in GROUPS:
        query = query.filter(action__in=GROUPS[group])
    if dataset_id:
        query = query.filter(dataset_id=dataset_id)
    if who:
        query = query.filter(user=None if who == '-' else who)
    if q:
        query = query.filter(text__icontains=q.strip().lower())
    return query


def list_activity(user, group="all", dataset_id=None, who=None, q="", page=1, per_page=30):
    trash = batches_in_trash()
    query = _filtered(user, group, dataset_id, who, q, trash)
    total = query.count()
    per_page = max(1, min(per_page, 100))
    pages = max(1, -(-total // per_page))
    page = max(1, min(page, pages))
    entries = list(query.order_by('-updated_at', '-id').skip((page - 1) * per_page).limit(per_page))

    datasets = {d.id: d for d in DatasetModel.objects(id__in=list({e.dataset_id for e in entries if e.dataset_id}))
                .only('id', 'name', 'deleted')}
    image_ids = {e.image_id for e in entries if e.image_id}
    images = {i.id: i for i in ImageModel.objects(id__in=list(image_ids)).only('id', 'file_name', 'deleted')}

    out = []
    for e in entries:
        row = {
            'id': e.id, 'action': e.action, 'user': e.user,
            'created_at': _iso(e.created_at), 'updated_at': _iso(e.updated_at),
            'counts': e.counts or {}, 'detail': e.detail or {},
            'dataset': None, 'image': None,
        }
        d = datasets.get(e.dataset_id)
        if e.dataset_id:
            row['dataset'] = {'id': e.dataset_id, 'name': d.name if d else (e.detail or {}).get('dataset_name'),
                              'deleted': bool(d.deleted) if d else True}
        i = images.get(e.image_id)
        if i is not None:
            row['image'] = {'id': i.id, 'file_name': i.file_name, 'deleted': bool(i.deleted)}
        if e.action == 'annotate':
            row['counts'] = {'added': len(e.added or []), 'edited': len(e.edited or [])}
            row['annotation_ids'] = list(e.added or [])[-50:] + list(e.edited or [])[-50:]
        elif e.action == 'delete':
            state = trash_state(e)
            row['trash'] = {k: state[k] for k in ('in_trash', 'restored', 'purged')}
            row['ids'] = state['ids']
            row['type'] = (e.detail or {}).get('kind')
            row['expires_at'] = _iso(e.created_at + datetime.timedelta(days=Config.TRASH_DAYS)) \
                if Config.TRASH_DAYS and state['in_trash'] else None
        elif e.action in ('import', 'video') or (e.action == 'auto_annotate' and e.task_id):
            row['task_id'] = e.task_id
            row['undone'] = {'by': e.undone_by, 'at': _iso(e.undone_at)} if e.undone_at else None
            row['can_undo'] = not e.undone_at and bool((e.counts or {}).get('images' if e.action == 'video'
                                                                           else 'annotations'))
        out.append(row)

    base = visible(user).filter(hidden__ne=True)
    counts = {g: base.filter(action__in=acts).count() for g, acts in GROUPS.items()}
    counts['trash'] = base.filter(action='delete', batch__in=list(trash)).count()
    counts['all'] = base.count()
    users = sorted({u or '-' for u in base.distinct('user')})
    dataset_options = DatasetModel.objects(id__in=[i for i in base.distinct('dataset_id') if i]).only('id', 'name')
    return {
        'entries': out, 'total': total, 'page': page, 'pages': pages, 'counts': counts,
        'users': users, 'datasets': sorted([{'id': d.id, 'name': d.name} for d in dataset_options],
                                           key=lambda d: d['name'] or ''),
        'days': Config.TRASH_DAYS,
    }


def expire():
    """Drop lines older than TRASH_DAYS (called with the trash cleanup)."""
    days = Config.TRASH_DAYS
    if not days:
        return 0
    return ActivityModel.objects(updated_at__lt=now() - datetime.timedelta(days=days)).delete()


def mark_sources(dataset_id):
    """Model runs / imports from before annotations were marked with their
    source: the activity log knows their task."""
    from database import AnnotationModel
    for entry in ActivityModel.objects(dataset_id=dataset_id, action__in=['auto_annotate', 'import'],
                                       task_id__ne=None).only('action', 'task_id', 'detail'):
        if entry.action == 'auto_annotate':
            AnnotationModel.objects(import_task=entry.task_id, source__exists=False).update(
                set__source='model', set__model=(entry.detail or {}).get('model'))
        else:
            AnnotationModel.objects(import_task=entry.task_id, source__exists=False).update(set__source='import')
