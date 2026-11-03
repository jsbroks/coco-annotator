<script>
import { modalOpen } from "@/libs/modal";
import paper from "paper";
import tool from "@/mixins/toolBar/tool";

/**
 * Rotated (oriented) bounding box tool.
 *
 * Drawing a new box takes three clicks:
 *   1. click the first corner
 *   2. click the second corner: these two points are one edge of the box
 *      (its direction and length; dragging from 1 to 2 works too)
 *   3. move the mouse to set the width and click again to finish
 *   Esc cancels. Hold Shift while placing point 2 to snap the angle.
 *
 * Editing the selected box:
 *   - arrow keys                move 1 px (Shift: 10 px)
 *   - drag the round handle     rotate (hold Shift to snap)
 *   - drag a corner handle      resize, the opposite corner stays put
 *   - drag inside the box       move
 *
 * Boxes are stored as a 4-corner polygon in corner order, plus
 * annotation.isrbbox; the server derives rbbox = [cx, cy, w, h, angle].
 */
const HANDLE_SIZE = 7; // screen pixels
const ROTATE_OFFSET = 25; // screen pixels between box edge and rotate handle
const MIN_SIZE = 2; // screen pixels

function toRad(deg) {
  return (deg * Math.PI) / 180;
}

function toDeg(rad) {
  return (rad * 180) / Math.PI;
}

function normaliseAngle(angle) {
  angle = ((((angle + 180) % 360) + 360) % 360) - 180;
  return angle === -180 ? 180 : angle;
}

