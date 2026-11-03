<p align="center"><img src="https://i.imgur.com/AA7IdbQ.png"></p>

<p align="center"><a href="README.md">繁體中文</a> ｜ English</p>

<p align="center"><i>2026 modernisation and new features by <b>TsaiCC × Claude</b> — original project by <a href="https://github.com/jsbroks/coco-annotator">Justin Brooks</a></i></p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick start</a> •
  <a href="UPGRADE.md">Upgrading</a> •
  <a href="https://github.com/Tsaicc-biovlsi/coco-annotator/issues">Issues</a> •
  <a href="#license">License</a>
</p>

---

COCO Annotator is a web-based image annotation tool designed for versatility and efficiently label images to create training data for image localization and object detection. It provides many distinct features including the ability to label an image segment (or part of a segment), track object instances, labeling objects with disconnected visible parts, efficiently storing and export annotations in the well-known [COCO format](http://cocodataset.org/#format-data). The annotation process is delivered through an intuitive and customizable interface and provides many tools for creating accurate datasets.


<br />

<p align="center">The original project's <a href="https://discord.gg/4zP5Qkj">discord community</a></p>
<p align="center">
  <a href="https://discord.gg/4zP5Qkj">
    <img src="https://discord.com/assets/e4923594e694a21542a489471ecffa50.svg" width="120">
  </a>
</p>

<br />

<p align="center"><a href="http://www.youtube.com/watch?feature=player_embedded&v=OMJRcjnMMok" target="_blank"><img src="https://img.youtube.com/vi/OMJRcjnMMok/maxresdefault.jpg" 
alt="Image annotations using COCO Annotator" width="600" /></a></p>
<p align="center"><i>Video guide for the original version (installation steps differ, see Quick start below).</i></p>

<br />

<p align="center"><img width="600" src="https://i.imgur.com/m4RmjCp.gif"></p>
<p align="center"><i>Note: This video is from v0.1.0 and many new features have been added.</i></p>


<br>

<p align="center">Support the original author, Justin Brooks</p>
<p align="center">
  <a href="https://www.patreon.com/jsbroks">
    <img src="https://c5.patreon.com/external/logo/become_a_patron_button@2x.png" width="120">
  </a>
</p>
<br>

# Features

Several annotation tools are currently available, with most applications as a desktop installation. Once installed, users can manually define regions in an image and creating a textual description. Generally, objects can be marked by a bounding box, either directly, through a masking tool, or by marking points to define the containing area. _COCO Annotator_ allows users to annotate images using free-form curves or polygons and provides many additional features were other annotations tool fall short.

- Directly export to COCO format
- Segmentation of objects
- Ability to add key points
- Useful API endpoints to analyze data
- Import datasets already annotated in COCO format
- **COCO ↔ YOLO conversion:** export a dataset as YOLO labels (detect, segment, OBB, pose, classify, semantic segmentation; zip with `data.yaml`, `classes.txt` and a folder you name holding `train/labels` (optionally `train/images`), optionally split into train / val / test by percentage with a reproducible seed) and import YOLO label zips or whole YOLO dataset folders. Offline: `python scripts/coco_yolo.py coco2yolo|yolo2coco ...`
- Annotate disconnect objects as a single instance
- Labeling image segments with any number of labels simultaneously
- Allow custom metadata for each instance or object
- **Rotated (oriented) bounding boxes** with rotate / resize / move handles, exported as `rbbox = [cx, cy, w, h, angle]` and exported as YOLO-OBB or converted to DOTA
- AI-assisted segmentation with [Segment Anything 2.1](https://github.com/facebookresearch/sam2) (or the original SAM) (click / box prompts) and Magic Wand
- Pre-annotate an image or a whole dataset with your own Ultralytics YOLO models (detect, OBB, segment, pose)
- Annotate images with semi-trained models (external model server)
- User authentication system
- Review workflow: assign images to members, submit for review, approve / reject with a note, progress per member, export only approved images
- Whole-image class labels for image classification
- Dataset health: class balance, object sizes and locations, and likely problems (unlabelled images, duplicates, boxes outside the image…)
- Video import: one frame every N seconds becomes a dataset image
- Interface in English and Traditional Chinese (繁體中文)

Usage is described in the [Chinese README](README.md) and [UPGRADE.md](UPGRADE.md). The [original project's wiki](https://github.com/jsbroks/coco-annotator/wiki) still covers the basics.

# Quick start

```bash
docker compose up -d --build        # http://localhost:5000
```

Put images in `./datasets/<dataset name>/`. For Segment Anything run
`./models/download_sam.sh` and build with `SAM=cpu` (or use
`docker-compose.gpu.yml`). Upgrading an existing installation? Read
[UPGRADE.md](UPGRADE.md) first — the MongoDB data needs a one-time migration.

# Backers

If you enjoy the development of coco-annotator or are looking for an enterprise annotation tool, consider checking out DataTorch.

<p align="center">
  <a href="https://datatorch.io">
    <img src="https://i.imgur.com/sOQ1s5F.png" width="250" />
  </a>
  <p align="center">
    https://datatorch.io · <a href="mailto:support@datatorch.io">support@datatorch.io</a> · <i>Next generation of coco-annotator</i>
   </p>
</p>

# Built With

Thanks to all these wonderful libaries/frameworks:

### Backend

- [Flask](https://flask.palletsprojects.com/) 3 + [Flask-RESTX](https://github.com/python-restx/flask-restx) - Python web framework and REST API
- [MongoDB](https://www.mongodb.com/) 7 + [MongoEngine](http://mongoengine.org/) - Document database and object mapper
- [Celery](https://docs.celeryq.dev/) 5 + [RabbitMQ](https://www.rabbitmq.com/) - Background tasks
- [Segment Anything](https://github.com/facebookresearch/segment-anything) + [PyTorch](https://pytorch.org/) - AI-assisted segmentation (optional)

### Frontend

- [Vue](https://vuejs.org/) 3 + [Vite](https://vite.dev/) - JavaScript framework and build tool
- [Axios](https://github.com/axios/axios) - Promise based HTTP client
- [PaperJS](http://paperjs.org/) - HTML canvas vector graphics library
- [Bootstrap](https://getbootstrap.com/) 5 - Frontend component library

# License

[MIT](https://tldrlegal.com/license/mit-license)

# Citation

```
  @MISC{cocoannotator,
    author = {Justin Brooks},
    title = {{COCO Annotator}},
    howpublished = "\url{https://github.com/jsbroks/coco-annotator/}",
    year = {2019},
  }
```
