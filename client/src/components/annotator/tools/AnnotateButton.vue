<script>
import toastrs from "@/mixins/toastrs";
import button from "@/mixins/toolBar/button";
import axios from "axios";

export default {
  name: "AnnotateButton",
  mixins: [button, toastrs],
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
      disabled: true,
      loading: false
    };
  },
  methods: {
    execute() {
      if (!this.validUrl) return;

      let canvas = this.$parent.image.raster.canvas;

      let data = new FormData();
      canvas.toBlob(blob => {
        data.append("image", blob);
        this.loading = true;

        axios
          .post(this.annotateUrl, data, {
            headers: {
              "Content-Type": "multipart/form-data"
            }
          })
          .then(response => {
            let coco = response.data.coco || {};

            let images = coco.images || [];
            let categories = coco.categories || [];
            let annotations = coco.annotations || [];

            if (
              images.length == 0 ||
              categories.length == 0 ||
              annotations.length == 0
            ) {
              // Error
              return;
            }
            // Index categoires
            let indexedCategories = {};
            categories.forEach(category => {
              indexedCategories[category.id] = category;
            });

            annotations.forEach(annotation => {
              let keypoints = annotation.keypoints || [];
              let segmentation = annotation.segmentation || [];
              let category = indexedCategories[annotation.category_id];
              let isbbox = annotation.isbbox || false;

              this.$parent.addAnnotation(
                category.name,
                segmentation,
                keypoints,
                isbbox=isbbox
              );
            });
          })
          .catch(() => {
            this.axiosReqestError("Annotator", "Could not read data from URL");
          })
          .finally(() => (this.loading = false));
      });
    }
  },
  computed: {
    name() {
      if (!this.validUrl) return "Annotate url is invalid";
      return "Annotate Image";
    },
    validUrl() {
      if (typeof this.annotateUrl === "number") return false;
      return this.annotateUrl.length > 2;
    }
  },
  watch: {
    loading() {
      this.icon = this.loading ? "fa-spinner fa-spin" : "fa-cloud-download";
    },
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
