<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import UndoAction from "@/undo";

import { invertColor } from "@/libs/colors";
import { mapMutations } from "vuex";

export default {
  name: "PolygonTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    },
    settings: {
      type: [Object, null],
      default: null
    }
  },
  data() {
    return {
      icon: "fa-pencil",
      name: "Polygon",
      scaleFactor: 3,
      cursor: "copy",
      polygon: {
        completeDistance: 5,
        minDistance: 2,
        path: null,
        guidance: true,
        simplify: 1,
        pathOptions: {
          strokeColor: "black",
          strokeWidth: 1
        }
      },
      color: {
        blackOrWhite: true,
        auto: true,
        radius: 10,
        circle: null
      },
      actionTypes: Object.freeze({
        ADD_POINTS: "Added Points",
        CLOSED_POLYGON: "Closed Polygon",
        DELETE_POLYGON: "Delete Polygon"
      }),
      actionPoints: 0
    };
  },
  methods: {
    ...mapMutations(["addUndo", "removeUndos"]),
    export() {
      return {
        guidance: this.polygon.guidance,
        completeDistance: this.polygon.completeDistance,
        minDistance: this.polygon.minDistance,
        blackOrWhite: this.color.blackOrWhite,
        auto: this.color.auto,
        radius: this.color.radius
      };
    },
    setPreferences(pref) {
      this.polygon.guidance = pref.guidance || this.polygon.guidance;
      this.polygon.completeDistance =
        pref.completeDistance || this.polygon.completeDistance;
      this.polygon.minDistance = pref.minDistance || this.polygon.minDistance;
      this.color.blackOrWhite = pref.blackOrWhite || this.color.blackOrWhite;
      this.color.auto = pref.auto || this.color.auto;
      this.color.radius = pref.radius || this.color.radius;
    },
    /**
     * Creates a new selection polygon path
     */
    createPolygon() {
      if (this.color.auto) {
        this.color.circle = new paper.Path.Circle(
          new paper.Point(0, 0),
          this.color.radius
        );
      }
      this.polygon.path = new paper.Path(this.polygon.pathOptions);
    },
    /**
     * Frees current polygon
     */
    deletePolygon() {
      if (this.polygon.path == null) return;

      this.polygon.path.remove();
      this.polygon.path = null;

      if (this.color.circle == null) return;
      this.color.circle.remove();
      this.color.circle = null;
    },
    autoStrokeColor(point) {
      if (this.color.circle == null) return;
      if (this.polygon.path == null) return;
      if (!this.color.auto) return;

      this.color.circle.position = point;
      let raster = this.$parent.image.raster;
      let color = raster.getAverageColor(this.color.circle);
      if (color) {
        this.polygon.pathOptions.strokeColor = invertColor(
          color.toCSS(true),
          this.color.blackOrWhite
        );
      }
    },
    onMouseDrag(event) {
      if (this.polygon.path == null) return;
      this.actionPoints++;
      this.autoStrokeColor(event.point);
      this.polygon.path.add(event.point);
      this.autoComplete(30);
    },
    onMouseDown(event) {
      let wasNull = false;
      if (this.polygon.path == null) {
        wasNull = true;
        this.createPolygon();
      }

      this.actionPoints = 1;
      this.polygon.path.add(event.point);

      if (this.autoComplete(3)) return;

      if (this.polygon.guidance && wasNull) this.polygon.path.add(event.point);
    },
    onMouseUp() {
      if (this.polygon.path == null) return;
      let action = new UndoAction({
        name: this.name,
        action: this.actionTypes.ADD_POINTS,
        func: this.undoPoints,
        args: {
          points: this.actionPoints
        }
      });

      this.addUndo(action);
    },
    onMouseMove(event) {
      if (this.polygon.path == null) return;
      if (this.polygon.path.segments.length === 0) return;
      this.autoStrokeColor(event.point);

      if (!this.polygon.guidance) return;
      this.removeLastPoint();
      this.polygon.path.add(event.point);
    },
    /**
     * Undo points
     */
    undoPoints(args) {
      if (this.polygon.path == null) return;

      let points = args.points;
      let length = this.polygon.path.segments.length;

      if (this.polygon.guidance) {
        length -= 1;
      }

      this.polygon.path.removeSegments(length - points, length);
    },
    /**
     * Completes polygon if point being added is close to first point
     * @returns {boolean} sucessfully closes object
     */
    autoComplete(minCompleteLength) {
      if (this.polygon.path == null) return false;
      if (this.polygon.path.segments.length < minCompleteLength) return false;

      let last = this.polygon.path.lastSegment.point;
      let first = this.polygon.path.firstSegment.point;

      let completeDistance = this.polygon.completeDistance;
      if (last.isClose(first, completeDistance)) {
        return this.complete();
      }

      return false;
    },
    /**
     * Closes current polygon and unites it with current annotaiton.
     * @returns {boolean} sucessfully closes object
     */
    complete() {
      if (this.polygon.path == null) return false;

      this.removeLastPoint();

      this.polygon.path.fillColor = "black";
      this.polygon.path.closePath();

      this.$parent.uniteCurrentAnnotation(this.polygon.path);

      this.polygon.path.remove();
      this.polygon.path = null;
      if (this.color.circle) {
        this.color.circle.remove();
        this.color.circle = null;
      }

      this.removeUndos(this.actionTypes.ADD_POINTS);
      return true;
    },
    removeLastPoint() {
      this.polygon.path.removeSegment(this.polygon.path.segments.length - 1);
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation === -1;
    }
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
        localStorage.setItem("editorTool", this.name);
      }
    },
    /**
     * Change width of stroke based on zoom of image
     */
    scale(newScale) {
      this.polygon.pathOptions.strokeWidth = newScale * this.scaleFactor;
      if (this.polygon.path != null)
        this.polygon.path.strokeWidth = newScale * this.scaleFactor;
    },
    /**
     * Remove last point (point were mouse was) if enable guidane
     */
    "polygon.guidance"(guidance) {
      if (this.polygon.path == null) return;

      if (!guidance && this.polygon.path.length > 1) {
        this.removeLastPoint();
      }
    },
    "polygon.minDistance"(newDistance) {
      this.tool.minDistance = newDistance;
    },
    "polygon.pathOptions.strokeColor"(newColor) {
      if (this.polygon.path == null) return;

      this.polygon.path.strokeColor = newColor;
    },
    "color.auto"(value) {
      if (value && this.polygon.path) {
        this.color.circle = new paper.Path.Circle(
          new paper.Point(0, 0),
          this.color.radius
        );
      }
      if (!value && this.color.circle) {
        this.color.circle.remove();
        this.color.circle = null;
      }
    }
  },
  created() {},
  mounted() {
    this.tool.minDistance = this.minDistance;
  }
};
</script>
