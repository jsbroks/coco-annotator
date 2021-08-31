<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "DownloadSemanticSegButton",
  mixins: [button],
  props: {
    image: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      name: "Download Semantic Segmentation Mask",
      icon: "fa-image"
    };
  },
  methods: {
    download() {
      let uri = "/api/image/semanticSegmentation/" + this.image.id + "?asAttachment=true";
      //download URI
      let link = document.createElement("a");
      link.href = uri;
      link.download = this.image.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
    // Download function
    execute() {
      //this.$parent.save(this.download);
      this.download();
    }
  }
};
</script>
