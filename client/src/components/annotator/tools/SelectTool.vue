<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import { TASK_TOOLS } from "@/components/TaskPicker.vue";

export default {
  name: "SelectTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-hand-pointer-o",
      name: "Select",
      cursor: "pointer",
      movePath: false,
      point: null,
      segment: null,
      scaleFactor: 15,
      edit: {
        indicatorWidth: 0,
        indicatorSize: 0,
        center: null,
        canMove: false
      },
      hover: {
        showText: true,
        text: null,
        // ID of annotation text has been generated for
        textId: -1,
        box: null,
        textShift: 0,
        fontSize: this.sacleFactor,
        shift: 0,
        rounded: 0,
        category: null,
        annotation: null,
        annotationText: null
      },
      keypoint: null,
      // dragging a rotated box: { mode: "move"|"resize", owner, ... }
      rbboxDrag: null,
      hitOptions: {
        segments: true,
        stroke: true,
        fill: false,
        tolerance: 10,
        match: hit => {
          return !hit.item.hasOwnProperty("indicator");
        }
      }
    };
  },
  methods: {
    export() {
      return {
        showText: this.hover.showText
      };
    },
    setPreferences(pref) {
      this.hover.showText = pref.showText || this.hover.showText;
    },
    generateTitle() {
      let string = " ";
      if (this.keypoint) {
        let index = this.keypoint.keypoint.indexLabel;
        let label = this.keypoint.keypoints.labels[index - 1];
        let visibility = this.keypoint.keypoint.visibility;
        let visibilityDesc = this.keypoint.keypoint.getVisibilityDescription();
        let annotationId = this.keypoint.keypoints.annotationId;
        let categoryName = this.keypoint.keypoints.categoryName;
        string += this.$t("hover.keypoint") + ": " + label + " \n";
        string += this.$t("hover.visibility") + ": " + visibility + " (" + this.$tr("option", visibilityDesc) + ") \n";
        if (annotationId !== -1) {
          string += "ID: " + annotationId + " \n";
        }
        if (categoryName) {
          string += this.$t("hover.category") + ": " + categoryName + " \n";
        }
        return string.replace(/\n/g, " \n ").slice(0, -2);
      }

      if (this.hover.category && this.hover.annotation) {
        let id = this.hover.annotation.annotation.id;
        let category = this.hover.category.category.name;
        string += "ID: " + id + " \n";
        string += this.$t("hover.category") + ": " + category + " \n";
      }

      if (this.$store.getters["user/loginEnabled"]) {
        let creator = this.hover.annotation.annotation.creator;
        if (creator != null) {
          string += this.$t("common.createdBy", { name: creator }) + "\n\n";
        }
      }

      return string.replace(/\n/g, " \n ").slice(0, -2) + " \n ";
    },
    generateStringFromMetadata() {
      if (this.keypoint) return "";
      let string = "";
      let metadata = this.hover.annotation.$refs.metadata.metadataList;

      if (metadata == null || metadata.length === 0) {
        string += this.$t("hover.noMetadata") + " \n";
      } else {
        string += this.$t("hover.metadata") + " \n";
        metadata.forEach(element => {
          if (element.key.length !== 0) {
            string += " " + element.key + " = " + element.value + " \n";
          }
        });
      }

      return string.replace(/\n/g, " \n ").slice(0, -2);
    },
    hoverText() {
      if (!this.hover.showText) return;
      if (!this.keypoint) {
        if (this.hover.category == null) return;
        if (this.hover.annotation == null) return;
      }

      let position = this.hover.position.add(this.hover.textShift, 0);

      if (
        this.hover.text == null ||
        this.hover.annotation.annotation.id !== this.hover.textId ||
        this.keypoint != null
      ) {
        if (this.hover.text !== null) {
          this.hover.text.remove();
          this.hover.box.remove();
        }
        let content = this.generateTitle() + this.generateStringFromMetadata();
        if (this.hover.annotation) {
          this.hover.textId = this.hover.annotation.annotation.id;
        }

        this.hover.text = new paper.PointText(position);
        this.hover.text.justification = "left";
        this.hover.text.fillColor = "black";
        this.hover.text.content = content;
        this.hover.text.indicator = true;

        this.hover.text.fontSize = this.hover.fontSize;

        this.hover.box = new paper.Path.Rectangle(
          this.hover.text.bounds,
          this.hover.rounded
        );
        this.hover.box.indicator = true;
        this.hover.box.fillColor = "white";
        this.hover.box.strokeColor = "white";
        this.hover.box.opacity = 0.5;

        this.hover.box.insertAbove(this.rect);
      }

      this.hover.shift =
        (this.hover.text.bounds.bottomRight.x -
          this.hover.text.bounds.bottomLeft.x) /
        2;
      this.hover.box.position = position.add(this.hover.shift, 0);
      this.hover.text.position = position.add(this.hover.shift, 0);

      this.hover.box.bringToFront();
      this.hover.text.bringToFront();
    },
    checkBbox(paperObject) {
      if (!paperObject) return false;
      let annotationId = paperObject.data.annotationId;
      let categoryId = paperObject.data.categoryId;
      if (annotationId == null || categoryId == null) return false;
      let category = this.$parent.getCategory(categoryId);
      let annotation = category && category.getAnnotation(annotationId);
      return !!(annotation && annotation.annotation.isbbox);
    },
    /** Annotation component of a rotated box under `item`, if any */
    rotatedBoxAnnotation(item) {
      if (!item || item.className !== "CompoundPath") return null;
      let data = item.data || {};
      if (data.annotationId == null || data.categoryId == null) return null;
      let category = this.$parent.getCategory(data.categoryId);
      if (!category) return null;
      let annotation = category.getAnnotation(data.annotationId);
      if (!annotation || !annotation.getRotatedBoxCorners()) return null;
      return annotation;
    },
    /**
     * Rotated boxes stay rectangles: dragging inside moves the box (like a
     * BBox), dragging a corner resizes it keeping its angle with the
     * opposite corner fixed. Edges never get extra points.
     */
    startRotatedBoxDrag(event, hitResult) {
      let onOutline =
        hitResult && (hitResult.type === "segment" || hitResult.type === "stroke");
      let item = onOutline ? hitResult.item.parent : event.item;
      let owner = this.rotatedBoxAnnotation(item);
      if (!owner) return false;
      if (event.modifiers.shift) return true; // no point removal on boxes

      if (hitResult && hitResult.type === "segment") {
        let corners = owner.getRotatedBoxCorners();
        let i = hitResult.segment.index;
        this.rbboxDrag = { mode: "resize", owner, corners, corner: i, anchor: corners[(i + 2) % 4] };
      } else {
        this.rbboxDrag = { mode: "move", owner, last: event.point };
      }
      return true;
    },
    dragRotatedBox(event) {
      let d = this.rbboxDrag;
      let path = d.owner.compoundPath && d.owner.compoundPath.children[0];
      if (!path) return;
      if (!d.undoSaved) {
        d.owner.createUndoAction(d.mode === "move" ? "Move" : "Resize");
        d.undoSaved = true;
        path = d.owner.compoundPath.children[0];
      }

      if (d.mode === "move") {
        let delta = event.point.subtract(d.last);
        path.segments.forEach(seg => {
          seg.point = seg.point.add(delta);
        });
        d.last = event.point;
        return;
      }

      let [c0, c1, c2] = d.corners;
      let u = c1.subtract(c0).normalize();
      let v = c2.subtract(c1).normalize();
      let diff = event.point.subtract(d.anchor);
      let w = Math.abs(diff.dot(u));
      let h = Math.abs(diff.dot(v));
      if (w < 1 || h < 1) return;
      let center = d.anchor.add(diff.divide(2));
      let signs = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
      path.segments.forEach((seg, k) => {
        seg.point = center
          .add(u.multiply((signs[k][0] * w) / 2))
          .add(v.multiply((signs[k][1] * h) / 2));
      });
    },
    onMouseDown(event) {
      // start from where the press is: the tool may not have seen the mouse
      // move here (e.g. picked by holding left + right), and a stale start
      // point would make the first drag jump
      this.onMouseMove(event);
      this.rbboxDrag = null;
      this.noteTaskToolClick(event);

      let hitResult = this.$parent.paper.project.hitTest(
        event.point,
        this.hitOptions
      );

      if (this.startRotatedBoxDrag(event, hitResult)) return;
      if (!hitResult) return;

      if (event.modifiers.shift) {
        if (hitResult.type === "segment") {
          hitResult.segment.remove();
        }
        return;
      }
      let path = hitResult.item;
      let paperObject = null;
      if (hitResult.type === "segment") {
        this.segment = hitResult.segment;
        paperObject = path.parent;
      } else if (hitResult.type === "stroke") {
        if (this.checkBbox(path.parent)) {
          // a box keeps its 4 corners: pressing on its edge moves it
          this.initPoint = event.point;
          this.moveObject = path.parent;
          paperObject = path.parent;
        } else {
          let location = hitResult.location;
          this.segment = path.insert(location.index + 1, event.point);
        }
      } else if (event.item.className == "CompoundPath") {
        this.initPoint = event.point;
        this.moveObject = event.item;
        paperObject = event.item;
      }
      this.isBbox = this.checkBbox(paperObject);
      // a press that hit a corner or an edge drags it (the round marker is
      // only a hint and can be smaller than the grab distance)
      this.edit.canMove = !!this.segment;
    },
    clear() {
      this.hover.category = null;
      this.hover.annotation = null;
      this.isBbox = false;
      this.segment = null;
      this.moveObject = null;
      if (this.hover.text != null) {
        this.hover.text.remove();
        this.hover.box.remove();
        this.hover.text = null;
        this.hover.box = null;
      }
    },
    createPoint(point) {
      if (this.point != null) {
        this.point.remove();
      }

      this.point = new paper.Path.Circle(point, this.edit.indicatorSize);
      this.point.strokeColor = "black";
      this.point.strokeWidth = this.edit.indicatorWidth;
      this.point.indicator = true;
    },
    onMouseDrag(event) {
      if (this.rbboxDrag) {
        this.dragRotatedBox(event);
        return;
      }
      if (this.isBbox && this.moveObject) {
        let delta_x = this.initPoint.x - event.point.x;
        let delta_y = this.initPoint.y - event.point.y;
        let segments = this.moveObject.children[0].segments;
        segments.forEach(segment => {
          let p = segment.point;
          segment.point = new paper.Point(p.x - delta_x, p.y - delta_y);
        });
        this.initPoint = event.point;
      }
      if (this.segment && this.edit.canMove) {
        this.createPoint(event.point);
        if (this.isBbox) {
          //counter clockwise prev and next.
          let isCounterClock =
            this.segment.previous.point.x == this.segment.point.x;
          let prev = isCounterClock ? this.segment.previous : this.segment.next;
          let next = !isCounterClock
            ? this.segment.previous
            : this.segment.next;

          prev.point = new paper.Point(event.point.x, prev.point.y);
          next.point = new paper.Point(next.point.x, event.point.y);
        } //getbbox here somehow
        this.segment.point = event.point;
      }
      else if (!this.keypoint) {
        // the event point exists on a relative coordinate system (dependent on screen dimensions) 
        // however, the image on the canvas paper exists on an absolute coordinate system
        // thus, tracking mouse deltas from the previous point is necessary
        let delta_x = this.initPoint.x - event.point.x;
        let delta_y = this.initPoint.y - event.point.y;
        let center_delta = new paper.Point(delta_x, delta_y);
        let new_center = this.$parent.paper.view.center.add(center_delta);
        this.$parent.paper.view.setCenter(new_center);
      }
      
    },

    /**
     * A plain click (no drag) on a shape of the dataset's planned kind (a
     * rotated box in an OBB dataset, a box in a detection one, ...) goes on
     * with the dataset's tool for it. Not while Select is only held for a
     * moment (left + right buttons), and not with Shift.
     */
    noteTaskToolClick(event) {
      this.taskToolClick = null;
      const parent = this.$parent;
      const task = parent.dataset && parent.dataset.task;
      const tool = task && TASK_TOOLS[task];
      if (!tool || (parent.chord && parent.chord.active) || this.mod(event, "shift")) return;
      if (parent.toolForShapeAt && parent.toolForShapeAt(event.point) === tool) {
        const e = event.event || {};
        this.taskToolClick = { tool, x: e.clientX, y: e.clientY };
      }
    },
    switchAfterClick(event) {
      const click = this.taskToolClick;
      this.taskToolClick = null;
      if (!click || (this.$parent.chord && this.$parent.chord.active)) return;
      const e = event.event || {};
      if (Math.hypot((e.clientX ?? click.x) - click.x, (e.clientY ?? click.y) - click.y) > 4) return; // dragged
      // after the click has selected the shape (the tool needs an annotation)
      setTimeout(() => {
        const ref = this.$parent.toolRef(click.tool);
        if (this.$parent.activeTool === "Select" && ref && !ref.isDisabled) {
          ref.tool.activate();
          this.$parent.activeTool = click.tool;
        }
      }, 0);
    },
    mod(event, key) {
      const e = event.event;
      if (e && typeof e.shiftKey === "boolean") return key === "shift" ? e.shiftKey : e.ctrlKey || e.metaKey;
      const m = event.modifiers || {};
      return key === "shift" ? !!m.shift : !!(m.control || m.command);
    },
    onMouseUp(event) {
      this.switchAfterClick(event);
      if (this.rbboxDrag && this.rbboxDrag.undoSaved) {
        this.rbboxDrag.owner.emitModify();
      }
      this.rbboxDrag = null;
      this.clear();
    },

    onMouseMove(event) {
      // ensures that the initPoint is always tracked. 
      // Necessary for the introduced pan functionality and fixes a bug with selecting and dragging bboxes, since initPoint is initially undefined
      this.initPoint = event.point;  

      let hitResult = this.$parent.paper.project.hitTest(
        event.point,
        this.hitOptions
      );

      if (hitResult) {
        let point = null;

        if (hitResult.type === "segment") {
          point = hitResult.segment.location.point;
        } else if (hitResult.type === "stroke") {
          point = hitResult.location.point;
        }

        if (point != null) {
          this.edit.center = point;
          this.createPoint(point);
        } else {
          if (this.point != null) {
            this.point.remove();
            this.point = null;
          }
        }
      }

      this.$parent.hover.annotation = -1;
      this.$parent.hover.category = -1;

      this.$parent.paper.project.activeLayer.selected = false;
      let item = event.item;

      this.keypoint = null;

      if (
        item &&
        item.data.hasOwnProperty("annotationId") &&
        item.data.hasOwnProperty("categoryId")
      ) {
        this.hover.position = event.point;

        let categoryId = event.item.data.categoryId;
        let annotationId = event.item.data.annotationId;
        this.$parent.hover.categoryId = categoryId;
        this.$parent.hover.annotation = annotationId;

        this.hover.category = this.$parent.getCategory(categoryId);
        if (this.hover.category != null) {
          this.hover.annotation = this.hover.category.getAnnotation(
            annotationId
          );
          event.item.selected = true;
          this.hoverText();
        }
      } else if (event.item && event.item.hasOwnProperty("keypoint")) {
        this.hover.position = event.point;
        this.keypoint = item;
      } else if (
        item &&
        item.lastChild &&
        item.lastChild.hasOwnProperty("keypoint")
      ) {
        this.hover.position = event.point;
        for (let i = 0; i < item.children.length; ++i) {
          if (item.children[i].hasOwnProperty("keypoint")) {
            let keypoint = item.children[i].keypoint;
            if (event.point.getDistance(keypoint) <= keypoint.radius) {
              this.keypoint = item.children[i];
              break;
            }
          }
        }
      } else {
        this.clear();
      }
    }
  },
  watch: {
    keypoint(keypoint) {
      this.clear();
      if (!keypoint) return;
      this.hoverText();
    },
    scale: {
      handler(newScale) {
        this.hover.rounded = newScale * 5;
        this.hover.textShift = newScale * 40;
        this.hover.fontSize = newScale * this.scaleFactor;
        this.edit.distance = newScale * 40;
        this.edit.indicatorSize = newScale * 10;
        this.edit.indicatorWidth = newScale * 2;
        // grab corners / edges within 10 screen pixels at any zoom (a fixed
        // 10 image pixels was 2 px on screen zoomed out, 40 px zoomed in)
        this.hitOptions.tolerance = newScale * 10;

        if (this.edit.center && this.point != null) {
          this.createPoint(this.edit.center);
        }

        if (this.hover.text != null) {
          this.hover.text.fontSize = this.hover.fontSize;
          this.hover.shift =
            (this.hover.text.bounds.bottomRight.x -
              this.hover.text.bounds.bottomLeft.x) /
            2;
          let totalShift = this.hover.shift + this.hover.textShift;
          this.hover.text.position = this.hover.position.add(totalShift, 0);
          this.hover.box.bounds = this.hover.text.bounds;
        }
      },
      immediate: true
    },
    isActive(active) {
      if (active) {
        this.tool.activate();
      } else {
        if (this.hover.text) {
          this.hover.text.remove();
          this.hover.box.remove();

          this.hover.box = null;
          this.hover.text = null;
        }
        if (this.point) {
          this.point.remove();
          this.point = null;
          this.segment = null;
        }
        if (this.hover.annotation) {
          this.hover.annotation.compoundPath.selected = false;
        }
      }
    }
  }
};
</script>
