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
    nextId: {
      type: Number,
      default: null
    },
    previousId: {
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
      let process = "Copying annotations from " + this.fromId;
      this.addProcess();

      axios
        .put(
          "/api/image/copy/" + this.fromId + "/" + this.imageId + "/annotations"
        )
        .then(() => {
          this.removeProcess(process);
          this.$parent.save(() => this.$parent.getData());
        })
        .catch(error => {
          this.axiosReqestError(
            "Copying Annotations",
            error.response.data.message
          );
          this.removeProcess(process);
        });
    }
  },
  computed: {
    validImageId() {
      let errorMsg = "Enter a valid image ID";

      if (this.fromId === "") return errorMsg;
      if (isNaN(this.fromId)) return errorMsg;
      if (this.fromId.trim() !== this.fromId) return errorMsg;

      return "";
    }
  },
  created() {}
};
</script>
