<template>
  <div class="col-md-3">
    <div class="card mb-4 box-shadow">
      <img 
        class="card-img-top" 
        @click="openAnnotator" 
        style="width: 100%; display: block"
        :src="imageUrl"
      >
      <div class="card-body">
             
        <span 
          class="d-inline-block text-truncate" 
          style="max-width: 85%; float: left"
        >
          <strong class="card-title">{{ image.id }}. {{ image.file_name }}</strong>
        </span>
                     
        <i 
          class="card-text fa fa-ellipsis-v fa-x icon-more" 
          :id="'dropdownImage' + image.id"
          data-toggle="dropdown" 
          aria-haspopup="true" 
          aria-expanded="false" 
          aria-hidden="true"
        /> 
        <br>      
        <div>                
          <p v-if="image.annotations > 0">
            {{ image.annotations }} annotations.
          </p>
          <p v-else>Image has no annotations</p>
        </div>

        <div 
          class="dropdown-menu" 
          :aria-labelledby="'dropdownImage' + image.id"
        >
          <a 
            class="dropdown-item" 
            @click="onDeleteClick"
          >Delete</a>
          <a 
            class="dropdown-item" 
            @click="openAnnotator"
          >Annotate</a>
          <a 
            class="dropdown-item" 
            @click="onDownloadClick"
          >Download Image & COCO</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "ImageCard",
  props: {
    image: {
      type: Object,
      required: true
    }
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
    openAnnotator() {
      this.$router.push({
        name: "annotate",
        params: { identifier: this.image.id }
      });
    },
    onDownloadClick() {
      this.downloadURI(
        "/api/image/" + this.image.id + "?asAttachment=true",
        this.image.file_name
      );

      axios.get("/api/image/" + this.image.id + "/coco").then(reponse => {
        let dataStr =
          "data:text/json;charset=utf-8," +
          encodeURIComponent(JSON.stringify(reponse.data));
        this.downloadURI(
          dataStr,
          this.image.file_name.replace(/\.[^/.]+$/, "") + ".json"
        );
      });
    },
    onDeleteClick() {
      axios.delete("/api/image/" + this.image.id).then(() => {
        this.$parent.updatePage();
      });
    }
  },
  computed: {
    imageUrl: function() {
      return "/api/image/" + this.image.id + "?width=250";
    }
  }
};
</script>

<style scoped>
.card-img-overlay {
  padding: 0 10px 0 0;
}

.card-body {
  padding: 10px 10px 0 10px;
}

p {
  margin: 0;
  padding: 0 0 3px 0;
}

.list-group-item {
  height: 21px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}
.icon-more {
  width: 10%;
  margin: 3px 0;
  padding: 0;
  float: right;
  color: black;
}
</style>
