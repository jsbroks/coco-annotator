<script>
import button from "@/mixins/toolBar/button";

// Opens the "run your model on this image" dialog (see ModelRunModal).
export default {
  name: "ModelButton",
  mixins: [button],
  emits: ["open"],
  data() {
    return {
      name: "Run Model",
      icon: "fa-rocket"
    };
  },
  methods: {
    execute() {
      this.$emit("open");
    }
  }
};
</script>
