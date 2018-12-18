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
      segment: null,
      scaleFactor: 15,
      hover: {
        showText: true,
        text: null,
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
        tolerance: 2
      }
    };
  },
  methods: {
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

      return string.replace(/\n/g, " \n ").slice(0, -2);
    },
    hoverText() {
      if (!this.hover.showText) return;

      if (this.hover.category == null) return;
      if (this.hover.annotation == null) return;

      let position = this.hover.position.add(this.hover.textShift, 0);

      if (
        this.hover.text == null ||
        this.hover.annotationText != this.hover.anntoation
      ) {
        let content = this.generateStringFromMetadata();

        if (this.hover.text != null) {
          this.hover.text.remove();
          this.hover.box.remove();
        }
        this.hover.text = new paper.PointText(position);
        this.hover.text.justification = "left";
        this.hover.text.fillColor = "black";
        this.hover.text.content = content;

        this.hover.text.fontSize = this.hover.fontSize;

        this.hover.box = new paper.Path.Rectangle(
          this.hover.text.bounds,
          this.hover.rounded
        );

        this.hover.box.fillColor = "white";
        this.hover.box.strokeColor = "white";
        this.hover.box.opacity = 0.5;

        this.hover.box.insertAbove(this.rect);
        this.hover.annotationText = this.hover.annotation;
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
        this.hitResult
      );

      if (!hitResult) return;

      if (event.modifiers.shift) {
        if (hitResult.type === "segment") {
          hitResult.segment.remove();
        }
        return;
      }

      this.path = hitResult.item;

      if (hitResult.type === "segment") {
        this.segment = hitResult.segment;
      } else if (hitResult.type === "stroke") {
        let location = hitResult.location;
        this.segment = this.path.insert(location.index + 1, event.point);
      }
    },
    onMouseDrag(event) {
      if (this.segment) {
        this.segment.point = event.point;
      }
    },
    onMouseMove(event) {
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
        this.hover.annotation = -1;

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
    scale(newScale) {
      this.hover.rounded = newScale * 5;
      this.hover.textShift = newScale * 40;
      this.hover.fontSize = newScale * this.scaleFactor;

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
    }
  }
};
</script>
