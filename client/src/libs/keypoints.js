import paper from "paper";

export class Keypoints extends paper.Group {
  constructor(edges, labels, colors, args) {
    super();
    args = args || {};

    this._edges = {};

    this._lines = {};
    this._labelled = {};
    this._keypoints = [];
    this.labels = labels;
    this.colors = {};
    for (let i=0; i < colors.length; ++i) {
      this.colors[String(i+1)] = colors[i];
    }

    this.annotationId = args.annotationId;
    this.categoryName = args.categoryName;
    this.strokeColor = args.strokeColor || "red";
    this.lineWidth = args.strokeWidth || 4;

    edges = edges || [];
    edges.forEach(e => this.addEdge(e));
  }

  isEmpty() {
    return this._keypoints.length === 0;
  }

  // setKeypointIndex(keypoint, newIndex) {
  //   let oldIndex = keypoint.indexLabel;
  //   if (newIndex == oldIndex) return;

  //   keypoint.indexLabel = parseInt(newIndex);

  //   if (oldIndex >= 0) {
  //     delete this._labelled[oldIndex];

  //     let otherIndices = this._edges[oldIndex];
  //     if (otherIndices) {
  //       otherIndices.forEach(i => this.removeLine([i, oldIndex]));
  //     }
  //     // TODO: Remove assoicated lines
  //   }
  //   if (newIndex >= 0) {
  //     this._labelled[newIndex] = keypoint;
  //     this._drawLines(keypoint);
  //   }
  // }

  bringToFront() {
    super.bringToFront();
    Object.values(this._lines).forEach(l => l.bringToFront());
    this._keypoints.forEach(k => k.path.bringToFront());
  }

  addKeypoint(keypoint) {
    keypoint.keypoints = this;
    keypoint.path.keypoints = this;
    // keypoint.color = this.strokeColor;
    keypoint.strokeColor =  this.strokeColor;
    keypoint.path.strokeWidth = this.strokeWidth;

    let indexLabel = keypoint.indexLabel;
    if (this._labelled.hasOwnProperty(indexLabel)) {
      keypoint.indexLabel = -1;
    } else {
      this._labelled[indexLabel] = keypoint;
    }

    this._keypoints.push(keypoint);
    this.addChild(keypoint.path);
    this._drawLines(keypoint);
    keypoint.path.bringToFront();
  }

  deleteKeypoint(keypoint) {
    let indexLabel = keypoint.indexLabel;
    if (this._labelled.hasOwnProperty(indexLabel)) {
      delete this._labelled[indexLabel];
    }
    if (this._edges.hasOwnProperty(indexLabel)) {
      this._edges[indexLabel].forEach(e => this.removeLine([e, indexLabel]));
    }
    let index = this._keypoints.findIndex(k => k == keypoint);
    if (index > -1) this._keypoints.splice(index, 1);
    keypoint.path.remove();
  }

  moveKeypoint(point, keypoint) {
    let indexLabel = keypoint.indexLabel;
    let edges = this._edges[indexLabel];

    if (edges) {
      edges.forEach(i => {
        let line = this.getLine([i, indexLabel]);
        if (line) {
          // We need to move the line aswell
          for (let i = 0; i < line.segments.length; i++) {
            let segment = line.segments[i];
            if (segment.point.isClose(keypoint, 0)) {
              segment.point = point;
              break;
            }
          }
        }
      });
    }
    keypoint.move(point);
    keypoint.path.bringToFront();
  }

  set visible(val) {
    this._visible = val;
    this._keypoints.forEach(k => (k.visible = val));
    Object.values(this._lines).forEach(l => (l.visible = val));
  }

  get visible() {
    return this._visible;
  }

  set color(val) {
    this._color = val;
    this.strokeColor = val;
    this._keypoints.forEach(k => {
      k.fillColor = this.colors[k.indexLabel];
      k.strokeColor = val;
    });
    Object.values(this._lines).forEach(l => (l.strokeColor = val));
  }

  get color() {
    return this._color;
  }

  set lineWidth(val) {
    this._lineWidth = val;
    this.strokeWidth = val;
    this._keypoints.forEach(k => (k.path.storkeWidth = val));
    Object.values(this._lines).forEach(l => (l.strokeWidth = val));
  }

