<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";
import UndoAction from "@/undo";

import { invertColor } from "@/libs/colors";
import { mapMutations } from "vuex";

export default {
  name: "KeypointTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    },
    settings: {
      type: [Object, null],
      default: null
    }
  },
  data() {
    return {
      icon: "fa-map-marker",
      name: "Keypoints",
      cursor: "cell"
    };
  },
  methods: {
    export() {
      return {
      };
    },
    setPreferences(pref) {
      
    },
    onMouseDrag(event) {

    },
    onMouseDown(event) {
      this.$parent.currentAnnotation.addKeypoint(event.point);
    },
    onMouseUp() {

    },
    onMouseMove(event) {

    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation === -1;
    }
  },
  watch: {
  },
  created() {},
  mounted() {
  }
};
</script>
