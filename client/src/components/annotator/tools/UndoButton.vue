<script>
import button from "@/mixins/toolBar/button";

import { mapMutations } from "vuex";

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
    ...mapMutations(["undo"]),
    execute() {
      this.undo();
    }
  },
  computed: {
    buttonLabel() {
      return this.name;
    },
    name() {
      let length = this.undoList.length;
      if (length == 0) {
        return this.$t("toolbar.nothingToUndo");
      }

      let last = this.undoList[length - 1];
      return this.$t("toolbar.undoLast", { name: last.name, action: this.$tr("undoAction", last.action) });
    },
    undoList() {
      return this.$store.state.undo;
    }
  },
  watch: {
    undoList: {
      deep: true,
      handler() {
        this.disabled = this.undoList.length === 0;
        this.iconColor = this.disabled ? this.color.disabled : this.color.enabled;
      }
    }
  },
  created() {
    this.iconColor = this.color.disabled;
  }
};
</script>
