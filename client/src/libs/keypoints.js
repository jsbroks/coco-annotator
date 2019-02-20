import paper from "paper";

export class Keypoints extends paper.Group {
  constructor(labels, edges, keypoints, args) {
    super();
    args = args || {};

    this.labels = new Set(labels);
    this._edges = {};

    this._lines = {};
    this._labelled = {};
    this._keypoints = [];

    this.strokeColor = args.strokeColor || "red";
    this.lineWidth = args.strokeWidth || 4;

    edges.forEach(e => this.addEdge(e));

    if (keypoints) {
      for (let i = 0; i < keypoints.length; i += 3) {
        let x = keypoints[i],
          y = keypoints[i + 1],
          v = keypoints[i + 2];
        let point = new Keypoint(x, y, { visibility: v, indexLabel: i });
        this.addKeypoint(point);
      }
    }
  }

  addKeypoint(keypoint) {
    keypoint.keypoints = this;
    keypoint.path.keypoints = this;
    keypoint.color = this.strokeColor;
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
    this._keypoints.forEach(k => (k.color = val));
  }

  get color() {
    return this._color;
  }

  set lineWidth(val) {
    this._lineWidth = val;
    this.strokeWidth = val;
    this._keypoints.forEach(k => (k.path.storkeWidth = val));
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

  exportJSON() {
    let array = [];
    this._keypoints.forEach(k => {
      array.push(...[k.x, k.y, k.visibility]);
    });
    return array;
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
    line.strokeWidth = this.strokeWidth;
    if (firstKeypoint.path.isBelow(secondKeypoint.path)) {
      line.insertBelow(firstKeypoint.path);
    } else {
      line.insertBelow(secondKeypoint.path);
    }

    this._lines[h] = line;
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
  LABELED_VISIBLE: 2
};

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
    this._draw();
    this.color = args.color || "red";
    this.setFillColor();
  }

  setFillColor() {
    if (this.path == null) return;

    switch (this.visibility) {
      case VisibilityType.NOT_LABELED:
        this.path.fillColor = "black";
        break;
      case VisibilityType.LABELED_NOT_VISIBLE:
        this.path.fillColor = "white";
        break;
      default:
        this.path.fillColor = this.color;
    }
  }

  move(point) {
    this.x = point.x;
    this.y = point.y;
    this._draw();
  }

  _draw() {
    let storkeWidth = 1;
    if (this.path !== null) {
      storkeWidth = this.path.strokeWidth;
      this.path.remove();
    }

    this.path = new paper.Path.Circle(this, this.radius);
    this.path.onMouseDrag = event => {
      if (this.keypoints) {
        this.keypoints.moveKeypoint(event.point, this);
      } else {
        this.move(event.point);
      }
    };
    this.path.strokeColor = this.color;
    this.path.strokeWidth = storkeWidth;
    this.path.visible = this.visible;
    this.path.keypoint = this;

    this.setFillColor();
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
    this.setFillColor();
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

  set color(val) {
    this._color = val;
    this.path.strokeColor = val;
    this.setFillColor();
  }

  get color() {
    return this._color;
  }

  set strokeColor(val) {
    this.color = val;
  }

  get strokeColor() {
    return this.color;
  }
}
