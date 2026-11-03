# Upgrading to coco-annotator 1.0 (2026 modernisation)

This release moves every part of the stack off end-of-life software, replaces
the TensorFlow 1 AI tools with Segment Anything, and adds a rotated bounding
box tool.

## What changed

| Part | Before | Now |
|---|---|---|
| Frontend framework | Vue 2.5, Vuex 3, Vue Router 3 | **Vue 3.5**, Vuex 4, Vue Router 4 |
| Frontend build | Vue CLI 3 (webpack 4), Node 10 | **Vite 7**, Node 22 |
| Frontend tests | Jest 24 | Vitest |
| Python | 3.6 (TensorFlow 1.14 image) | **3.12** (`python:3.12-slim`) |
| Web framework | Flask 1.0, flask-restplus 0.12 (dead) | **Flask 3.1, flask-restx 1.3** |
| Realtime | Flask-SocketIO 3 + eventlet, vue-socket.io | Flask-SocketIO 5 (threading + simple-websocket), socket.io-client 4 |
| Task queue | Celery 4.2 | **Celery 5.5** |
| Database | MongoDB 4.0 | **MongoDB 7.0** (see migration below) |
| Message broker | RabbitMQ 3.7 | RabbitMQ 4.1 |
| AI assistance | DEXTR + Mask R-CNN (Keras 2.1 / TF 1.14) | **Segment Anything (PyTorch)** |
| Image libs | OpenCV 4.0, imantics, Pillow 5 | OpenCV 4.x headless, NumPy 2, Shapely 2, Pillow 11 |
| CSS framework | Bootstrap 4.1 + jQuery | **Bootstrap 5.3** (no jQuery) |

## New features

### Rotated bounding boxes (`O`)

Select an annotation, pick the **Rotated BBox** tool (tilted square icon or `O`), then
draw a box with three clicks:

1. click the first corner,
2. click the second corner — these two points are one edge of the box (its
   direction and length; you can also drag from the first point to the
   second; hold **Shift** to snap the angle, 15° by default),
3. move the mouse to set the width and click to finish (**Esc** cancels).

Edit the selected box by dragging the round handle (rotate, **Shift** snaps),
a corner (resize, the opposite corner stays fixed) or the inside (move).
Arrow keys move it by 1 px (**Shift**: 10 px). Like a BBox, it can also be
moved or resized with the **Select** tool (`S`); it stays a rectangle.
The thicker edge shows the box's *heading* (first edge); *Swap Heading*
rotates the corner order by 90° without moving the box. With this tool,
clicking another rotated box selects it; Ctrl+click starts a new box inside
an existing one. With SAM, clicking an existing shape does not select it;
pick annotations from the sidebar or with `S`.

Stored and exported per annotation:

```json
"isrbbox": true,
"rbbox": [cx, cy, w, h, angle],
"segmentation": [[x1, y1, x2, y2, x3, y3, x4, y4]]
```

`angle` is in degrees, clockwise in image coordinates (y down), measured along
the first edge (corner 1 → 2), normalised to (-180, 180]. `w` is the first
edge, `h` the second. The polygon keeps the corners in that order, so tools
that only understand COCO polygons still work. `bbox`/`area` are filled as
usual. COCO imports may contain `rbbox` without a polygon (e.g. converted from
DOTA); the polygon is generated.

To train oriented detectors:

```bash
python scripts/export_obb.py coco-export.json labels/ --format dota       # DOTA txt
python scripts/export_obb.py coco-export.json labels/ --format yolo-obb   # Ultralytics YOLO-OBB
```

### Segment Anything (`A`)

Select an annotation, pick the **SAM** tool (◎ icon or `A`):

* click the object (green point), **Shift**+click to exclude background (red),
* or drag a box around the object,
* press **Enter** (or *Apply*) to add the preview to the annotation.

The image embedding is computed once when the tool is selected and cached on
the server, so later clicks are fast (~50 ms). On CPU the first embedding of
an image takes a few seconds with `vit_b`; a GPU makes it near-instant.

