<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";

export default {
  name: "EraserTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-paint-brush",
      name: "Brush",
      cursor: "none",
      scaleFactor: 3,
      brush: {
        path: null,
        simplify: 5,
        pathOptions: {
          strokeColor: "white",
          strokeWidth: 1,
          radius: 30
        }
      }
    };
  },
  methods: {
    moveBrush(point) {
      if (this.brush.path == null) this.createBrush();

      this.brush.path.bringToFront();
      this.brush.path.position = point;
    },
    createBrush(center) {
      center = center || new paper.Point(0, 0);

      this.brush.path = new paper.Path.Circle({
        strokeColor: this.brush.pathOptions.strokeColor,
        strokeWidth: this.brush.pathOptions.strokeWidth,
        radius: this.brush.pathOptions.radius,
        center: center
      });
    },
    onMouseMove(event) {
      this.moveBrush(event.point);
    },
    onMouseDown(event) {
      this.draw();
    },
    onMouseDrag(event) {
      this.moveBrush(event.point);
      this.draw();
    },
    draw() {
      let simplify = this.brush.simplify < 1 ? 1 : this.brush.simplify;
      this.$parent.uniteCurrentAnnotation(this.brush.path, simplify);
    }
  },
  watch: {
    "brush.pathOptions.radius"() {
      let position = this.brush.path.position;
      this.brush.path.remove();
      this.createBrush(position);
    },
    "brush.pathOptions.strokeColor"(newColor) {
      this.brush.path.strokeColor = newColor;
    },
    isActive(active) {
      if (this.brush.path != null) {
        this.brush.path.visible = active;
      }

      if (active) {
        this.tool.activate();
      }
    },
    /**
     * Change width of stroke based on zoom of image
     */
    scale(newScale) {
      this.brush.pathOptions.strokeWidth = newScale * this.scaleFactor;
      if (this.brush.path != null)
        this.brush.path.strokeWidth = newScale * this.scaleFactor;
    }
  },
  mounted() {}
};
</script>
