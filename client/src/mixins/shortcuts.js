export default {
  data() {
    return {
      commands: []
    };
  },
  methods: {
    annotator() {
      return [
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
            this.activeTool = "Polygon";
          }
        },
        {
          default: ["w"],
          name: "Magic Wand Tool",
          function: () => {
            this.activeTool = "Magic Wand";
          }
        },
        {
          default: ["b"],
          name: "Brush Tool",
          function: () => {
            this.activeTool = "Brush";
          }
        },
        {
          default: ["e"],
          name: "Eraser Tool",
          function: () => {
            this.activeTool = "Eraser";
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
