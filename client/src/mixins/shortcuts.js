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
          name: "Move Up Annotations"
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
          default: ["backspace"],
          name: "Delete Current Annotation",
          function: () => {
            if (this.currentAnnotation) {
              let currentKeypoint = this.currentAnnotation.currentKeypoint;
              if (currentKeypoint) {
                this.currentAnnotation.keypoints.deleteKeypoint(
                  currentKeypoint
                );
                this.currentAnnotation.tagRecomputeCounter++;
                this.currentAnnotation.currentKeypoint = null;
              } else {
                this.currentAnnotation.deleteAnnotation();
              }
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
          default: ["r"],
          name: "BBox Tool",
          function: () => {
            if (!this.$refs.polygon.isDisabled) this.activeTool = "BBox";
          }
        },
        {
          default: ["n"],
          name: "Next Image",
          function: this.nextImage
        },
        {
          default: ["p"],
          name: "Previous Image",
          function: this.previousImage
        },
        {
          default: ["v"],
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
          default: ["k"],
          name: "Keypoints Tool",
          function: () => {
            if (!this.$refs.magicwand.isDisabled) this.activeTool = "Keypoints";
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
          title: "BBox Tool Shortcuts",
          default: ["escape"],
          name: "Remove Current BBox",
          function: this.$refs.bbox.deletePolygon
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