  get lineWidth() {
    return this._lineWidth;
  }

  set radius(val) {
    this._radius = val;
    this._keypoints.forEach(k => (k.radius = val));
  }

  get radius() {
    return this._radius;
  }

  exportJSON(labels, width, height) {
    let array = [];
    for (let i = 0; i < labels.length; i++) {
      let j = i * 3;
      array[j] = 0;
      array[j + 1] = 0;
      array[j + 2] = 0;
    }

    this._keypoints.forEach(k => {
      let center = new paper.Point(width / 2, height / 2);
      let point = k.clone().add(center);
      let index = k.indexLabel;

      if (index == -1) {
        array.push(...[Math.round(point.x), Math.round(point.y), k.visibility]);
      } else {
        index = (index - 1) * 3;
        array[index] = Math.round(point.x);
        array[index + 1] = Math.round(point.y);
        array[index + 2] = Math.round(k.visibility);
      }
    });

    return array;
  }

  contains(point) {
    return this._keypoints.findIndex(k => k.path.contains(point)) > -1;
  }

  edges() {
    let edges = [];
    let keys = Object.keys(this._edges);

    for (let i = 0; i < keys.length; i++) {
      let i1 = parseInt(keys[i]);
      let otherIndices = Array.from(this._edges[i1]);

      for (let j = 0; j < otherIndices.length; j++) {
        let i2 = parseInt(otherIndices[j]);

        if (i2 < i1) continue;
        edges.push([i1, i2]);
      }
    }

    return edges;
  }

  addEdge(edge) {
    if (edge.length !== 2) return;

    let i1 = edge[0];
    let i2 = edge[1];

    // If labels convert to indexs
    if (typeof i1 == "string") i1 = this.getLabelIndex(i1);
    if (typeof i2 == "string") i2 = this.getLabelIndex(i2);
    if (i1 < 0 || i2 < 0) return;

    this._addEdgeIndex(i1, i2);
    this._addEdgeIndex(i2, i1);

    // Draw line if points exist
    let k1 = this._labelled[i1];
    let k2 = this._labelled[i2];
    if (k1 && k2) {
      this._drawLine(edge, k1, k2);
    }
  }

  getLabelIndex(label) {
    return this.labels.find(l => l == label);
  }

  _addEdgeIndex(index1, index2) {
    if (this._edges.hasOwnProperty(index1)) {
      if (!this._edges[index1].has(index2)) this._edges[index1].add(index2);
    } else {
      this._edges[index1] = new Set([index2]);
    }
  }

  /**
   * Draws lines to other keypoints if they exist
   */
  _drawLines(keypoint) {
    if (keypoint.indexLabel < 0) return;
    if (!this._edges.hasOwnProperty(keypoint.indexLabel)) return;

    let otherIndices = this._edges[keypoint.indexLabel];
    otherIndices.forEach(i => {
      let k2 = this._labelled[i];
      if (!k2) return;

      let edge = [keypoint.indexLabel, i];
      this._drawLine(edge, keypoint, k2);
    });
  }

  /**
   * Draws a line between two keypoints and hashes to a table for quick look up
   * @param {list} edge array of two elementings contain the index edges
   * @param {Keypoint} firstKeypoint first keypoint object
   * @param {Keypoint} secondKeypoint second keypoint object
   */
  _drawLine(edge, firstKeypoint, secondKeypoint) {
    let h = this._hashEdge(edge);
    if (this._lines[h]) return;

    let line = new paper.Path.Line(firstKeypoint, secondKeypoint);
    line.strokeColor = this.strokeColor;
    line.strokeWidth = this.lineWidth;
    line.indicator = true;

    line.insertAbove(secondKeypoint.path);

    this._lines[h] = line;
  }

  removeLine(edge) {
    let h = this._hashEdge(edge);
    let line = this._lines[h];
    if (line) {
      line.remove();
      delete this._lines[h];
    }
  }

  /**
   * Returns paperjs path of line [O(1) lookup time]
   * @param {list} edge array of two elementing contains the index edges
   * @returns paperjs object path of the line or undefind if not found
   */
  getLine(edge) {
    let h = this._hashEdge(edge);
    return this._lines[h];
  }

