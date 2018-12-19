export default {
  template:
    "<div><i v-tooltip.right='name' class='fa fa-x' :class='icon' :style='{ color: iconColor }' @click='click'></i><br></div>",
  data() {
    return {
      color: {
        enabled: "white",
        active: "#2ecc71",
        disabled: "gray"
      },
      iconColor: "",
      delay: 400
    };
  },
  methods: {
    click() {
      if (!this.disabled) {
        this.toggleAnimation();
        this.execute();
      }
    },
    toggleAnimation() {
      this.iconColor = this.color.active;
      setTimeout(() => {
        this.iconColor = this.color.enabled;
      }, this.delay);
    }
  },
  created() {
    this.iconColor = this.color.enabled;
  }
};