Enable it:

```bash
./models/download_sam.sh            # vit_b checkpoint into ./models
SAM=cpu docker compose up -d --build                          # CPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build   # NVIDIA GPU
```

Without PyTorch or the checkpoint the tool is simply disabled.

### Pre-annotate with your own YOLO models

Copy trained Ultralytics YOLO weights (`.pt`, YOLOv8/YOLO11 and later) into
the `models/` folder (`MODELS_DIR`); subfolders are fine. Detect, OBB, segment
and pose models are supported and become boxes, rotated boxes, polygons and
box + keypoints. Requires an image built with `SAM=cpu` or `SAM=cuda` (the
same PyTorch install is used).

* **One image:** the rocket button in the annotator toolbar. Your work is
  saved, the model runs, and the predictions appear as normal annotations.
* **Whole dataset:** *Pre-annotate with Model* in the dataset sidebar. Runs in
  the background (progress under Tasks); optionally skips images that already
  have annotations.

Admins can also add or remove models in that dialog (upload a `.pt`; it is
checked by loading it before it is offered).

Classes are matched to the dataset's categories by name (case-insensitive);
missing ones can be created automatically. For pose models, a category
without keypoint labels gets them from the model (COCO names and skeleton for
17-keypoint models); keypoints below 0.5 confidence are left unlabelled.
New `.pt` files are picked up without restarting. Only put model files from
people you trust in this folder: loading a `.pt` file runs code from it.

## Migrating an existing installation

### 1. MongoDB data (required)

The new version keeps its data in the `mongodb7_data` volume. The original
`mongodb_data` volume (MongoDB 4.0, which MongoDB 7 cannot open) is never
touched, so the old installation can be restored at any time. Copy the data
over once, with the stack stopped:

```bash
cd coco-annotator            # the folder you run docker compose in
docker compose down
git fetch && git checkout upgrade-2026   # or unpack the new version here
./scripts/migrate_mongo.sh   # finds the old volume, dumps it, restores into mongodb7_data
docker compose up -d --build
```

The script dumps only the application database (`flask`), keeps a copy of the
dump in `mongo-dump-*/`, prints document counts per collection, and refuses to
run while a container still uses the old volume. If it cannot tell which old
volume to use (for example the project folder was renamed, or the stack was
started with the old `docker-compose` v1, which names it
`cocoannotator_mongodb_data`), pass it explicitly:
`OLD_VOLUME=<name> ./scripts/migrate_mongo.sh`.

If the old installation used the original `docker-compose.gpu.yml`, its
database is not in a volume but in the `db/` folder next to it; pass that
folder instead: `OLD_DIR=/path/to/old/coco-annotator/db ./scripts/migrate_mongo.sh`.

The new version can also be installed in a separate folder while the old one
stays untouched: set `DATASETS_DIR` in `.env` (see `.env.example`) to the old
`datasets` folder so both use the same images.

Rolling back: `docker compose down`, check out the original code
(`git checkout master`) and `docker compose up -d`; it still uses the old
volume. Images in `datasets/` are shared by both versions and not modified.

### 2. Images are built locally

The compose files no longer pull the old `jsbroks/coco-annotator:*` images.
`docker compose up -d --build` builds the `webserver` and `workers` targets
of the root `Dockerfile`.

### 3. Configuration

Removed environment variables: `MASK_RCNN_FILE`, `MASK_RCNN_CLASSES`,
`DEXTR_FILE`.

New ones:

| Variable | Default | Meaning |
|---|---|---|
| `SAM_MODEL_TYPE` | `vit_b` | `vit_b`, `vit_l` or `vit_h` |
| `SAM_CHECKPOINT` | `/models/sam_vit_b_01ec64.pth` | checkpoint path |
| `SAM_DEVICE` | `auto` | `auto`, `cpu` or `cuda` |
| `MODELS_DIRECTORY` | `/models` | folder (in the container) with your YOLO `.pt` files |
| `YOLO_DEVICE` | `auto` | `auto`, `cpu`, `cuda:0`, … |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | run tasks in the web process (development) |
| `VERSION` | git tag | version shown in the UI |
| `ALLOW_REGISTRATION` | `true` | `false`: only the first account can self-register; admins create users in the Admin panel. Now passed through by `docker-compose.yml` (set it in `.env`) |

