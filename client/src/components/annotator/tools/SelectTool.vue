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
      hitOptions: {
        segments: true,
        stroke: true,
        fill: false,
        tolerance: 5,
        match: hit => {
          if (this.point == null) return true;
          if (
            hit.item instanceof paper.Path ||
            hit.item instanceof paper.CompoundPath
          ) {
            return !hit.item.hasOwnProperty("indicator");
          }
          return true;
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
    generateTitle() {
      let string = " ";
      if (this.hover.category && this.hover.annotation) {
        string += this.hover.category.category.name;
        string += ' : '
        string += this.hover.annotation.annotation.id;
        string += '\n'
      }
      return string.replace(/\n/g, " \n ").slice(0, -2);
    },
    generateStringFromMetadata() {
      let string = " ";
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

      if (this.$store.getters["user/loginEnabled"]) {
        let creator = this.hover.annotation.annotation.creator;
        if (creator != null) {
          string += "Created by " + creator + "\n";
        }
      }

      return string.replace(/\n/g, " \n ").slice(0, -2);
    },
    hoverText() {
      if (!this.hover.showText) return;

      if (this.hover.category == null) return;
      if (this.hover.annotation == null) return;

      let position = this.hover.position.add(this.hover.textShift, 0);

      if (
        this.hover.text == null ||
        this.hover.annotation.annotation.id !== this.hover.textId
      ) {
        if (this.hover.text !== null) {
          this.hover.text.remove();
          this.hover.box.remove();
        }

        this.hover.textId = this.hover.annotation.annotation.id;
        let content = this.generateTitle() + ' \n ' +
          this.generateStringFromMetadata();

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
      this.hover.text.bringToFront();
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

      if (hitResult.type === "segment") {
        this.segment = hitResult.segment;
      } else if (hitResult.type === "stroke") {
        let location = hitResult.location;
        this.segment = path.insert(location.index + 1, event.point);
      }

      if (this.point != null) {
        this.edit.canMove = this.point.contains(event.point);
      }
    },
    createPoint(point) {
      if (this.point != null) {
        this.point.remove();
      }

      this.point = new paper.Path.Circle(point, this.edit.indicatorSize);
      this.point.strokeColor = "white";
      this.point.strokeWidth = this.edit.indicatorWidth;
      this.point.indicator = true;
    },
    onMouseDrag(event) {
      if (this.segment) {
        if (!this.edit.canMove) return;
        this.createPoint(event.point);
        this.segment.point = event.point;
      }
    },
    onMouseMove(event) {
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
      if (
        event.item &&
        event.item.visible &&
        event.item.data.hasOwnProperty("categoryId") &&
        event.item.hasChildren()
      ) {
        let item = event.item;
        this.$parent.hover.category = item.data.categoryId;
        this.hover.category = this.$parent.getCategory(item.data.categoryId);

        if (this.hover.category == null) return;

        for (let i = 0; i < item.children.length; i++) {
          let child = item.children[i];

          if (
            child.visible &&
            child.contains(event.point) &&
            child.data.hasOwnProperty("annotationId")
          ) {
            this.hover.position = event.point;
            this.$parent.hover.annotation = child.data.annotationId;

            this.hover.annotation = this.hover.category.getAnnotation(
              child.data.annotationId
            );
            child.selected = true;

            this.hoverText();
            break;
          }
        }
      } else {
        this.hover.category = null;
        this.hover.annotation = null;

        if (this.hover.text != null) {
          this.hover.text.remove();
          this.hover.box.remove();
          this.hover.text = null;
          this.hover.box = null;
        }
      }
    }
  },
  watch: {
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
