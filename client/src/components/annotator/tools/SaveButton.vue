<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "SaveButton",
  mixins: [button],
  data() {
    return {
      name: "Save",
      icon: "fa-save"
    };
  },
  methods: {
    execute() {
      this.$parent.save();
    }
  }
};
</script>