`FILE_WATCHER=false` and `TESTING=false` are now honoured (previously any
non-empty value enabled them).

### 4. Users

Passwords stored by the old version (`sha256$…`) are still accepted and are
re-hashed with scrypt on the user's next login. No action needed.

### 5. Removed features / API

* `POST /api/model/dextr/<id>` and `POST /api/model/maskrcnn` → replaced by
  `POST /api/model/sam/<image_id>` (`points`, `labels`, `box`) and
  `POST /api/model/sam/<image_id>/prepare`. `GET /api/model/` reports what is
  available. The **Annotate Image** button (dataset "annotate URL") still
  works with any external model server that returns COCO.
* `POST /api/dataset/<id>/generate` (Google Images download) — the library it
  used stopped working years ago.

### Clear an image

The ⊗ button in the annotator toolbar deletes every annotation of the current
image (after a confirmation). They can be restored from the Undo page.

## Bugs fixed along the way

* Celery tasks (scan, import, export, thumbnails) were bound to a thread-local
  app; with a multi-threaded web server they were sent to the wrong broker.
* The file watcher thread died on the first half-written image.
* `Esc` in the annotator threw (`bbox.deletePolygon` did not exist).
* `GET /api/dataset/coco/<id>` referenced a model that no longer existed.
* Editing a category with a duplicate name raised `NameError`.
* Export download file names contained `b'…'`.
* `Dataset.vue` referenced an undefined `process` variable (worked only
  because webpack 4 injected a Node `process` shim).
* paper.js is loaded as a classic script: bundled as an ES module it runs in
  strict mode and throws while styling groups.

## Development

```bash
docker compose -f docker-compose.dev.yml up --build   # http://localhost:8080 (hot reload)

# or without Docker
cd backend && pip install -r requirements.txt mongomock && pytest   # no MongoDB/RabbitMQ needed
cd client && npm ci && npm run dev && npm test
```

Backend tests run against an in-memory MongoDB and execute Celery tasks
eagerly (`tests/conftest.py`), including an end-to-end API smoke test
(`tests/test_smoke.py`).

## Bootstrap 5

The UI moved from Bootstrap 4 + jQuery to Bootstrap 5.3 without jQuery
(modals use `src/libs/modal.js`). `src/assets/bootstrap-compat.css` keeps the
previous look where Bootstrap 5 changed defaults (link underlines, grid rows,
breadcrumb, container width). If you customised templates, rename
`data-toggle/target/dismiss` to `data-bs-*` and update renamed classes
(`ml-/mr-` → `ms-/me-`, `text-left/right` → `text-start/end`, `badge-*` →
`text-bg-*`, `btn-block` → `w-100`, …).

## Autosave

Annotation changes (shapes, keypoints, metadata) are saved automatically
about 2 seconds after the last edit, and pending changes are sent when the
tab is hidden, reloaded or closed. Previously they were only saved with
Save, when switching images or when leaving the page. Empty, just-created
annotations are left alone by autosave (a manual save still removes them).

## Languages

The interface is available in English and Traditional Chinese (繁體中文).
Pick the language from the globe menu in the navigation bar; the choice is
remembered in the browser, and on a first visit the browser language decides
(any Chinese variant selects Traditional Chinese).

Translations live in `client/src/i18n/locales/*.json` (vue-i18n). To add a
language, copy `en.json`, translate it, and register it in `LANGUAGES` in
`client/src/i18n/index.js`. A unit test checks that every English message has
a Traditional Chinese translation. Messages returned by the server (API error
texts) are still English.

## Keypoints

The Keypoints tool is enabled only when the selected annotation has a BBox or
rotated box: draw the object's box first, then place its keypoints.

The REST API and the URL scheme (`/#/annotate/<id>`) are unchanged.
