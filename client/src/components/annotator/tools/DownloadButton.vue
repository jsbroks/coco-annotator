<script>
import button from "@/mixins/toolBar/button";
import axios from "axios";

export default {
  name: "DownloadButton",
  mixins: [button],
  props: {
    image: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      name: "Download COCO",
      icon: "fa-download",
      include: {
        image: true,
        coco: true
      }
    };
  },
  methods: {
    downloadURI(uri, exportName) {
      let link = document.createElement("a");
      link.href = uri;
      link.download = exportName;
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
    download() {
      if (this.include.image) {
        let url = "/api/image/" + this.image.id + "?asAttachment=true";
        this.downloadURI(url, this.image.filename);
      }
      if (this.include.coco) {
        let url = "/api/image/" + this.image.id + "/coco";

        axios.get(url).then(response => {
          let dataStr =
            "data:text/json;charset=utf-8," +
            encodeURIComponent(JSON.stringify(response.data));
          let filename = this.image.filename.replace(/\.[^/.]+$/, "") + ".json";
          this.downloadURI(dataStr, filename);
        });
      }
    },
    // Download function
    execute() {
      this.$parent.save(this.download);
    }
  }
};
</script>
