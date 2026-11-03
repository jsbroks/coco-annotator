"""Import a video by saving frames at a fixed interval as dataset images.

Frames go to ``<dataset>/<video name>/<video name>_<time>.jpg`` (the time
as minutes-seconds-milliseconds, so names sort in playback order) and
are added to the dataset straight away. Runs as a background task.
"""
import datetime
import json
import logging
import os
import re
import threading
import time
import uuid

import cv2

from database import ActivityModel, DatasetModel, ImageModel, TaskModel

logger = logging.getLogger('gunicorn.error')

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv")


STAGE_HOURS = 24  # an uploaded video not imported after this long is removed


def stage_dir():
    from config import Config
    path = os.path.join(Config.DATASET_DIRECTORY, '.video-staging')
    os.makedirs(path, exist_ok=True)
    return path


def probe(path):
    """Length, fps, frame count and size of a video (frame count from the
    container; some formats only give an estimate)."""
    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        raise ValueError("The video could not be opened (unsupported format or codec)")
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        capture.release()
    if fps <= 0 or fps > 1000:
        fps = 30.0
    return {"fps": round(fps, 3), "frames": frames, "duration": round(frames / fps, 3) if frames else None,
            "width": width, "height": height}


def _clean_stage(directory):
    limit = time.time() - STAGE_HOURS * 3600
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < limit:
                os.remove(path)
        except OSError:
            pass


def stage(upload, user):
    """Keep an uploaded video until it is imported; returns its id and info."""
    name = os.path.basename((upload.filename or 'video').replace('\\', '/'))
    ext = os.path.splitext(name)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        raise ValueError('Unsupported video type: ' + (ext or name))
    directory = stage_dir()
    _clean_stage(directory)
    upload_id = uuid.uuid4().hex
    path = os.path.join(directory, upload_id + ext)
    upload.save(path)
    try:
        info = probe(path)
    except ValueError:
        os.remove(path)
        raise
    meta = {"name": name, "ext": ext, "user": getattr(user, 'username', None), "complete": True, **info}
    _write_meta(upload_id, meta)
    return {"upload_id": upload_id, "name": name, **info}


def _write_meta(upload_id, meta):
    with open(os.path.join(stage_dir(), upload_id + '.json'), 'w') as f:
        json.dump(meta, f)


# --- in pieces: big videos go up in chunks (proxies often cap one request,
# e.g. at 100 MB, and a dropped piece can be sent again)

def chunk_start(name, size, user):
    name = os.path.basename((name or 'video').replace('\\', '/'))
    ext = os.path.splitext(name)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        raise ValueError('Unsupported video type: ' + (ext or name))
    from config import Config
    if size is None or not 0 < size <= Config.MAX_VIDEO_SIZE:
        raise ValueError(f'The video must be smaller than {Config.MAX_VIDEO_SIZE // 1024 ** 3} GB')
    directory = stage_dir()
    _clean_stage(directory)
    upload_id = uuid.uuid4().hex
    open(os.path.join(directory, upload_id + ext), 'wb').close()
    _write_meta(upload_id, {"name": name, "ext": ext, "user": getattr(user, 'username', None),
                            "size": int(size), "complete": False})
    return {"upload_id": upload_id, "received": 0}


def chunk_append(upload_id, user, offset, data):
    """Add one piece at ``offset``; a piece sent twice (a retry) is not added again.
    Returns the bytes received so far."""
    found = staged(upload_id, user, complete=False)
    if found is None:
        raise LookupError('Unknown upload')
    path, meta = found
    received = os.path.getsize(path)
    if offset + len(data) <= received:
        return received                      # already have it
    if offset != received:
        raise ValueError(f'Expected the piece at {received}, got {offset}')
    if received + len(data) > meta['size']:
        raise ValueError('More data than the announced size')
    with open(path, 'ab') as f:
        f.write(data)
    os.utime(path)
    return received + len(data)


def chunk_finish(upload_id, user):
    found = staged(upload_id, user, complete=False)
    if found is None:
        raise LookupError('Unknown upload')
    path, meta = found
    if os.path.getsize(path) != meta['size']:
        raise ValueError(f"Only {os.path.getsize(path)} of {meta['size']} bytes arrived")
    try:
        info = probe(path)
    except ValueError:
        discard(upload_id, user, complete=False)
        raise
    meta.update(info, complete=True)
    _write_meta(upload_id, meta)
    return {"upload_id": upload_id, "name": meta['name'], **info}


def staged(upload_id, user, complete=True):
    """(path, meta) of a staged video of this user, or None (``complete``:
    fully uploaded, or still arriving in pieces)."""
    if not re.fullmatch(r'[0-9a-f]{32}', upload_id or ''):
        return None
    directory = stage_dir()
    try:
        with open(os.path.join(directory, upload_id + '.json')) as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None
    if meta.get('user') != getattr(user, 'username', None):
        return None
    if complete is not None and bool(meta.get('complete', True)) != complete:
        return None
    path = os.path.join(directory, upload_id + meta.get('ext', ''))
    return (path, meta) if os.path.isfile(path) else None


def discard(upload_id, user, complete=None):
    found = staged(upload_id, user, complete=complete)
    if found is None:
        return False
    for path in (found[0], os.path.join(stage_dir(), upload_id + '.json')):
        try:
            os.remove(path)
        except OSError:
            pass
    return True


