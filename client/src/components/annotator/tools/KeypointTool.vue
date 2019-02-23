<script>
import tool from "@/mixins/toolBar/tool";

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
      return {};
    },
    onMouseDown(event) {
      this.$parent.currentAnnotation.addKeypoint(event.point);
    }
  },
  computed: {
    isDisabled() {
      return this.$parent.current.annotation === -1;
    }
  },
  watch: {},
  created() {},
  mounted() {}
};
</script>
