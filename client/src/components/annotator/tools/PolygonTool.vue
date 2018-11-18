<script>
import paper from "paper";
import tool from "@/mixins/tool";

export default {
  name: "PolygonTool",
  mixins: [tool],
  data() {
    return {
      icon: "fa-pencil",
      name: "Polygon",
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
    createPolygon() {
      this.polygon.path = new paper.Path(this.polygon.pathOptions);
    },
    deletePolygon() {
      if (this.polygon.path == null) return;

      this.polygon.path.remove();
      this.polygon.path = null;
    },
    onMouseDown(event) {
      //let compound = vue.compoundPath;
      if (this.polygon.path == null) {
        this.createPolygon();
      }

      this.polygon.path.add(event.point);
      //            if (this.autoComplete(polygon, 3, compound, vue.setCompoundPath)) return;
      if (this.polygon.guidance) this.polygon.path.add(event.point);
    },
    onMouseMove(event) {
      if (this.polygon.path == null) return;
      if (!this.polygon.guidance) return;
      if (this.polygon.path.segments.length === 0) return;

      this.polygon.path.removeSegment(this.polygon.path.segments.length - 1);
      this.polygon.path.add(event.point);
    }
  }
};
</script>
