<script>
import button from "@/mixins/toolBar/button";
import axios from "axios";

export default {
  name: "AnnotateButton",
  mixins: [button],
  props: {
    annotateUrl: {
      required: true,
      type: [String, Number]
    }
  },
  data() {
    return {
      icon: "fa-cloud-download",
      cursor: "copy",
      iconColor: "white",
      disabled: true
    };
  },
  methods: {
    execute() {
      if (!this.validUrl) return;

      return axios.get(this.annotateUrl).then(response => {
        console.log(response.data);
        let coco = response.data.coco || {};

        let images = coco.images;
        let categories = coco.categories;
        let annotations = coco.annotations;

        if (images || categories || annotations) {
          // Error
          return;
        }

        // Index image
        
        // Index categories

        // Add images

      });
    }
  },
  computed: {
    name() {
      if (!this.validUrl) return "Annotate url is invalid";
      return "Annotate Image";
    },
    validUrl() {
      if (typeof this.annotateUrl === 'number') return false;
      return this.annotateUrl.length > 2;
    }
  },
  watch: {
    validUrl() {
      this.disabled = !this.validUrl;
    },
    disabled() {
      this.iconColor = this.disabled ? this.color.disabled : this.color.enabled;
    }
  },
  created() {
    this.iconColor = this.color.disabled;
    this.disabled = !this.validUrl;
  }
};
</script>
