<template>
  <div>
    <i v-tooltip.right="name" class="fa fa-x fa-clone" style="color: white" data-toggle="modal" data-target="#copy_annotations"></i>

    <br>
    <!-- Modal -->
    <div class="modal fade" id="copy_annotations" tabindex="-1" role="dialog" aria-labelledby="copyAnnotationsLabel" aria-hidden="true">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="copyAnnotationsLabel">Copy Annotations From Image</h5>
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form novalidate="true">
              <div class="form-group">
                <label>Image ID</label>
                <input v-model="copyFrom.imageId" 
                  :class="{'form-control': true, 'is-invalid': validImageId.length !== 0}"
                  placeholder="Enter a valid image ID" required>
                <div class="invalid-feedback">
                  {{ validImageId }}
                </div>
              </div>
            </form>

          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" @click="copyAnnotations()">Copy</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "CopyAnnotationsButton",
  components: {},
  props: {},
  data() {
    return {
      name: "Copy Annotations",
      copyFrom: {
        imageId: "",
        validatedImageId: "invalid"
      },
      imageIds: []
    };
  },
  methods: {
    copyAnnotations() {
      if (this.copyFrom.imageId === "" || isNaN(this.copyFrom.imageId)) {
        return;
      }
      let imageId = parseInt(this.copyFrom.imageId);
      if (!this.imageIds.includes(imageId)) {
        return;
      }
      this.$emit("close");
      return this.$parent.copyAnnotationsFrom(this.copyFrom.validatedImageId);
    }
  },
  computed: {
    validImageId() {
      let errorMsg = "Enter a valid image ID";
      if (this.copyFrom.imageId === "") {
        return errorMsg;
      } else if (isNaN(this.copyFrom.imageId)) {
        return errorMsg;
      } else if (!this.imageIds.includes(parseInt(this.copyFrom.imageId))) {
        return errorMsg;
      }
      return "";
    }
  },
  created() {
    axios
      .get("/api/image/?fields=id")
      .then(response => {
        this.imageIds = response.data.map(image => image.id);
      })
      .catch(error => {
        this.axiosReqestError("Loading Dataset", error.response.data.message);
      });
  }
};
</script>

<style scoped>
.subtitle {
  margin: 0;
  font-size: 10px;
}
</style>