def safe_stem(name):
    stem = os.path.splitext(os.path.basename(name or "video"))[0]
    stem = re.sub(r'[\\/:*?"<>|\s]+', "_", stem).strip("._")
    return stem[:80] or "video"


def frame_name(stem, ms):
    minutes, rest = divmod(int(round(ms)), 60000)
    seconds, millis = divmod(rest, 1000)
    return f"{stem}_{minutes:03d}m{seconds:02d}s{millis:03d}.jpg"


def extract_frames(video_path, out_dir, stem, every_seconds=1.0, max_frames=1000,
                   on_progress=None, quality=95, every_frames=None, start_seconds=0.0, end_seconds=None):
    """Save one frame every ``every_seconds`` (or every ``every_frames`` video
    frames) between ``start_seconds`` and ``end_seconds`` (the end of the video
    if None). Returns the saved paths."""
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("The video could not be opened (unsupported format or codec)")
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or fps > 1000:
            fps = 30.0
        step = max(1, int(every_frames)) if every_frames else max(1, int(round(every_seconds * fps)))
        first = max(0, int(round((start_seconds or 0) * fps)))
        last = int(round(end_seconds * fps)) if end_seconds is not None else None
        span_end = min(total - 1, last) if total > 0 and last is not None else (total - 1 if total > 0 else last)
        span = (span_end - first + 1) if span_end is not None else 0
        expected = min(max_frames, (span + step - 1) // step) if span > 0 else max_frames
        os.makedirs(out_dir, exist_ok=True)

        saved, index = [], 0
        while len(saved) < max_frames:
            if last is not None and index > last:
                break
            if not capture.grab():
                break
            if index >= first and (index - first) % step == 0:
                ok, frame = capture.retrieve()
                if ok and frame is not None:
                    path = os.path.join(out_dir, frame_name(stem, index * 1000.0 / fps))
                    cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    saved.append(path)
                    if on_progress and expected:
                        on_progress(min(99.0, 100.0 * len(saved) / expected))
            index += 1
        return saved, {"fps": round(fps, 3), "frames": total, "step": step, "first": first, "last": last}
    finally:
        capture.release()


def _run(task_id, dataset_id, video_path, original_name, every_seconds, max_frames, socket,
         every_frames=None, start_seconds=0.0, end_seconds=None):
    task = TaskModel.objects.get(id=task_id)
    dataset = DatasetModel.objects.get(id=dataset_id)
    task.update(status="PROGRESS")
    stem = safe_stem(original_name)
    out_dir = os.path.join(dataset.directory, stem)
    created = 0
    try:
        interval = f"{every_frames} frames" if every_frames else f"{every_seconds} s"
        span = f" from {start_seconds or 0} s to {'the end' if end_seconds is None else f'{end_seconds} s'}"
        task.info(f"Extracting a frame every {interval}{span} (at most {max_frames}) from {original_name}")
        paths, info = extract_frames(
            video_path, out_dir, stem, every_seconds, max_frames,
            on_progress=lambda p: task.set_progress(p, socket=socket), every_frames=every_frames,
            start_seconds=start_seconds, end_seconds=end_seconds)
        task.info(f"Video: {info['fps']} fps, {info['frames']} frames; kept every {info['step']}th frame")
        for path in paths:
            if ImageModel.objects(path=path).first() is not None:
                continue
            try:
                image = ImageModel.create_from_path(path, dataset.id)
                image.import_task = task_id  # lets the activity log take the frames back
                image.save()
                created += 1
            except Exception as e:  # e.g. created by the folder watcher at the same time
                logger.info(f"Frame {path} not added: {e}")
        task.info(f"Added {created} frames to {dataset.name}/{stem}/")
        if len(paths) >= max_frames:
            task.warning(f"Stopped at the limit of {max_frames} frames")
    except Exception as e:
        logger.exception("Video import failed")
        task.error(str(e))
    finally:
        try:
            os.remove(video_path)
        except OSError:
            pass
        ActivityModel.objects(task_id=task_id, action='video').update(
            set__counts={'images': created}, set__detail__folder=stem,
            set__updated_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
        task.set_progress(100, socket=socket)


def import_video(dataset, video_path, original_name, every_seconds=1.0, max_frames=1000,
                 user=None, socket=None, background=True, every_frames=None,
                 start_seconds=0.0, end_seconds=None):
    task = TaskModel(
        name=f"Importing video {os.path.basename(original_name)} into {dataset.name}",
        dataset_id=dataset.id,
        group="Video Import",
    )
    if user is not None:
        task.creator = user.username
    task.save()
    from . import activity
    activity.record('video', user, dataset_id=dataset.id, task_id=task.id,
                    detail={'file_name': os.path.basename(original_name),
                            'every_seconds': None if every_frames else every_seconds,
                            'every_frames': every_frames,
                            'start_seconds': start_seconds or None, 'end_seconds': end_seconds},
                    text=original_name)
    args = (task.id, dataset.id, video_path, original_name, every_seconds, max_frames, socket, every_frames,
            start_seconds, end_seconds)
    if background:
        threading.Thread(target=_run, args=args, daemon=True).start()
    else:
        _run(*args)
    return {"id": task.id, "name": task.name, "folder": safe_stem(original_name)}
