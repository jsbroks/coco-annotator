<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import MagicWand from "./magic-wand";

export default {
  name: "MagicWand",
  mixins: [tool],
  props: {
    width: {
      type: null,
      required: true
    },
    height: {
      type: null,
      required: true
    },
    imageData: {
      required: true,
      validator: prop => typeof prop === "object" || prop === null
    }
  },
  data() {
    return {
      icon: "fa-magic",
      name: "Magic Wand",
      imageInfo: {},
      cursor: "crosshair",
      wand: {
        threshold: 30,
        blur: 40
      }
    };
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
        localStorage.setItem("editorTool", this.name);
      }
    }
  },
  methods: {
    /**
     * Exports settings
     * @returns {object} current settings
     */
    export() {
      return {
        threshold: this.wand.threshold,
        blur: this.wand.blur
      };
    },
    setPreferences(pref) {
      this.wand.threshold = pref.threshold || this.wand.threshold;
      this.wand.blur = pref.blur || this.wand.blur;
    },
    /**
     * Creates MagicWand selection
     * @param {number} x x position
     * @param {number} y y position
     * @param {number} thr threashold
     * @param {number} rad radius blur
     * @returns {paper.CompoundPath} create selection
     */
    flood(x, y, thr, rad) {
      if (this.imageData == null) return;

      let image = {
        data: this.imageData.data,
        width: this.width,
        height: this.height,
        bytes: 4
      };
      let mask = MagicWand.floodFill(image, x, y, thr);
      rad = rad < 1 ? 1 : Math.abs(rad);
      mask = MagicWand.gaussBlurOnlyBorder(mask, rad);

      let contours = MagicWand.traceContours(mask).filter(x => !x.inner);

      if (contours[0]) {
        let centerX = image.width / 2;
        let centerY = image.height / 2;

        let points = contours[0].points;
        points = points.map(pt => ({
          x: pt.x + 0.5 - centerX,
          y: pt.y + 0.5 - centerY
        }));

        let polygon = new paper.Path(points);
        polygon.closed = true;

        return polygon;
      }
      return null;
    },
    onMouseUp() {
      // this.$parent.currentAnnotation.simplifyPath();
    },
    onMouseDown(event) {
      let x = Math.round(this.width / 2 + event.point.x);
      let y = Math.round(this.height / 2 + event.point.y);

      // Check if valid coordinates
      if (x > this.width || y > this.height || x < 0 || y < 0) {
        return;
      }

      // Create shape and apply to current annotation
      let path = this.flood(x, y, this.wand.threshold, this.wand.blur);

      if (event.modifiers.shift) {
        this.$parent.currentAnnotation.subtract(path);
      } else {
        this.$parent.currentAnnotation.unite(path);
      }

      if (path != null) path.remove();
    },
    onMouseDrag(event) {
      this.onMouseDown(event);
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation === -1;
    }
  }
};
</script>
