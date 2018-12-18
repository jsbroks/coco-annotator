<script>
import button from "@/mixins/toolBar/button";
import axios from "axios";

import { mapMutations } from "vuex";

export default {
  name: "DeleteButton",
  mixins: [button],
  data() {
    return {
      name: "Undo Last Action",
      icon: "fa-undo"
    };
  },
  methods: {
    ...mapMutations(["undo"]),
    execute() {
      this.undo();
    }
  }
};
</script>
