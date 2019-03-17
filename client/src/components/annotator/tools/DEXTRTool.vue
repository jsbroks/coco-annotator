<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import axios from "axios";

export default {
  name: "DEXTRTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-crosshairs",
      name: "DEXTR",
      cursor: "crosshair",
      settings: {
        padding: 50,
        threshold: 80
      },
      points: []
    };
  },
  methods: {
    createPoint(point) {
      let paperPoint = new paper.Path.Circle(point, 5);
      paperPoint.fillColor = this.$parent.currentAnnotation.color;
      paperPoint.data.point = point;
      this.points.push(paperPoint);
    },
    onMouseDown(event) {
      this.createPoint(event.point);
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation == -1;
    }
  },
  watch: {
    points(newPoints) {
      if (newPoints.length == 4) {
        let points = this.points;
        this.points = [];

        let currentAnnotation = this.$parent.currentAnnotation;
        let pointsList = [];
        let width = this.$parent.image.raster.width / 2;
        let height = this.$parent.image.raster.height / 2;

        points.forEach(point => {
          let pt = point.position;

          pointsList.push([
            Math.round(width + pt.x),
            Math.round(height + pt.y)
          ]);
        });

        axios
          .post(`/api/model/dextr/${this.$parent.image.id}`, {
            points: pointsList,
            ...this.settings
          })
          .then(response => {
            let segments = response.data.segmentaiton;
            let center = new paper.Point(width, height);

            let compoundPath = new paper.CompoundPath();
            for (let i = 0; i < segments.length; i++) {
              let polygon = segments[i];
              let path = new paper.Path();

              for (let j = 0; j < polygon.length; j += 2) {
                let point = new paper.Point(polygon[j], polygon[j + 1]);
                path.add(point.subtract(center));
              }
              path.closePath();
              compoundPath.addChild(path);
            }

            currentAnnotation.unite(compoundPath);
          })
          .finally(() => points.forEach(point => point.remove()));
      }
    }
  }
};
</script>
