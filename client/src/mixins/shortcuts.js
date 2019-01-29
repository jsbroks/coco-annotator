import { mapMutations } from "vuex";

export default {
  data() {
    return {
      commands: []
    };
  },
  methods: {
    ...mapMutations(["undo"]),
    annotator() {
      return [
        {
          default: ["arrowup"],
          function: this.moveUp,
          name: "Move Up Annotaitons"
        },
        {
          default: ["arrowdown"],
          function: this.moveDown,
          name: "Move Down Annotations"
        },
        {
          default: ["arrowright"],
          function: this.stepIn,
          name: "Expand Category"
        },
        {
          default: ["arrowleft"],
          function: this.stepOut,
          name: "Collapse Category"
        },
        {
          default: ["space"],
          name: "New Annotation",
          function: () => {
            if (this.currentCategory) {
              this.currentCategory.createAnnotation();
            }
          }
        },
        {
          default: ["delete"],
          name: "Delete Current Annotation",
          function: () => {
            if (this.currentAnnotation) {
              this.currentAnnotation.deleteAnnotation();
            }
          }
        },
        {
          default: ["control", "z"],
          name: "Undo Last Action",
          function: this.undo
        },
        {
          default: ["s"],
          name: "Select Tool",
          function: () => {
            this.activeTool = "Select";
          }
        },
        {
          default: ["p"],
          name: "Polygon Tool",
          function: () => {
            if (!this.$refs.polygon.isDisabled) this.activeTool = "Polygon";
          }
        },
        {
          default: ["w"],
          name: "Magic Wand Tool",
          function: () => {
            if (!this.$refs.magicwand.isDisabled)
              this.activeTool = "Magic Wand";
          }
        },
        {
          default: ["b"],
          name: "Brush Tool",
          function: () => {
            if (!this.$refs.brush.isDisabled) this.activeTool = "Brush";
          }
        },
        {
          default: ["e"],
          name: "Eraser Tool",
          function: () => {
            if (!this.$refs.eraser.isDisabled) this.activeTool = "Eraser";
          }
        },
        {
          default: ["c"],
          name: "Center Image",
          function: this.fit
        },
        {
          default: ["control", "s"],
          name: "Save",
          function: this.save
        },
        {
          title: "Polygon Tool Shortcuts",
          default: ["escape"],
          name: "Remove Current Polygon",
          function: this.$refs.polygon.deletePolygon
        },
        {
          title: "Eraser Tool Shortcuts",
          default: ["["],
          name: "Increase Radius",
          function: this.$refs.eraser.increaseRadius
        },
        {
          default: ["]"],
          name: "Decrease Radius",
          function: this.$refs.eraser.decreaseRadius
        },
        {
          title: "Brush Tool Shortcuts",
          default: ["["],
          name: "Increase Radius",
          function: this.$refs.brush.increaseRadius
        },
        {
          default: ["]"],
          name: "Decrease Radius",
          function: this.$refs.brush.decreaseRadius
        },
        {
          title: "Magic Tool Shortcuts",
          default: ["shift", "click"],
          name: "Subtract Selection",
          readonly: true
        }
      ];
    }
  },
  mounted() {
    if (this.$route.name === "annotate") {
      this.commands = this.annotator();
    }
  }
};
