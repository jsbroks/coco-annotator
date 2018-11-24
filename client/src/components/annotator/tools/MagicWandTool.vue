<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import MagicWand from "./magic-wand";

export default {
  name: "MagicWand",
  mixins: [tool],
  props: {
    raster: {
      type: Object,
      required: true
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
        blur: 5,
        simplify: 1
      }
    };
  },
  methods: {
    flood(x, y, thr, rad, simplify) {
      let image = {
        data: this.imageInfo.data.data,
        width: this.imageInfo.width,
        height: this.imageInfo.height,
        bytes: 4
      };
      let mask = MagicWand.floodFill(image, x, y, thr);
      rad = rad < 1 ? 1 : Math.abs(rad);
      mask = MagicWand.gaussBlurOnlyBorder(mask, rad);

      let contours = MagicWand.traceContours(mask).filter(x => !x.inner);
      contours = MagicWand.simplifyContours(contours, simplify, 3);

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
    onMouseDown(event) {
      let x = Math.round(this.imageInfo.width / 2 + event.point.x);
      let y = Math.round(this.imageInfo.height / 2 + event.point.y);

      if (
        x > this.imageInfo.width ||
        y > this.imageInfo.height ||
        x < 0 ||
        y < 0
      ) {
        return;
      }

      let path = this.flood(
        x,
        y,
        this.wand.threshold,
        this.wand.blur,
        this.wand.simplify
      );

      if (event.modifiers.shift) {
        this.$parent.subtractCurrentAnnotation(path);
      } else {
        this.$parent.uniteCurrentAnnotation(path);
      }

      if (path != null) path.remove();
    },

    onMouseDrag(event) {
      this.onMouseDown(event);
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation == -1;
    }
  },
  watch: {
    raster(raster) {
      if (Object.keys(raster).length === 0) return;

      this.imageInfo.width = raster.width;
      this.imageInfo.height = raster.height;

      // Create a copy of image data
      let tempCtx = document.createElement("canvas").getContext("2d");
      tempCtx.canvas.width = raster.width;
      tempCtx.canvas.height = raster.height;
      tempCtx.drawImage(raster.image, 0, 0);

      this.imageInfo.data = tempCtx.getImageData(
        0,
        0,
        raster.width,
        raster.height
      );
    }
  }
};
</script>
