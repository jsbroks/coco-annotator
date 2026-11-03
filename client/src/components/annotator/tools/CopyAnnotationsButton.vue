<template>
  <div>
    <i
      v-tooltip.right="$tr('toolbar', name)"
      class="fa fa-x fa-clone"
      style="color: white"
      data-bs-toggle="modal"
      data-bs-target="#copyAnnotations"
    ></i>
    <br />
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
            <h5 class="modal-title" id="copyAnnotationsLabel">
              {{ $t('copyAnnotationsButton.copyAnnotationsFromImage') }}
            </h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form novalidate="true">
              <button
                type="button"
                class="btn btn-sm btn-light"
                style="float: left"
                @click="fromId = previous.toString()"
              >
                <i class="fa fa-arrow-left"></i> {{ $t('copyAnnotationsButton.previousImage') }}
              </button>
              <button
                type="button"
                class="btn btn-sm btn-light"
                style="float: right; margin-left: 8px"
                @click="fromId = next.toString()"
              >
                {{ $t('copyAnnotationsButton.nextImage') }} <i class="fa fa-arrow-right"></i>
              </button>

              <div class="mb-3">
                <label>{{ $t('copyAnnotationsButton.imageId') }}</label>
                <input
                  v-model="fromId"
                  :class="{
                    'form-control': true,
                    'is-invalid': validImageId.length !== 0
                  }"
                  :placeholder="$t('copyAnnotationsButton.enterAnImageId')"
                  required
                />
                <div class="invalid-feedback">{{ validImageId }}</div>
              </div>

              <div class="mb-3">
                <label>{{ $t('copyAnnotationsButton.copyOnlySelectedCategories') }}</label>
                <TagsInput
                  v-model:value="selectedCategories"
                  element-id="categoriesToCopy"
                  :existing-tags="categoryTags"
                  :typeahead="true"
                  :only-existing-tags="true"
                  :typeahead-activation-threshold="0"
                />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="close()">
              {{ $t('copyAnnotationsButton.close') }}
            </button>
            <button
              type="button"
              class="btn btn-primary"
              @click="copyAnnotations()"
            >
              {{ $t('copyAnnotationsButton.copy') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { hideModal } from "@/libs/modal";
import axios from "axios";

import { mapMutations } from "vuex";
import toastrs from "@/mixins/toastrs";
import TagsInput from "@/components/TagsInput.vue";


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
    },
    categories: {
      type: Array,
      required: true
    }
  },
  components: { TagsInput },
  mixins: [toastrs],
  data() {
    return {
      name: "Copy Annotations",
      fromId: "",
      selectedCategories: [],
      visible: false
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess", "resetUndo"]),
    close() {
      hideModal("#copyAnnotations");
    },
    copyAnnotations() {
      if (this.validImageId !== "") return;
      this.close();

      let process = "Copying annotations from " + this.fromId;
      let categories = [];
      this.selectedCategories.forEach(category =>
        categories.push(parseInt(category))
      );

      this.$parent.save(() => {
        this.addProcess(process);
        axios
          .post(
            "/api/image/copy/" +
              this.fromId +
              "/" +
              this.imageId +
              "/annotations",
            {
              category_ids: categories
            }
          )
          .then(() => {
            this.$parent.getData();
          })
          .catch(error => {
            this.axiosReqestError(
              "Copying Annotations",
              error.response.data.message
            );
          })
          .finally(() => this.removeProcess(process));
      });
    }
  },
  watch: {
    categories: {
      immediate: true,
      handler(newCategories) {
        let tags = [];
        newCategories.forEach(category => {
          tags.push(category.id.toString());
        });
        this.selectedCategories = tags;
      }
    }
  },
  computed: {
    validImageId() {
      let errorMsg = this.$t("copy.invalidId");

      if (this.fromId == null) return errorMsg;
      if (this.fromId === "") return errorMsg;
      if (isNaN(this.fromId)) return this.$t("copy.notNumber");
      if (this.fromId.trim() !== this.fromId) return this.$t("copy.notNumber");
      if (this.fromId === this.imageId)
        return this.$t("copy.sameImage");

      return "";
    },
    categoryTags() {
      let tags = {};
      this.categories.forEach(category => {
        tags[category.id] = category.name;
      });

      return tags;
    }
  }
};
</script>

<style scoped>
.btn-light {
  margin-bottom: 4px;
}
</style>
