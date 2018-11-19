<script>
import paper from "paper";
import tool from "@/mixins/tool";

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
      icon: "fa-eraser",
      name: "Eraser",
      cursor: "none",
      scaleFactor: 3,
      eraser: {
        brush: null,
        minimumArea: 10,
        simplify: 20,
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
      if (this.eraser.brush == null) this.createBrush();

      this.eraser.brush.bringToFront();
      this.eraser.brush.position = point;
    },
    createBrush() {
      this.eraser.brush = new paper.Path.Circle({
        strokeColor: this.eraser.pathOptions.strokeColor,
        strokeWidth: this.eraser.pathOptions.strokeWidth,
        radius: this.eraser.pathOptions.radius
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
      this.$parent.subtractCurrentAnnotation(this.eraser.brush, this.eraser.simplify);
    }
  },
  watch: {
    "eraser.pathOptions.radius"() {
      this.eraser.brush.remove();
      this.createBrush();
    },
    isActive(active) {
      if (this.eraser.brush != null) {
        this.eraser.brush.visible = active;
      }

      if (active) {
        this.tool.activate();
      }
    },
    /**
     * Change width of stroke based on zoom of image
     */
    scale(newScale) {
      this.eraser.pathOptions.strokeWidth = newScale * this.scaleFactor;
      if (this.eraser.brush != null)
        this.eraser.brush.strokeWidth = newScale * this.scaleFactor;
    }
  },
  mounted() {}
};
</script>
