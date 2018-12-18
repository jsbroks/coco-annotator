<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "CenterButton",
  mixins: [button],
  data() {
    return {
      name: "Center Image",
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
