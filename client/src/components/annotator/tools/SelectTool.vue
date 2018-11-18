<script>
//import paper from "paper";
import tool from "@/mixins/tool";

export default {
  name: "SelectTool",
  mixins: [tool],
  data() {
    return {
      icon: "fa-hand-pointer-o",
      name: "Select"
    };
  },
  methods: {
    onMouseDown() {}
  }
};
</script>
