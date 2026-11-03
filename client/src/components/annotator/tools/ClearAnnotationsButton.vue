<script>
import button from "@/mixins/toolBar/button";

// Deletes every annotation of the current image (restorable from Undo).
export default {
  name: "ClearAnnotationsButton",
  mixins: [button],
  data() {
    return {
      name: "Clear Annotations",
      icon: "fa-times-circle"
    };
  },
  methods: {
    execute() {
      this.$parent.clearAnnotations();
    }
  }
};
</script>
