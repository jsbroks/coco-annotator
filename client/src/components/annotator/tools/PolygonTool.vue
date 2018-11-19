<script>
import paper from "paper";
import simplify from "simplify-js";
import tool from "@/mixins/tool";

export default {
  name: "PolygonTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-pencil",
      name: "Polygon",
      scaleFactor: 3,
      polygon: {
        toggleGuidance: null,
        deleteCurrent: null,
        completeDistance: 5,
        minDistance: 2,
        path: null,
        guidance: true,
        simplify: 1,
        pathOptions: {
          strokeColor: "black",
          strokeWidth: 1
        }
      }
    };
  },
  methods: {
    /**
     * Creates a new selection polygon path
     */
    createPolygon() {
      this.polygon.path = new paper.Path(this.polygon.pathOptions);
    },
    /**
     * Frees current polygon
     */
    deletePolygon() {
      if (this.polygon.path == null) return;

      this.polygon.path.remove();
      this.polygon.path = null;
    },
    onMouseDrag(event) {
      if (this.polygon.path == null) return;

      this.polygon.path.add(event.point);
      this.autoComplete(30);
    },
    onMouseDown(event) {
      let wasNull = false;
      if (this.polygon.path == null) {
        wasNull = true;
        this.createPolygon();
      }

      this.polygon.path.add(event.point);
      if (this.autoComplete(3)) return;
      if (this.polygon.guidance && wasNull) this.polygon.path.add(event.point);
    },
    onMouseMove(event) {
      if (this.polygon.path == null) return;
      if (!this.polygon.guidance) return;
      if (this.polygon.path.segments.length === 0) return;

      this.polygon.path.removeSegment(this.polygon.path.segments.length - 1);
      this.polygon.path.add(event.point);
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

      if (this.polygon.simplify > 0) {
        let points = [];

        this.polygon.path.segments.forEach(seg => {
          points.push({ x: seg.point.x, y: seg.point.y });
        });

        let previous = points.length;
        points = simplify(points, this.polygon.simplify, true);
        this.$toastr.success(
          "Polygon Tool",
          "Reduced by " + (previous - points.length) + " points."
        );
        this.polygon.path.remove();
        this.polygon.path = new paper.Path(points);
      }
      this.polygon.path.fillColor = "black";
      this.polygon.path.closePath();

      this.$parent.uniteCurrentAnnotation(this.polygon.path);

      this.polygon.path.remove();
      this.polygon.path = null;
      return true;
    }
  },
  watch: {
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

      if (guidance && this.polygon.path.length > 1) {
        this.polygon.path.removeSegment(this.polygon.path.segments.length - 1);
      }
    }
  }
};
</script>
