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
    createBrush(center) {
      center = center || new paper.Point(0, 0);

      this.eraser.brush = new paper.Path.Circle({
        strokeColor: this.eraser.pathOptions.strokeColor,
        strokeWidth: this.eraser.pathOptions.strokeWidth,
        radius: this.eraser.pathOptions.radius,
        center: center
      });
    },
    onMouseMove(event) {
      this.moveBrush(event.point);
    },
    onMouseDrag(event) {
      this.moveBrush(event.point);
      this.erase();
    },
    onMouseDown(event) {
      this.erase();
    },
    erase() {
      let simplify = this.eraser.simplify < 1 ? 1 : this.eraser.simplify;
      this.$parent.subtractCurrentAnnotation(
        this.eraser.brush,
        simplify
      );
    }
  },
  watch: {
    "eraser.pathOptions.radius"() {
      let position = this.eraser.brush.position;
      this.eraser.brush.remove();
      this.createBrush(position);
    },
    "eraser.pathOptions.strokeColor"(newColor) {
      this.eraser.brush.strokeColor = newColor;
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
