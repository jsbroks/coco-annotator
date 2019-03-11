<p align="center"><img src="https://i.imgur.com/AA7IdbQ.png"></p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="https://github.com/jsbroks/coco-annotator/wiki">Wiki</a> •
  <a href="https://github.com/jsbroks/coco-annotator/wiki/Getting-Started">Getting Stated</a> •
  <a href="https://github.com/jsbroks/coco-annotator/issues">Issues</a> •
  <a href="#license">License</a>
</p>


---


[![GitHub Stars](https://img.shields.io/github/stars/jsbroks/coco-annotator.svg)](https://github.com/jsbroks/coco-annotator/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/jsbroks/coco-annotator.svg)](https://github.com/jsbroks/coco-annotator/issues) 
![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)
[![Code Quality](https://img.shields.io/lgtm/grade/javascript/g/jsbroks/coco-annotator.svg?label=code%20quality)](https://lgtm.com/projects/g/jsbroks/coco-annotator/context:javascript)
[![Demo](https://img.shields.io/badge/demo-online-green.svg)](https://annotator.justinbrooks.ca/)
[![Build Status](https://travis-ci.org/jsbroks/coco-annotator.svg?branch=master)](https://travis-ci.org/jsbroks/coco-annotator)
[![Docker Pulls](https://img.shields.io/docker/pulls/jsbroks/coco-annotator.svg)](https://hub.docker.com/r/jsbroks/coco-annotator)

COCO Annotator is a web-based image annotation tool designed for versatility and efficiently label images to create training data for image localization and object detection. It provides many distinct features including the ability to label an image segment (or part of a segment), track object instances, labeling objects with disconnected visible parts, efficiently storing and export annotations in the well-known [COCO format](http://cocodataset.org/#format-data). The annotation process is delivered through an intuitive and customizable interface and provides many tools for creating accurate datasets.

<p align="center"><img width="600" src="https://i.imgur.com/m4RmjCp.gif"></p>
<p align="center"><i>Note: This video is from v0.1.0 and many new features have been added.</i></p>

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
 - Magic wand/select tool
 - Generate datasets using google images
 - User authentication system

For examples and more information check out the [wiki](https://github.com/jsbroks/coco-annotator/wiki).

# Demo

| Login Information |
| ----------------- |
| __Username:__ admin   |
| __Password:__ password |

https://annotator.justinbrooks.ca/

# Backers
Thanks to the backers for making this project possible!

<p align="center">
  <a href="http://robotics.uoguelph.ca/"><img src="http://robotics.uoguelph.ca/images/banner.jpg" width=200></a>
</p>
<p  align="center">
  <a href="http://robotics.uoguelph.ca/">The Robotics Institute @ Guelph</a> (<a href="https://github.com/uoguelph-ri">GitHub</a>)
</p>

<p align="center">
  <a href="https://intvo.com/"><img src="https://intvo.com/wp-content/uploads/2019/02/INTVO-6.png" width=200></a>
</p>
<p  align="center">
  <a href="https://intvo.com/">INTVO</a> (<a href="https://github.com/intvo">GitHub</a>)
</p>

# Built With

Thanks to all these wonderful libaries/frameworks:
 - [Flask](http://flask.pocoo.org/) - Python web microframework
 - [Vue](https://vuejs.org/) - Frontend javascript framework
 - [Axios](https://github.com/axios/axios) - Promise based HTTP client
 - [PaperJS](http://paperjs.org/) - Canvas editor library
 - [Bootstrap](https://getbootstrap.com/) - Frontend component library

# License
[MIT](https://tldrlegal.com/license/mit-license)