export default {
  name: "RotatedBBoxTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-square-o",
      iconRotate: -30,
      name: "Rotated BBox",
      cursor: "crosshair",
      box: null, // { cx, cy, w, h, angle } in paper coordinates, angle in degrees
      overlay: null,
      drag: null, // editing an existing box
      drawing: null, // { points: [p1, p2?], cursor } while placing a new box
      pendingCommits: 0,
      commitQueue: Promise.resolve(),
      lastNudge: 0,
      settings: {
        snap: 15,
        strokeColor: "#00e5ff"
      }
    };
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation === -1;
    },
    annotationComponent() {
      return this.$parent.currentAnnotation;
    },
    /** The category new boxes go to, when it is not the selected box's one */
    drawCategoryComponent() {
      const id = this.$parent.drawCategoryId;
      if (id == null) return null;
      const current = this.$parent.currentCategory;
      if (current && current.category.id === id) return null;
      return (this.$parent.categoryRefs() || []).find(c => c.category.id === id) || null;
    },
    boxInfo() {
      if (!this.box) return null;
      return {
        w: this.box.w.toFixed(1),
        h: this.box.h.toFixed(1),
        angle: this.box.angle.toFixed(1)
      };
    },
    hint() {
      if (this.drawing) {
        if (this.drawing.points.length === 1) return this.$t("rbbox.step2");
        return this.$t("rbbox.step3");
      }
      const base = this.boxInfo
        ? `${this.boxInfo.w} × ${this.boxInfo.h} px, ${this.boxInfo.angle}°`
        : this.$t("rbbox.step1");
      const other = this.drawCategoryComponent;
      return other ? `${base} · ${this.$t("rbbox.newIn", { name: other.category.name })}` : base;
    }
  },
  methods: {
    export() {
      return {
        snap: this.settings.snap,
        strokeColor: this.settings.strokeColor
      };
    },
    setPreferences(pref) {
      if (pref.snap != null) this.settings.snap = pref.snap;
      if (pref.strokeColor) this.settings.strokeColor = pref.strokeColor;
    },

    /* ---------- geometry ---------- */
    axes(angle) {
      let t = toRad(angle);
      let u = new paper.Point(Math.cos(t), Math.sin(t));
      let v = new paper.Point(-Math.sin(t), Math.cos(t));
      return { u, v };
    },
    corners(box) {
      let { u, v } = this.axes(box.angle);
      let c = new paper.Point(box.cx, box.cy);
      let hu = u.multiply(box.w / 2);
      let hv = v.multiply(box.h / 2);
      return [
        c.subtract(hu).subtract(hv),
        c.add(hu).subtract(hv),
        c.add(hu).add(hv),
        c.subtract(hu).add(hv)
      ];
    },
    boxFromCorners(points) {
      let [p0, p1, p2] = points;
      let center = points
        .reduce((acc, p) => acc.add(p), new paper.Point(0, 0))
        .divide(4);
      let edge = p1.subtract(p0);
      return {
        cx: center.x,
        cy: center.y,
        w: edge.length,
        h: p2.subtract(p1).length,
        angle: normaliseAngle(toDeg(Math.atan2(edge.y, edge.x)))
      };
    },
    /** Box spanned by two opposite corners in the frame rotated by angle */
    boxFromDiagonal(a, b, angle) {
      let { u, v } = this.axes(angle);
      let d = b.subtract(a);
      let center = a.add(d.divide(2));
      return {
        cx: center.x,
        cy: center.y,
        w: Math.abs(d.dot(u)),
        h: Math.abs(d.dot(v)),
        angle
      };
    },
    /**
     * Box with one edge from p1 to p2, extended sideways to the cursor.
     * The edge p1 -> p2 becomes the box's first edge (its heading).
     */
    boxFromEdge(p1, p2, cursor) {
      let edge = p2.subtract(p1);
      let angle = toDeg(Math.atan2(edge.y, edge.x));
      let { v } = this.axes(angle);
      let height = cursor.subtract(p1).dot(v); // signed distance from the edge
      // keep p1 -> p2 on the side the box grows from
      let center = p1.add(edge.divide(2)).add(v.multiply(height / 2));
      if (height < 0) {
        angle += 180;
        height = -height;
      }
      return {
        cx: center.x,
        cy: center.y,
        w: edge.length,
        h: height,
        angle: normaliseAngle(angle)
      };
    },
    /** Second point, optionally snapped so the edge angle is a multiple of snap */
    snapPoint(p1, point, shift) {
      if (!shift || !(this.settings.snap > 0)) return point;
      let d = point.subtract(p1);
      let step = this.settings.snap;
      let angle = Math.round(toDeg(Math.atan2(d.y, d.x)) / step) * step;
      let { u } = this.axes(angle);
      return p1.add(u.multiply(d.length));
    },
    toLocal(point, box) {
      let { u, v } = this.axes(box.angle);
      let d = point.subtract(new paper.Point(box.cx, box.cy));
      return { a: d.dot(u), b: d.dot(v) };
    },
    rotateHandlePosition(box) {
      let { v } = this.axes(box.angle);
      let c = new paper.Point(box.cx, box.cy);
      return c.subtract(v.multiply(box.h / 2 + ROTATE_OFFSET * this.scale));
    },

    /* ---------- overlay ---------- */
    clearOverlay() {
      if (this.overlay) this.overlay.remove();
      this.overlay = null;
    },
    marker(point) {
      return new paper.Path.Circle({
        center: point,
        radius: 4 * this.scale,
        fillColor: this.settings.strokeColor,
        strokeColor: "black",
        strokeWidth: 0.5 * this.scale
      });
    },
    drawPreview() {
      this.clearOverlay();
      if (!this.drawing || !this.isActive) return;

      let stroke = this.settings.strokeColor;
      let [p1, p2] = this.drawing.points;
      let cursor = this.drawing.cursor || p1;
      let items = [this.marker(p1)];

      if (!p2) {
        // placing the second point: rubber-band edge
        items.push(
          new paper.Path.Line({
            from: p1,
            to: cursor,
            strokeColor: stroke,
            strokeWidth: 3 * this.scale
          })
        );
      } else {
        let box = this.boxFromEdge(p1, p2, cursor);
        items.push(
          new paper.Path({
            segments: this.corners(box),
            closed: true,
            strokeColor: stroke,
            strokeWidth: 1.5 * this.scale,
            dashArray: [6 * this.scale, 4 * this.scale],
            fillColor: new paper.Color(0, 0.9, 1, 0.12)
          }),
          new paper.Path.Line({
            from: p1,
            to: p2,
            strokeColor: stroke,
            strokeWidth: 3 * this.scale
          }),
          this.marker(p2)
        );
      }
      this.overlay = new paper.Group(items);
      this.overlay.locked = true;
    },
    drawOverlay() {
      if (this.drawing) {
        this.drawPreview();
        return;
      }
      this.clearOverlay();
      if (!this.box || !this.isActive) return;

      let corners = this.corners(this.box);
      let size = HANDLE_SIZE * this.scale;
      let stroke = this.settings.strokeColor;

      let outline = new paper.Path({
        segments: corners,
        closed: true,
        strokeColor: stroke,
        strokeWidth: 1.5 * this.scale,
        dashArray: [6 * this.scale, 4 * this.scale]
      });
      // mark the first edge so the box's heading is visible
      let heading = new paper.Path.Line({
        from: corners[0],
        to: corners[1],
        strokeColor: stroke,
        strokeWidth: 3 * this.scale
      });

      let top = corners[0].add(corners[1]).divide(2);
      let rotatePos = this.rotateHandlePosition(this.box);
      let stem = new paper.Path.Line({
        from: top,
        to: rotatePos,
        strokeColor: stroke,
        strokeWidth: 1 * this.scale
      });
      let rotate = new paper.Path.Circle({
        center: rotatePos,
        radius: size * 0.8,
        fillColor: stroke,
        strokeColor: "black",
        strokeWidth: 0.5 * this.scale
      });

      let handles = corners.map(
        p =>
          new paper.Path.Rectangle({
            point: p.subtract(size / 2),
            size: [size, size],
            fillColor: "white",
            strokeColor: "black",
            strokeWidth: 0.5 * this.scale
          })
      );

      this.overlay = new paper.Group([outline, heading, stem, rotate, ...handles]);
      this.overlay.locked = true; // never steal clicks from annotations
    },

    /* ---------- annotation sync ---------- */
    syncFromAnnotation() {
      if (this.drag || this.drawing) return;
      let annotation = this.annotationComponent;
      let corners = annotation ? annotation.getRotatedBoxCorners() : null;
      this.box = corners ? this.boxFromCorners(corners) : null;
      this.drawOverlay();
    },
    annotationHasShape(annotation) {
      if (!annotation) return false;
      let path = annotation.compoundPath;
      return path != null && !path.isEmpty();
    },
    /**
     * Apply a box to the selected annotation. A new box drawn over an
     * annotation that already has a shape gets a new annotation, which
     * needs a server round trip: the box is shown immediately and commits
     * are queued, so the next box can be drawn while it is being created.
     */
    commit(box, isNew) {
      this.box = box;
      this.drawOverlay();
      this.pendingCommits += 1;
      // the box belongs to the annotation selected now, even if another one is
      // picked before an earlier queued commit has finished (while a new box
      // is still being created, an edit goes to that new one)
      const target = this.pendingCommits > 1 ? null : this.$parent.currentAnnotation;
      this.commitQueue = this.commitQueue
        .then(() => this.applyBox(box, isNew, target))
        .catch(error => console.error("rotated box", error))
        .finally(() => {
          this.pendingCommits -= 1;
        });
      return this.commitQueue;
    },
    async applyBox(box, isNew, target) {
      let parent = this.$parent;
      let annotation = target || parent.currentAnnotation;

      let category = (target && target.$parent && target.$parent.createAnnotation) ? target.$parent : parent.currentCategory;
      let needsNew = this.annotationHasShape(annotation);
      // a box selected on the image (to edit it) belongs to another category:
      // a new box still goes to the category being drawn
      const drawing = isNew ? this.drawCategoryComponent : null;
      if (drawing && drawing !== category) {
        category = drawing;
        needsNew = true;
      }
      if (isNew && needsNew && category) {
        await category.createAnnotation();
        // wait until the new annotation is mounted and selected
        for (let i = 0; i < 5 && parent.currentAnnotation === annotation; i++) {
          await this.$nextTick();
        }
        annotation = parent.currentAnnotation;
      }
      if (!annotation) {
        this.$toastr.warning(this.$t("rbbox.noAnnotation"));
        return;
      }

      annotation.setRotatedBox(this.corners(box));
      // a new box for an object with keypoints: they come next
      if (isNew && parent.afterBoxDrawn) parent.afterBoxDrawn(this.name);
      if (!this.drawing && !this.drag && annotation === parent.currentAnnotation) {
        this.box = box;
        this.drawOverlay();
      }
    },
    cancelDrawing() {
      if (!this.drawing) return;
      this.drawing = null;
      this.syncFromAnnotation();
    },

    /* ---------- mouse ---------- */
    hitTest(point) {
      if (!this.box) return null;
      let tol = HANDLE_SIZE * this.scale * 1.2;

      if (point.getDistance(this.rotateHandlePosition(this.box)) <= tol) {
        return { mode: "rotate" };
      }
      let corners = this.corners(this.box);
      for (let i = 0; i < 4; i++) {
        if (point.getDistance(corners[i]) <= tol) {
          return { mode: "resize", corner: i };
        }
      }
      let { a, b } = this.toLocal(point, this.box);
      if (Math.abs(a) <= this.box.w / 2 && Math.abs(b) <= this.box.h / 2) {
        return { mode: "move" };
      }
      return null;
    },
    startDrag(hit, point) {
      let corners = this.corners(this.box);
      this.drag = {
        ...hit,
        start: point,
        startBox: { ...this.box },
        anchor: hit.mode === "resize" ? corners[(hit.corner + 2) % 4] : null
      };
    },
    onMouseDown(event) {
      // points 2 and 3 of a new box are taken on mouse up
      if (this.drawing) return;

      // the shape may have changed elsewhere (undo, other tools); while a new
      // box is still being created on the server, the box shown is the one
      if (!this.pendingCommits) this.syncFromAnnotation();
      let point = event.point;
      let hit = this.hitTest(point);

      if (hit) {
        this.startDrag(hit, point);
        return;
      }

      // pressing on another rotated box (inside or on its outline / corners)
      // selects it, and a press on its corner or inside starts dragging right
      // away (Ctrl/⌘ + click starts a new box there instead)
      if (!this.mod(event, "ctrl")) {
        let target = this.boxAt(point);
        if (target) {
          this.$parent.onCategoryClick({ ...target, keypoint: -1, fromCanvas: true });
          this.syncFromAnnotation();
          let picked = this.hitTest(point);
          if (picked) this.startDrag(picked, point);
          return;
        }
      }

      // first point of a new box
      this.box = null;
      this.drawing = { points: [point], cursor: point };
      this.drawPreview();
    },
    /**
     * Modifier state from the browser event that caused this mouse event.
     * paper.js tracks modifiers from key events, which can stay "pressed"
     * when the key is released outside the page (e.g. after Shift+Win+S).
     */
    mod(event, key) {
      let e = event.event;
      if (e && typeof e.shiftKey === "boolean") {
        return key === "shift" ? e.shiftKey : e.ctrlKey || e.metaKey;
      }
      let m = event.modifiers || {};
      return key === "shift" ? !!m.shift : !!(m.control || m.command);
    },
    /** The visible rotated box (other than the selected one) under a point */
    boxAt(point) {
      let parent = this.$parent;
      let best = null;
      parent.categoryRefs().forEach(category => {
        if (!category.isVisible) return;
        category.annotationRefs().forEach(annotation => {
          if (!annotation.isVisible) return;
          if (
            category.index === parent.current.category &&
            annotation.index === parent.current.annotation
          ) {
            return;
          }
          let corners = annotation.getRotatedBoxCorners();
          if (!corners) return;
          let path = new paper.Path({ segments: corners, closed: true, insert: false });
          // on the outline or a corner handle counts too
          let near = path.getNearestPoint(point);
          let tol = HANDLE_SIZE * this.scale * 1.2;
          if (path.contains(point) || (near && near.getDistance(point) <= tol)) {
            let area = Math.abs(path.area);
            // the smallest box wins when boxes overlap
            if (!best || area < best.area) {
              best = { area, category: category.index, annotation: annotation.index };
            }
          }
          path.remove();
        });
      });
      return best && { category: best.category, annotation: best.annotation };
    },
    onMouseMove(event) {
      if (!this.drawing) return;
      let [p1, p2] = this.drawing.points;
      this.drawing.cursor = p2 ? event.point : this.snapPoint(p1, event.point, this.mod(event, "shift"));
      this.drawPreview();
    },
    onMouseDrag(event) {
      if (this.drawing) {
        // dragging from the first point also defines the first edge
        this.onMouseMove(event);
        return;
      }
      if (!this.drag) return;
      let d = this.drag;
      let point = event.point;

      if (d.mode === "move") {
        let delta = point.subtract(d.start);
        this.box = {
          ...d.startBox,
          cx: d.startBox.cx + delta.x,
          cy: d.startBox.cy + delta.y
        };
      } else if (d.mode === "resize") {
        this.box = this.boxFromDiagonal(d.anchor, point, d.startBox.angle);
      } else if (d.mode === "rotate") {
        let c = new paper.Point(d.startBox.cx, d.startBox.cy);
        let dir = point.subtract(c);
        let angle = toDeg(Math.atan2(dir.y, dir.x)) + 90;
        if (this.mod(event, "shift") && this.settings.snap > 0) {
          angle = Math.round(angle / this.settings.snap) * this.settings.snap;
        }
        this.box = { ...d.startBox, angle: normaliseAngle(angle) };
      }
      this.drawOverlay();
    },
    onMouseUp(event) {
      let min = MIN_SIZE * this.scale;

      if (this.drawing) {
        let points = this.drawing.points;
        let p1 = points[0];
        if (points.length === 1) {
          let p2 = this.snapPoint(p1, event.point, this.mod(event, "shift"));
          // the mouse up of the first click: wait for the second click
          if (p2.getDistance(p1) < min) return;
          points.push(p2);
          this.drawing.cursor = event.point;
          this.drawPreview();
          return;
        }
        let box = this.boxFromEdge(p1, points[1], event.point);
        if (box.h < min) return; // need some width: keep waiting
        this.drawing = null;
        this.commit(box, true);
        return;
      }

      if (!this.drag) return;
      this.drag = null;
      if (!this.box || this.box.w < min || this.box.h < min) {
        this.syncFromAnnotation();
        return;
      }
      this.commit(this.box, false);
    },
    /**
     * Arrow keys move the selected box (1 image pixel, 10 with Shift).
     * Registered in the capture phase so the annotator's own arrow-key
     * shortcuts (next/previous annotation) do not also fire.
     */
    onNudgeKey(e) {
      if (!this.isActive || this.drawing || this.drag || this.pendingCommits || modalOpen()) return;
      let step = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
      if (!step) return;
      let tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      this.syncFromAnnotation();
      let annotation = this.annotationComponent;
      if (!this.box || !annotation) return;

      e.preventDefault();
      e.stopPropagation();

      let distance = e.shiftKey ? 10 : 1;
      this.box = {
        ...this.box,
        cx: this.box.cx + step[0] * distance,
        cy: this.box.cy + step[1] * distance
      };
      // one undo step per burst of key presses, not one per press
      let now = Date.now();
      annotation.setRotatedBox(this.corners(this.box), now - this.lastNudge > 1000);
      this.lastNudge = now;
      this.drawOverlay();
    },
    onKeyDown(e) {
      if (!this.isActive || !this.drawing) return;
      if (e.key === "Escape") {
        e.preventDefault();
        this.cancelDrawing();
      }
    },

    /* ---------- panel actions ---------- */
    rotateBy(degrees) {
      if (!this.box) return;
      this.commit({ ...this.box, angle: normaliseAngle(this.box.angle + degrees) }, false);
    },
    /** Rotate the corner order by 90° without moving the box (changes heading) */
    swapHeading() {
      if (!this.box) return;
      let b = this.box;
      this.commit({ ...b, w: b.h, h: b.w, angle: normaliseAngle(b.angle + 90) }, false);
    },
    /** the selected annotation's outline (polygon, box) -> rotated box */
    convertCurrent() {
      const annotation = this.annotationComponent;
      if (!annotation || annotation.annotation.isrbbox || !annotation.toRotatedBox()) {
        this.$toastr.info(this.$t("rbbox.nothingToConvert"));
        return;
      }
      this.syncFromAnnotation();
      this.$toastr.success(this.$t("rbbox.converted", { n: 1 }));
    },
    /** every outline on this image that is not a rotated box yet */
    convertAll() {
      const targets = [];
      this.$parent.categoryRefs().forEach(category =>
        category.annotationRefs().forEach(a => {
          if (!a.annotation.isrbbox && a.compoundPath && !a.compoundPath.isEmpty()) targets.push(a);
        }));
      if (!targets.length) {
        this.$toastr.info(this.$t("rbbox.nothingToConvert"));
        return;
      }
      if (!confirm(this.$t("rbbox.convertAllConfirm", { n: targets.length }))) return;
      const n = targets.filter(a => a.toRotatedBox()).length;
      this.syncFromAnnotation();
      this.$toastr.success(this.$t("rbbox.converted", { n }));
    },
    deleteBox() {
      this.box = null;
      this.clearOverlay();
    }
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
        localStorage.setItem("editorTool", this.name);
        this.syncFromAnnotation();
      } else {
        this.drag = null;
        this.drawing = null;
        this.clearOverlay();
      }
    },
    annotationComponent() {
      if (this.isActive) this.syncFromAnnotation();
    },
    "$parent.current.annotation"() {
      // selecting another annotation cancels a box being drawn, but not when
      // the change is our own (a queued box selecting its new annotation)
      if (!this.pendingCommits) this.drawing = null;
      if (this.isActive) this.$nextTick(() => this.syncFromAnnotation());
    },
    scale() {
      this.drawOverlay();
    },
    "settings.strokeColor"() {
      this.drawOverlay();
    }
  },
  mounted() {
    window.addEventListener("keydown", this.onKeyDown);
    window.addEventListener("keydown", this.onNudgeKey, true);
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.onKeyDown);
    window.removeEventListener("keydown", this.onNudgeKey, true);
    this.clearOverlay();
  }
};
</script>
