import paper from "paper";

export default {
  model: {
    prop: "selected",
    event: "update"
  },
  props: {
    selected: {
      type: String,
      required: true
    }
  },
  template:
    "<div><i class='fa fa-x' :class='icon' :style='{ color: iconColor }' @click='click'></i><br></div>",
  data() {
    return {
      tool: null,
      enabled: false,
      color: {
        enabled: "white",
        active: "#2ecc71",
        disabled: "gray",
        toggle: "red"
      }
    };
  },
  methods: {
    onMouseMove() {},
    onMouseDown() {},
    onMouseDrag() {},
    onMouseUp() {},
    click() {
      this.update();
    },
    update() {
      this.$emit("update", this.name);
    }
  },
  computed: {
    isActive() {
      return this.selected === this.name;
    },
    iconColor() {
      if (this.isToggled) return this.color.toggle;
      if (this.isActive) return this.color.active;
      if (this.isDisabled) return this.color.disabled;

      return this.color.enabled;
    }
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
      }
    }
  },
  mounted() {
    this.tool = new paper.Tool();

    this.tool.onMouseDown = this.onMouseDown;
    this.tool.onMouseDrag = this.onMouseDrag;
    this.tool.onMouseMove = this.onMouseMove;
    this.tool.onMouseUp = this.onMouseUp;
  }
};
