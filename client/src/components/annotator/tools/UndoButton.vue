
<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "UndoButton",
  mixins: [button],
  data() {
    return {
      icon: "fa-undo",
      disabled: true
    };
  },
  methods: {
    execute() {
      this.undo();
    }
  },
  computed: {
    name() {
      let length = this.undoList.length;
      if (length == 0) {
        return "Nothing to undo";
      }

      let last = this.undoList[length - 1];
      return "Undo (Last Action: " + last.name + " " + last.action + ")";
    },
    undoList() {
      return this.$store.state.undo;
    }
  },
  watch: {
    undoList() {
      this.iconColor =
        this.undoList.length === 0 ? this.color.disabled : this.color.enabled;
    }
  },
  created() {
    this.iconColor = this.color.disabled;
  }
};
</script>

<style scoped>
</style>
>
