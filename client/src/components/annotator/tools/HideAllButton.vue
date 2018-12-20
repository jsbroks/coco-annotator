<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "HideAllButton",
  mixins: [button],
  data() {
    return {
      name: "Hide All",
      icon: "fa-eye-slash"
    };
  },
  methods: {
    execute() {
      this.$parent.hideAll();
    }
  }
};
</script>
