import paper from "paper";

export default class extends paper.Point {
  static NOT_LABELED = 0;
  static LABELED_NOT_VISIBLE = 1;
  static LABELED_VISIBLE = 2;

  constructor(x, y, args) {
    super(x, y);

    this.path = null;

    this.radius = args.radius || 5;
    this.label = args.label || "";
    this.indexLabel = args.indexLabel || -1;
    this.edges = args.edges || [];
    this.visibility = args.visibility || this.NOT_LABELED;

    this._draw();
    this.color = "white";
  }

  fillColor() {
    if (this.path == null) return;

    switch (this.visibility) {
      case this.NOT_LABELED:
        this.path.fillColor = "black";
        break;
      case this.LABELED_NOT_VISIBLE:
        this.path.fillColor = "white";
        break;
      default:
        this.path.fillColor = this.color;
    }
  }

  addLine(line) {
    this.edges.push(line);
    line.strokeWidth = 2;
    line.strokeColor = this.color;
  }

  _draw() {
    if (this.path !== null) {
      this.path.remove();
    }

    this.path = new paper.Path.Circle(this, this.radius);
    this.path.strokeColor = this.color;
    this.path.strokeWidth = 3;
    this.path.keypoint = this;

    this.fillColor();
  }

  set visible(val) {
    this.path.visible = val;
    this.edges.forEach(e => (e.visible = val));
  }

  get visible() {
    return this.path.visible;
  }

  set visibility(val) {
    this._visibility = val;
    this.fillColor();
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
    this.strokeColor = val;
    this.fillColor = val;
    this.edges.forEach(e => (e.strokeColor = val));
  }

  get color() {
    return this.path.fillColor;
  }

  set strokeColor(val) {
    this.path.strokeColor = val;
  }

  get strokeColor() {
    return this.path.strokeColor;
  }
}
