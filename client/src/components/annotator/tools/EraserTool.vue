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
        pathOptions: {
          strokeColor: "white",
          strokeWidth: 1,
          radius: 30
        }
      },
      selection: null
    };
  },
  methods: {
    removeBrush() {
      if (this.eraser.brush != null) {
        this.eraser.brush.remove();
        this.eraser.brush = null;
      }
    },
    removeSelection() {
      if (this.selection != null) {
        this.selection.remove();
        this.selection = null;
      }
    },
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
    createSelection() {
      this.selection = new paper.Path({
        strokeColor: this.eraser.pathOptions.strokeColor,
        strokeWidth: this.eraser.pathOptions.strokeWidth
      });
    },
    onMouseMove(event) {
      this.moveBrush(event.point);
    },
    onMouseDrag(event) {
      this.moveBrush(event.point);
      this.erase();
    },
    onMouseDown() {
      this.createSelection();
      this.erase();
    },
    onMouseUp() {
      this.$parent.currentAnnotation.createUndoAction("Subtract");
      this.$parent.currentAnnotation.subtract(this.selection, true, false);
      this.removeSelection();
    },
    erase() {
      // Undo action, will be handled on mouse up
      let newSelection = this.selection.unite(this.eraser.brush);

      this.selection.remove();
      this.selection = newSelection;
    },
    decreaseRadius() {
      if (!this.isActive) return;
      this.eraser.pathOptions.radius -= 2;
    },
    increaseRadius() {
      if (!this.isActive) return;
      this.eraser.pathOptions.radius += 2;
    },
    export() {
      return {
        strokeColor: this.eraser.pathOptions.strokeColor,
        radius: this.eraser.pathOptions.radius
      };
    },
    setPreferences(pref) {
      this.eraser.pathOptions.strokeColor =
        pref.strokeColor || this.eraser.pathOptions.strokeColor;
      this.eraser.pathOptions.radius =
        pref.radius || this.eraser.pathOptions.radius;
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation == -1;
    }
  },
  watch: {
    "eraser.pathOptions.radius"() {
      if (this.eraser.brush == null) return;
      let position = this.eraser.brush.position;
      this.eraser.brush.remove();
      this.createBrush(position);
    },
    "eraser.pathOptions.strokeColor"(newColor) {
      if (this.eraser.brush == null) return;
      this.eraser.brush.strokeColor = newColor;
    },
    isActive(active) {
      if (this.eraser.brush != null) {
        this.eraser.brush.visible = active;
      }
      if (active) {
        this.tool.activate();
        localStorage.setItem("editorTool", this.name);
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