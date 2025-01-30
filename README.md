<p align="center"><img src="https://i.imgur.com/AA7IdbQ.png"></p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="https://github.com/jsbroks/coco-annotator/wiki">Wiki</a> •
  <a href="https://github.com/jsbroks/coco-annotator/wiki/Getting-Started">Getting Started</a> •
  <a href="https://github.com/jsbroks/coco-annotator/issues">Issues</a> •
  <a href="#license">License</a>
</p>

---

<p align="center">
  <a href="/jsbroks/coco-annotator/stargazers">
    <img src="https://img.shields.io/github/stars/jsbroks/coco-annotator.svg">
  </a>
  <a href="/jsbroks/coco-annotator/issues">
    <img src="https://img.shields.io/github/issues/jsbroks/coco-annotator.svg">
  </a>
  <a href="https://tldrlegal.com/license/mit-license">
    <img src="https://img.shields.io/github/license/mashape/apistatus.svg">
  </a>
  <a href="https://lgtm.com/projects/g/jsbroks/coco-annotator/context:javascript">
    <img src="https://img.shields.io/lgtm/grade/javascript/g/jsbroks/coco-annotator.svg?label=code%20quality">
  </a>
  <a href="https://annotator.justinbrooks.ca/">
    <img src="https://img.shields.io/badge/demo-online-green.svg">
  </a>
  <a href="https://travis-ci.org/jsbroks/coco-annotator">
    <img src="https://travis-ci.org/jsbroks/coco-annotator.svg?branch=master">
  </a>
  <a href="https://hub.docker.com/r/jsbroks/coco-annotator">
    <img src="https://img.shields.io/docker/pulls/jsbroks/coco-annotator.svg">
  </a>
</p>

COCO Annotator is a web-based image annotation tool designed for versatility and efficiently label images to create training data for image localization and object detection. It provides many distinct features including the ability to label an image segment (or part of a segment), track object instances, labeling objects with disconnected visible parts, efficiently storing and export annotations in the well-known [COCO format](http://cocodataset.org/#format-data). The annotation process is delivered through an intuitive and customizable interface and provides many tools for creating accurate datasets.


<br />

<p align="center">Join our growing <a href="https://discord.gg/4zP5Qkj">discord community</a> of ML practitioner</p>
<p align="center">
  <a href="https://discord.gg/4zP5Qkj">
    <img src="https://discord.com/assets/e4923594e694a21542a489471ecffa50.svg" width="120">
  </a>
</p>

<br />

<p align="center"><a href="http://www.youtube.com/watch?feature=player_embedded&v=OMJRcjnMMok" target="_blank"><img src="https://img.youtube.com/vi/OMJRcjnMMok/maxresdefault.jpg" 
alt="Image annotations using COCO Annotator" width="600" /></a></p>
<p align="center"><i>Checkout the video for a basic guide on installing and using COCO Annotator.</i></p>

<br />

<p align="center"><img width="600" src="https://i.imgur.com/m4RmjCp.gif"></p>
<p align="center"><i>Note: This video is from v0.1.0 and many new features have been added.</i></p>


<br>

<p align="center">If you enjoy my work please consider supporting me</p>
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
- Annotate disconnect objects as a single instance
- Labeling image segments with any number of labels simultaneously
- Allow custom metadata for each instance or object
- Advanced selection tools such as, [DEXTR](https://github.com/jsbroks/dextr-keras), [MaskRCNN](https://github.com/matterport/Mask_RCNN) and Magic Wand
- Annotate images with semi-trained models
- Generate datasets using google images
- User authentication system

For examples and more information check out the [wiki](https://github.com/jsbroks/coco-annotator/wiki).

# Demo

| Login Information      |
| ---------------------- |
| **Username:** admin    |
| **Password:** password |

https://annotator.justinbrooks.ca/

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

- [Flask](http://flask.pocoo.org/) - Python web microframework
- [MongoDB](https://www.mongodb.com/) - Cross-platform document-oriented database
- [MongoEngine](http://mongoengine.org/) - Python object data mapper for MongoDB

### Frontend

- [Vue](https://vuejs.org/) - JavaScript framework for building user interfaces
- [Axios](https://github.com/axios/axios) - Promise based HTTP client
- [PaperJS](http://paperjs.org/) - HTML canvas vector graphics library
- [Bootstrap](https://getbootstrap.com/) - Frontend component library

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
