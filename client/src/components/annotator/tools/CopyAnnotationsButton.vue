<template>
  <div>
    <i
      v-tooltip.right="name"
      class="fa fa-x fa-clone"
      style="color: white"
      data-toggle="modal"
      data-target="#copyAnnotations"
    ></i>
    <br>
    <!-- Modal -->
    <div
      id="copyAnnotations"
      class="modal fade"
      tabindex="-1"
      role="dialog"
      ref="modal"
      aria-labelledby="copyAnnotationsLabel"
      aria-hidden="true"
    >
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
                <input
                  v-model="fromId"
                  :class="{'form-control': true, 'is-invalid': validImageId.length !== 0}"
                  placeholder="Enter an image ID"
                  required
                >
                <div class="invalid-feedback">{{ validImageId }}</div>
              </div>
              <button type="button" class="btn btn-sm btn-light" style="float: left" @click="fromId = previous.toString()">
                <i class="fa fa-arrow-left"></i> Previous Image
              </button>
              <button type="button" class="btn btn-sm btn-light" style="float: right" @click="fromId = next.toString()">
                Next Image <i class="fa fa-arrow-right"></i>
              </button>

            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="close()">Close</button>
            <button type="button" class="btn btn-primary" @click="copyAnnotations()">Copy</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import toastrs from "@/mixins/toastrs";
import JQuery from "jquery";
let $ = JQuery;

import { mapMutations } from "vuex";

export default {
  name: "CopyAnnotationsButton",
  props: {
    imageId: {
      type: Number,
      required: true
    },
    next: {
      type: Number,
      default: null
    },
    previous: {
      type: Number,
      default: null
    }
  },
  mixins: [toastrs],
  data() {
    return {
      name: "Copy Annotations",
      fromId: "",
      visible: false
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess", "resetUndo"]),
    close() {
      $("#copyAnnotations").modal("hide");
    },
    copyAnnotations() {
      if (this.validImageId !== "") return;
      this.close();

      let process = "Copying annotations from " + this.fromId;

      this.$parent.save(() => {
        this.addProcess(process);
        axios
          .put(
            "/api/image/copy/" +
              this.fromId +
              "/" +
              this.imageId +
              "/annotations"
          )
          .then(() => {
            this.removeProcess(process);
            this.$parent.getData();
          })
          .catch(error => {
            this.axiosReqestError(
              "Copying Annotations",
              error.response.data.message
            );
            this.removeProcess(process);
          });
      });
    }
  },
  computed: {
    validImageId() {
      let errorMsg = "Enter a valid image ID";

      if (this.fromId == null) return errorMsg;
      if (this.fromId === "") return errorMsg;
      if (isNaN(this.fromId)) return "Value must be a number";
      if (this.fromId.trim() !== this.fromId) return "Value must be a number";
      if (this.fromId === this.imageId)
        return "Sorry, you can not clone the same image";

      return "";
    }
  },
  created() {}
};
</script>
