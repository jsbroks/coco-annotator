<script>
import button from "@/mixins/toolBar/button";

export default {
  name: "DownloadBinMaskButton",
  mixins: [button],
  props: {
    image: {
      type: Object,
      required: true
    },
    annotation_id:{
      type: Number,
      required: true
    }
  },
  data() {
    return {
      name: "Download Binary Mask",
      icon: "fa-image"
    };
  },
  methods: {
    download() {
      if (this.annotation_id == -1) alert("Please select an annotation !");
      let uri = "/api/image/binmask/" + this.image.id + "/" + this.annotation_id + "?asAttachment=true";
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
      this.$parent.save(this.download);
    }
  }
};
</script>
