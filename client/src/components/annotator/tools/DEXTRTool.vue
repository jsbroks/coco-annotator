<script>
import paper from "paper";
import tool from "@/mixins/toolBar/tool";

export default {
  name: "DEXTRTool",
  mixins: [tool],
  props: {
    scale: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      icon: "fa-crosshairs",
      name: "DEXTR",
      cursor: "crosshair"
    };
  },
  methods: {

  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation == -1;
    }
  },
  watch: {
    /**
     * Change width of stroke based on zoom of image
     */
    scale(newScale) {
        
    }
  },
  mounted() {}
};
</script>
