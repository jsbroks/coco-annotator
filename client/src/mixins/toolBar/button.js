import { renderToolIcon } from "./render";
import { tr } from "@/i18n";

export default {
  render() {
    return renderToolIcon(this, this.buttonLabel !== undefined ? this.buttonLabel : tr("toolbar", this.name));
  },
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