  /**
   * Uses cantor pairing function to has two numbers
   * @param {list} edge array of two elementing contains the index edges
   */
  _hashEdge(edge) {
    // Order doesn't matter so can sort first
    let min = Math.min(edge[0], edge[1]);
    let max = Math.max(edge[0], edge[1]);
    // Cantor pairing function
    let add = min + max;
    return (1 / 2) * add * (add - 1) - max;
  }
}

/**
 * Keypoint visibility types as defined by the COCO format
 */
export let VisibilityType = {
  NOT_LABELED: 0,
  LABELED_NOT_VISIBLE: 1,
  LABELED_VISIBLE: 2,
  UNKNOWN: 3
};

export let VisibilityOptions = (function() {
  let options = {};
  for (let l in VisibilityType) {
    if (l !== "UNKNOWN") {
      options[VisibilityType[l]] = l.replace("_", " ");
    }
  }
  return options;
}());


export class Keypoint extends paper.Point {
  constructor(x, y, args) {
    super(x, y);
    args = args || {};

    this.path = null;

    this.label = args.label || "";
    this.radius = args.radius || 5;
    this.indexLabel = args.indexLabel || -1;
    this.visibility = args.visibility || VisibilityType.NOT_LABELED;
    this.visible = args.visible || true;

    this.onClick = args.onClick;
    this.onDoubleClick = args.onDoubleClick;
    this.onMouseDrag = args.onMouseDrag;

    this._draw();
    this.fillColor = args.fillColor || "red";
    this.strokeColor = args.strokeColor || "red";
    this.updateFillColor();
  }

  move(point) {
    this.x = point.x;
    this.y = point.y;
    this._draw();
  }

  _draw() {
    let strokeColor = this.strokeColor;
    if (this.path !== null) {
      strokeColor = this.path.strokeColor;
      this.path.remove();
    }

    this.path = new paper.Path.Circle(this, this.radius);

    this.path.onMouseDown = this.onMouseDown;
    this.path.onMouseUp = this.onMouseUp;
    this.path.onMouseDrag = this.onMouseDrag;
    this.path.onDoubleClick = this.onDoubleClick;
    this.path.onClick = this.onClick;

    this.path.indicator = true;
    this.path.strokeColor = strokeColor;
    this.path.strokeWidth = this.radius * 0.4;
    this.path.visible = this.visible;
    this.path.keypoint = this;
    this.path.keypoints = this.keypoints;

    this.updateFillColor();
  }

  getVisibilityDescription() {
    return VisibilityOptions[this.visibility];
  }

  set visible(val) {
    this._visible = val;
    this.path.visible = val;
  }

  get visible() {
    return this._visible;
  }

  set visibility(val) {
    this._visibility = val;
    this.updateFillColor();
  }

  get visibility() {
    return this._visibility;
  }

  set radius(val) {
    this._radius = val;
    this._draw();
  }

  get radius() {
    return this._radius;
  }

  set strokeColor(val) {
    this._strokeColor = val;
    this.path.strokeColor = this.selected ? "white" : val;
    this.updateFillColor();
  }

  get strokeColor() {
    return this._strokeColor;
  }

  set fillColor(val) {
    this._fillColor = val;
    this.updateFillColor();
  }

  get fillColor() {
    return this._fillColor;
  }

  set strokeColor(val) {
    this._strokeColor = val;
    this.path.strokeColor = this.selected ? "white" : val;
    this.updateFillColor();
  }

  get strokeColor() {
    return this._strokeColor;
  }

  updateFillColor() {
    if (this.path == null) return;

    switch (this.visibility) {
      case VisibilityType.NOT_LABELED:
        this.path.fillColor = "black";
        break;
      case VisibilityType.LABELED_NOT_VISIBLE:
        this.path.fillColor = "white";
        break;
      default:
        this.path.fillColor = this.fillColor;
    }
  }

  set selected(val) {
    this._selected = val;
    this.path.strokeColor = val ? "white" : this.strokeColor;
    this.path.bringToFront();
  }

  get selected() {
    return this._selected;
  }
}
