<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";

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
        string += "Keypoint: " + label + " \n";
        string += "Visibility: " + visibility + " (" + visibilityDesc + ") \n";
        if (annotationId !== -1) {
          string += "ID: " + annotationId + " \n";
        }
        if (categoryName) {
          string += "Category: " + categoryName + " \n";
        }
        return string.replace(/\n/g, " \n ").slice(0, -2);
      }

      if (this.hover.category && this.hover.annotation) {
        let id = this.hover.textId;
        let category = this.hover.category.category.name;
        string += "ID: " + id + " \n";
        string += "Category: " + category + " \n";
      }

      if (this.$store.getters["user/loginEnabled"]) {
        let creator = this.hover.annotation.annotation.creator;
        if (creator != null) {
          string += "Created by " + creator + "\n\n";
        }
      }

      return string.replace(/\n/g, " \n ").slice(0, -2) + " \n ";
    },
    generateStringFromMetadata() {
      if (this.keypoint) return "";
      let string = "";
      let metadata = this.hover.annotation.$refs.metadata.metadataList;

      if (metadata == null || metadata.length === 0) {
        string += "No Metadata \n";
      } else {
        string += "Metadata \n";
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
      let category = this.$parent.getCategory(categoryId);
      let annotation = category.getAnnotation(annotationId);
      return annotation.annotation.isbbox;
    },
    onMouseDown(event) {
      let hitResult = this.$parent.paper.project.hitTest(
        event.point,
        this.hitOptions
      );

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
        let location = hitResult.location;
        this.segment = path.insert(location.index + 1, event.point);
      } else if (event.item.className == "CompoundPath") {
        this.initPoint = event.point;
        this.moveObject = event.item;
        paperObject = event.item;
      }
      this.isBbox = this.checkBbox(paperObject);
      if (this.point != null) {
        this.edit.canMove = this.point.contains(event.point);
      } else {
        this.edit.canMove = false;
      }
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

    onMouseUp(event) {
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
