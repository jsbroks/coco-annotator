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
        minimumArea: 10,
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
    createBrush() {
      this.brush.path = new paper.Path.Circle({
        strokeColor: this.brush.pathOptions.strokeColor,
        strokeWidth: this.brush.pathOptions.strokeWidth,
        radius: this.brush.pathOptions.radius
      });
    },
    onMouseMove(event) {
      this.moveBrush(event.point);
    },
    onMouseDrag(event) {
      this.moveBrush(event.point);
      this.erase();
    },
    erase() {
      this.$parent.uniteCurrentAnnotation(this.brush.path, this.brush.simplify);
    }
  },
  watch: {
    "brush.pathOptions.radius"() {
      this.eraser.brush.remove();
      this.createBrush();
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
