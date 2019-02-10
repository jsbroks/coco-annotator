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
    "<div><i v-tooltip.right='tooltip' class='fa fa-x' :class='icon' :style='{ color: iconColor }' @click='click'></i><br></div>",
  data() {
    return {
      tool: null,
      enabled: false,
      cursor: "default",
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
      if (this.isDisabled) return;

      this.$emit("update", this.name);
    },
    setPreferences() {}
  },
  computed: {
    isActive() {
      if (this.selected == this.name) {
        this.$emit("setcursor", this.cursor);
        return true;
      }
      return false;
    },
    iconColor() {
      if (this.isDisabled) return this.color.disabled;

      if (this.isToggled) return this.color.toggle;
      if (this.isActive) return this.color.active;

      return this.color.enabled;
    },
    isDisabled() {
      return false;
    },
    tooltip() {
      if (this.isDisabled) {
        return this.name + " (select an annotation to activate tool)";
      }
      return this.name + " Tool";
    }
  },
  watch: {
    isActive(active) {
      if (active) {
        this.tool.activate();
      }
    },
    isDisabled(disabled) {
      if (disabled && this.isActive) {
        this.$emit("update", "Select");
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
