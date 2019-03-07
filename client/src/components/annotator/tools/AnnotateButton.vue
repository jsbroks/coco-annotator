<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "AnnotateButton",
  mixins: [button],
  props: {},
  data() {
    return {
      icon: "fa-cloud-upload",
      cursor: "copy",
      iconColor: "white",
      disabled: true
    };
  },
  methods: {
    execute() {
            
    }
  },
  computed: {
    name() {
      if (this.dis)
      return "Annotate Image";
    },
  },
  created() {
    this.iconColor = this.color.disabled;
  }
};
</script>
