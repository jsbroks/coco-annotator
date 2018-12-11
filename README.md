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

COCO Annotator is a web-based image annotation tool designed for versatility and efficiently label images to create training data for image localization and object detection. It provides many distinct features including the ability to label an image segment (or part of a segment), track object instances, labeling objects with disconnected visible parts, efficiently storing and export annotations in the well-know [COCO format](http://cocodataset.org/#format-data). The annotation process is delivered though an intuitive and customizable interface and provided many tools for creating accurate datasets.

<p align="center"><img src="https://i.imgur.com/m4RmjCp.gif"></p>
<p align="center"><i>Note: This video is from v0.1.0 and many new features have been added.</i></p>

# Features

Several annotation tools are currently available, with most applications as a desktop installation. Once installed, users can manually define regions in an image and creating a textual description. Generally, objects can be marked by a bounding box, either directly, through a masking tool, or by marking points to define the containing area. _COCO Annotator_ allows users to annotate images using free-form curves or polygons and provides many additional features were other annotations tool fall short.

 - Directly export to COCO format
 - Segmentation of objects
 - Useful API endpoints to analyze data
 - Import datasets already annotated in COCO format
 - Annotated disconnected objects as a single instance
 - Labeling image segments with any number of labels simultaneously
 - Allow custom metadata for each instance or object
 - Magic wand/select tool
 - Generate datasets using google images

### Semi-automated Annotations

For cluttered images such as that in _Figure 1_, the image tends to be dense with many objects. In this figure, we can see numerous cars were the process to annotate each one becomes time-consuming. When tens of thousands such images need to be ground-truthed, an efficient annotation tool becomes more pressing. For starters, some type of semi-automatic marking of the image segments may be helpful in speeding up the annotation process. 

<p align="center"><img width="400" src="https://akm-img-a-in.tosshub.com/indiatoday/images/story/201412/traffic-snarls-2_650_122914113653.jpg"></p>
<p align="center">Figure 1: Traffic on an highway in Delhi</p>

This problem is solved through the use of two different methods. A tool called Magic Wand uses the flood fill algorithm to create a selection of pixels similar in color and shade. The second method allows users to configure external API call to a semi-trained model which then applies annotations return from the request.

### Annotation of Disconnected Objects

Annotated objects are not required to be composed of continuous segments. For example, if a car is partially blocked by a tree. The disjoint visible parts can be annotated as part of a single car without including the tree.

<p align="center"><img width="600" src="https://i.imgur.com/5OZOZ4K.jpg"></p>
<p align="center">Figure 2: Annotation of a single car object with visual disconnected parts</p>

# Backers

<p align="center"><a href="http://robotics.uoguelph.ca/"><img src="http://robotics.uoguelph.ca/images/banner.jpg"></p></a>
<p  align="center">Backed by the <a href="http://robotics.uoguelph.ca/">The Robotics Institute @ Guelph</a> (<a href="https://github.com/uoguelph-ri">GitHub</a>)</p>

# Built With

Thanks to all these wonderful libaries/frameworks:
 - [Flask](http://flask.pocoo.org/) - Python web microframework
 - [Vue](https://vuejs.org/) - Frontend javascript framework
 - [Axios](https://github.com/axios/axios) - Promise based HTTP client
 - [PaperJS](http://paperjs.org/) - Canvas editor library
 - [Bootstrap](https://getbootstrap.com/) - Frontend component library

# License
[MIT](https://tldrlegal.com/license/mit-license)
