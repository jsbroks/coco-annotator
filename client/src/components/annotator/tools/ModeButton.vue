<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "ModeButton",
  emits: ["update:mode"],
  mixins: [button],
  props: {
    mode: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      name: "Mode: " + this.mode
    };
  },
  watch: {
    mode() {
      this.name = "Mode: " + this.mode;
    }
  },
  computed: {
    buttonLabel() {
      return this.$t("toolbar.modeLabel", { mode: this.$t("toolbar.mode." + this.mode) });
    },
    icon() {
      if (this.mode == "segment") return "fa-pencil-square-o";
      if (this.mode == "label") return "fa-tags";
      return "";
    }
  },
  methods: {
    next() {
      if (this.mode == "segment") return "label";
      return "segment";
    },
    execute() {
      this.$emit("update:mode", this.next());
    }
  }
};
</script>
