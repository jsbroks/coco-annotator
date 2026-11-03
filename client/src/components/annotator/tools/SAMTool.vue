<script>
import paper from "paper";
import axios from "axios";
import tool from "@/mixins/toolBar/tool";
import { minAreaRect } from "@/libs/minAreaRect";

/**
 * Segment Anything (SAM) assisted segmentation.
 *
 *  - click            add a point on the object
 *  - Shift + click    add a point on the background (exclude it)
 *  - drag             draw a box around the object
 *  - Enter / Apply    add the preview to the current annotation
 *
 * "Rotated box" output (on by default in an OBB dataset): the smallest
 * rotated box around the mask is added instead of the outline, as a new
 * annotation when the selected one already has a shape.
 *
 * The server caches the image embedding, so every click after the first
 * only runs SAM's light-weight mask decoder.
 */
const DRAG_THRESHOLD = 4; // screen pixels

export default {
  name: "SAMTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-bullseye",
      name: "SAM",
      cursor: "crosshair",
      status: {
        checked: false,
        available: false,
        preparing: false,
        predicting: false,
        message: ""
      },
      points: [], // { point: paper.Point, label: 0|1 }
      box: null, // [paper.Point, paper.Point]
      score: null,
      preview: null,
      markers: null,
      dragStart: null,
      boxPath: null,
      requestId: 0,
      // the rotated box around the preview (paper points), in box mode
      previewCorners: null,
      previewBox: null,
      lastSegmentation: null,
      settings: {
        replace: false,
        // null: from the dataset's task (see output)
        output: null,
        obbPad: 0
      }
    };
  },
  computed: {
    isDisabled() {
      return !this.status.available || this.$parent.current.annotation === -1;
    },
    tooltip() {
      if (this.status.checked && !this.status.available) {
        return this.$t("sam.unavailableTooltip");
      }
      if (this.isDisabled) return this.$t("toolbar.needsAnnotation", { tool: "SAM" });
      return `${this.$t("sam.tooltip")} · ${this.$t("sam.outputs", { what: this.outputText })}`;
    },
    hasPrompt() {
      return this.points.length > 0 || this.box != null;
    },
    statusText() {
      if (!this.status.checked) return this.$t("sam.checking");
      if (!this.status.available) return this.status.message || this.$t("sam.unavailable");
      if (this.status.preparing) return this.$t("sam.preparing");
      if (this.status.predicting) return this.$t("sam.segmenting");
      if (this.preview) return this.$t("sam.score", { score: Math.max(0, this.score * 100).toFixed(0) });
      return this.status.model ? `${this.status.model} · ${this.$t("sam.hint")}` : this.$t("sam.hint");
    },
    imageId() {
      return this.$parent.image.id;
    },
    /**
     * What Enter adds: "outline" (the mask), "box" (the box around it) or
     * "rbox" (the smallest rotated box around it). Chosen per dataset
     * (remembered in this browser); by default from the dataset's task.
     */
    output: {
      get() {
        if (this.settings.output) return this.settings.output;
        const task = this.$parent.dataset && this.$parent.dataset.task;
        return task === "obb" ? "rbox" : task === "detect" ? "box" : "outline";
      },
      set(value) {
        this.settings.output = value;
        const id = this.$parent.dataset && this.$parent.dataset.id;
        if (id == null) return;
        try {
          localStorage.setItem(`sam/output/${id}`, value);
        } catch {
          // not remembered
        }
      }
    },
    boxMode() {
      return this.output !== "outline";
    },
    outputText() {
      return this.$t("sam.output." + this.output);
    }
  },
  methods: {
    export() {
      return { replace: this.settings.replace, obbPad: this.settings.obbPad };
    },
    setPreferences(pref) {
      if (pref.replace != null) this.settings.replace = pref.replace;
      if (pref.obbPad != null) this.settings.obbPad = pref.obbPad;
    },
    /** this dataset's choice of output (null: from its task) */
    loadOutput() {
      const id = this.$parent.dataset && this.$parent.dataset.id;
      let saved = null;
      try {
        saved = id == null ? null : localStorage.getItem(`sam/output/${id}`);
      } catch {
        saved = null;
      }
      this.settings.output = ["outline", "box", "rbox"].includes(saved) ? saved : null;
    },
    checkStatus() {
      axios
        .get("/api/model/")
        .then(response => {
          let sam = response.data.sam || {};
          this.status.available = !!sam.available;
          this.status.model = sam.model_type || "";
          this.status.message = sam.error || "";
        })
        .catch(() => {
          this.status.available = false;
        })
        .finally(() => (this.status.checked = true));
    },
    prepare() {
      if (!this.status.available || this.imageId == null) return;
      this.status.preparing = true;
      axios
        .post(`/api/model/sam/${this.imageId}/prepare`)
        .catch(() => {})
        .finally(() => (this.status.preparing = false));
    },

    /* ---------- coordinates ---------- */
    toImage(point) {
      let raster = this.$parent.image.raster;
      return [
        Math.round(point.x + raster.width / 2),
        Math.round(point.y + raster.height / 2)
      ];
    },

    /* ---------- drawing ---------- */
    drawMarkers() {
      if (this.markers) this.markers.remove();
      this.markers = null;
      if (!this.isActive) return;

      let r = 5 * this.scale;
      let items = this.points.map(
        p =>
          new paper.Path.Circle({
            center: p.point,
            radius: r,
            fillColor: p.label ? "#2ecc71" : "#e74c3c",
            strokeColor: "white",
            strokeWidth: 1.5 * this.scale
          })
      );
      if (this.box) {
        items.push(
          new paper.Path.Rectangle({
            from: this.box[0],
            to: this.box[1],
            strokeColor: "#f1c40f",
            strokeWidth: 1.5 * this.scale,
            dashArray: [6 * this.scale, 4 * this.scale]
          })
        );
      }
      this.markers = new paper.Group(items);
      this.markers.locked = true;
    },
    clearPreview() {
      if (this.preview) this.preview.remove();
      if (this.previewBox) this.previewBox.remove();
      this.preview = null;
      this.previewBox = null;
      this.previewCorners = null;
      this.score = null;
    },
    /** the rotated box around the preview (box mode) */
    drawPreviewBox() {
      if (this.previewBox) this.previewBox.remove();
      this.previewBox = null;
      this.previewCorners = null;
      if (!this.preview || !this.boxMode) {
        if (this.preview) this.preview.opacity = 0.45;
        return;
      }
      const points = [];
      this.preview.children.forEach(path => path.segments.forEach(seg => points.push({ x: seg.point.x, y: seg.point.y })));
      const pad = Math.max(0, Number(this.settings.obbPad) || 0);
      if (this.output === "box") {
        const xs = points.map(p => p.x), ys = points.map(p => p.y);
        if (!xs.length) return;
        const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad;
        const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
        this.previewCorners = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([x, y]) => new paper.Point(x, y));
      } else {
        const rect = minAreaRect(points, pad);
        if (!rect) return;
        this.previewCorners = rect.corners.map(c => new paper.Point(c.x, c.y));
      }
      // the mask fades, the box it gives is what will be added
      this.preview.opacity = 0.25;
      this.previewBox = new paper.Path({
        segments: this.previewCorners,
        closed: true,
        strokeColor: "#00e5ff",
        strokeWidth: 2 * this.scale,
        locked: true
      });
      // the first (heading) edge a bit thicker, as with the rotated box tool
      if (this.output === "box") {
        this.previewBox.locked = true;
        if (this.markers) this.markers.bringToFront();
        return;
      }
      const heading = new paper.Path.Line({
        from: this.previewCorners[0],
        to: this.previewCorners[1],
        strokeColor: "#00e5ff",
        strokeWidth: 4 * this.scale
      });
      this.previewBox = new paper.Group([this.previewBox, heading]);
      this.previewBox.locked = true;
      if (this.markers) this.markers.bringToFront();
    },
    showPreview(segmentation) {
      this.clearPreview();
      this.lastSegmentation = segmentation;
      if (!segmentation || segmentation.length === 0) return;

      let raster = this.$parent.image.raster;
      let center = new paper.Point(raster.width / 2, raster.height / 2);
      let compound = new paper.CompoundPath();
      segmentation.forEach(polygon => {
        let path = new paper.Path();
        for (let j = 0; j < polygon.length; j += 2) {
          path.add(new paper.Point(polygon[j], polygon[j + 1]).subtract(center));
        }
        path.closePath();
        compound.addChild(path);
      });

      let annotation = this.$parent.currentAnnotation;
      compound.fillColor = annotation ? annotation.color : "#3498db";
      compound.opacity = 0.45;
      compound.strokeColor = "white";
      compound.strokeWidth = 1.5 * this.scale;
      compound.dashArray = [4 * this.scale, 3 * this.scale];
      compound.locked = true;
      this.preview = compound;
      this.drawPreviewBox();
      if (this.markers) this.markers.bringToFront();
    },

    /* ---------- prediction ---------- */
    predict() {
      if (!this.hasPrompt) {
        this.clearPreview();
        return;
      }
      let body = {
        points: this.points.map(p => this.toImage(p.point)),
        labels: this.points.map(p => p.label)
      };
      if (this.box) {
        let [a, b] = this.box.map(this.toImage);
        body.box = [
          Math.min(a[0], b[0]),
          Math.min(a[1], b[1]),
          Math.max(a[0], b[0]),
          Math.max(a[1], b[1])
        ];
      }

      let id = ++this.requestId;
      this.status.predicting = true;
      axios
        .post(`/api/model/sam/${this.imageId}`, body)
        .then(response => {
          if (id !== this.requestId) return; // a newer prompt is on its way
          this.showPreview(response.data.segmentation);
          this.score = response.data.score;
        })
        .catch(error => {
          if (id !== this.requestId) return;
          let message =
            (error.response && error.response.data && error.response.data.message) ||
            this.$t("sam.requestFailed");
          this.$toastr.error(message, "SAM", { positionClass: "toast-bottom-left" });
        })
        .finally(() => {
          if (id === this.requestId) this.status.predicting = false;
        });
    },
    async apply() {
      let annotation = this.$parent.currentAnnotation;
      if (!this.preview || !annotation) return;
      if (this.boxMode && this.previewCorners) {
        await this.applyBox(annotation, this.previewCorners);
        return;
      }

      let shape = this.preview.clone();
      shape.locked = false;
      if (this.settings.replace && annotation.compoundPath) {
        annotation.subtract(annotation.compoundPath.clone(), false, true);
        annotation.unite(shape, true, false);
      } else {
        annotation.unite(shape, true, true);
      }
      shape.remove();
      this.reset();
    },
    /** box modes: one box per annotation (a new one when needed) */
    async applyBox(annotation, corners) {
      const parent = this.$parent;
      this.reset();
      const hasShape = annotation.compoundPath && !annotation.compoundPath.isEmpty();
      if (hasShape && !this.settings.replace) {
        const category = annotation.$parent && annotation.$parent.createAnnotation ? annotation.$parent : parent.currentCategory;
        if (!category) return;
        await category.createAnnotation();
        for (let i = 0; i < 5 && parent.currentAnnotation === annotation; i++) await this.$nextTick();
        annotation = parent.currentAnnotation;
        if (!annotation) return;
      }
      if (this.output === "box") {
        const rect = new paper.Path({ segments: corners, closed: true, insert: false });
        if (this.settings.replace && hasShape) annotation.subtract(annotation.compoundPath.clone(), false, true);
        annotation.unite(rect, true, !(this.settings.replace && hasShape), true);
        rect.remove();
        return;
      }
      annotation.setRotatedBox(corners);
    },
    undoPoint() {
      if (this.points.length > 0) this.points.pop();
      else this.box = null;
      this.drawMarkers();
      this.predict();
    },
    reset() {
      this.requestId++;
      this.points = [];
      this.box = null;
      this.status.predicting = false;
      this.clearPreview();
      this.drawMarkers();
    },

    /* ---------- mouse & keyboard ---------- */
    onMouseDown(event) {
      this.dragStart = event.point;
    },
    onMouseDrag(event) {
      if (!this.dragStart) return;
      if (event.point.getDistance(this.dragStart) < DRAG_THRESHOLD * this.scale) return;
      if (this.boxPath) this.boxPath.remove();
      this.boxPath = new paper.Path.Rectangle({
        from: this.dragStart,
        to: event.point,
        strokeColor: "#f1c40f",
        strokeWidth: 1.5 * this.scale
      });
      this.boxPath.locked = true;
    },
    onMouseUp(event) {
      if (!this.dragStart) return;
      let start = this.dragStart;
      this.dragStart = null;
      if (this.boxPath) {
        this.boxPath.remove();
        this.boxPath = null;
      }

      if (event.point.getDistance(start) >= DRAG_THRESHOLD * this.scale) {
        this.box = [start, event.point];
      } else {
        this.points.push({ point: event.point, label: event.modifiers.shift ? 0 : 1 });
      }
      this.drawMarkers();
      this.predict();
    },
    onKeyDown(e) {
      if (!this.isActive) return;
      let tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "Enter" && this.preview) {
        e.preventDefault();
        this.apply();
      }
    }
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
        localStorage.setItem("editorTool", this.name);
        this.prepare();
      } else {
        this.reset();
      }
    },
    "$parent.current.annotation"() {
      this.reset();
    },
    scale() {
      this.drawMarkers();
      this.drawPreviewBox();
    },
    output() {
      this.drawPreviewBox();
    },
    "settings.obbPad"() {
      this.drawPreviewBox();
    },
    "$parent.dataset.id": {
      immediate: true,
      handler() {
        this.loadOutput();
      }
    }
  },
  mounted() {
    this.checkStatus();
    window.addEventListener("keydown", this.onKeyDown);
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.onKeyDown);
    this.reset();
  }
};
</script>
