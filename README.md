<p align="center"><img src="https://i.imgur.com/AA7IdbQ.png"></p>
<p align="center">
  Coco Annotator is currently in the alpha stage of development. Please report any bugs and issues.
</p>

---

A web based image annotation tool used to create training data for machine learning. It provides many distinct features
including the ability to label an image segment (or part of a segment), track object instances, labeling objects with
disconnected visible parts and efficiently storing the annotation and instances information in the well-know [COCO
format](http://cocodataset.org/#format-data). The annotation process is delivered though an initiative and customizable interface similar to PhotoShop.

<p align="center"><img src="https://i.imgur.com/qce0qzk.gif"></p>


## Table of Contents

- [Getting Started](https://github.com/jsbroks/coco-annotator#getting-started)
  - [Prerequisites](https://github.com/jsbroks/coco-annotator#prerequisites)
  - [Installing](https://github.com/jsbroks/coco-annotator#installing)
- [Usage](https://github.com/jsbroks/coco-annotator#usage)
  - [Editor](https://github.com/jsbroks/coco-annotator#editor)
    - [Tool Bar](https://github.com/jsbroks/coco-annotator#tool-bar)
    - [Annotation Bar](https://github.com/jsbroks/coco-annotator#annotation-bar)
  - [Undo](https://github.com/jsbroks/coco-annotator#undo)
  - [API](https://github.com/jsbroks/coco-annotator#api)
- [Built With](https://github.com/jsbroks/coco-annotator#built-with)
- [License](https://github.com/jsbroks/coco-annotator#getting-started)

## Getting Started

### Prerequisites

[Docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/)
is required. You can follow there documentation for installation in the links provided.

### Installing

Create a copy of this repository:
```bash
git clone https://github.com/jsbroks/coco-annotator
cd coco-annotator
```

Run the application using docker compose:
```bash
docker-compose up --build
```

Give it a few minutes to build the docker image.

Now, you can now access the website (<http://localhost:5000/>).

# Usage

### Editor

URL: `/annotate/<image_id>`

#### Tool Bar

Tools are found on the left sidbar used for applying operations to the image.

##### Selection Tool

Edit or find assocated annotations by hovering or clicking segments in the viewer. `Click` any point to modify its location. `Shift-Click` any point to delete it from its assoicated segmentation.

##### Polygon/Lasso Tool

The polygonal lasso effortless tool for creating for drawing free-form or rigid segments.

Requires an annotation to be selected to which the polygon will be added too.

##### Saving/Downloading Tools

By default annotations are saved every minute to the database. Force save any new changes if all other async procoesses are complete. Status updates can be found in the top left of the navigation bar.

By default your annotations will be saved every minute. It is highly recommended to always save before leaving a session. 

##### Delete

Partially deletes all annotations and image from the database. Deletions can be restored on the Undo page.

#### Annotation Bar

Located on the left hand side of the image, the Annotaiton Bar allows for viewing and changing information about the categories, annotations and currently selected tool.

### Undo

List all partially deleted items for quick and simple restoring.

### API

Information about each endpoint can be found at `/api/`.

# Built With

Thanks to all these wonderful libaries/frameworks:
 - [Flask](http://flask.pocoo.org/) - Python web microframework
 - [Vue](https://vuejs.org/) - Frontend javascript framework
 - [RequireJS](https://requirejs.org/) - File module loader
 - [Axios](https://github.com/axios/axios) - Promise based HTTP client
 - [PaperJS](http://paperjs.org/) - Canvas editor library
 - [Bootstrap](https://getbootstrap.com/) - Frontend component library

# License
[MIT](https://tldrlegal.com/license/mit-license)
