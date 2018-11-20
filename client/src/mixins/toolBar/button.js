export default {
  template:
    "<div><i class='fa fa-x' :class='icon' :style='{ color: iconColor }' @click='click'></i><br></div>",
  data() {
    return {
      icon: "",
      color: {
        enabled: "white",
        active: "#2ecc71"
      },
      iconColor: "",
      delay: 400
    };
  },
  methods: {
    click() {
      this.toggleAnimation();
      this.execute();
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
