<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "CenterButton",
  mixins: [button],
  data() {
    return {
      icon: "fa-align-center"
    };
  },
  methods: {
    execute() {
      this.$parent.fit();
    }
  }
};
</script>
