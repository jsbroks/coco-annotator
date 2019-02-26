<template>
  <div class="col-md-3">
    <!-- Dataset Card -->
    <div class="card mb-4 box-shadow">
      <!-- Display Image -->
      <img
        @click="onImageClick"
        :src="imageUrl"
        class="card-img-top"
        @error="imageError = true"
        style="width: 100%; display: block;"
      />

      <!-- Card Body -->
      <div class="card-body">
        <span
          class="d-inline-block text-truncate"
          style="max-width: 85%; float: left"
        >
          <strong class="card-title">{{ dataset.name }}</strong>
        </span>

        <i
          class="card-text fa fa-ellipsis-v fa-x icon-more"
          :id="'dropdownDataset' + dataset.id"
          data-toggle="dropdown"
          aria-haspopup="true"
          aria-expanded="false"
          aria-hidden="true"
        />

        <br />

        <div>
          <div v-if="dataset.numberImages > 0">
            {{ dataset.numberAnnotated }} of {{ dataset.numberImages }} images
            annotated.
            <div class="progress">
              <div
                class="progress-bar"
                role="progressbar"
                :style="{ width: percent + '%' }"
              ></div>
            </div>
          </div>

          <p v-else>No images in dataset.</p>
          <span
            v-for="(category, index) in listCategories"
            :key="index"
            class="badge badge-pill badge-primary category-badge"
            :style="{ 'background-color': category.color }"
          >
            {{ category.name }}
          </span>
        </div>

        <div
          class="dropdown-menu"
          :aria-labelledby="'dropdownDataset' + dataset.id"
        >
          <button
            class="dropdown-item"
            data-toggle="modal"
            :data-target="'#datasetEdit' + dataset.id"
          >
            Edit
          </button>
          <button
            v-if="dataset.permissions.owner"
            class="dropdown-item"
            data-toggle="modal"
            :data-target="'#datasetShare' + dataset.id"
          >
            Share
          </button>
          <button
            class="dropdown-item"
            @click="onCocoDownloadClick"
            v-show="dataset.permissions.download"
          >
            Download COCO
          </button>
          <hr v-show="dataset.permissions.delete" />
          <button
            class="dropdown-item delete"
            v-show="dataset.permissions.delete"
            @click="onDeleteClick"
          >
            Delete
          </button>
        </div>
      </div>

      <div
        v-show="$store.getters['user/loginEnabled']"
        class="card-footer text-muted"
      >
        Created by {{ dataset.owner }}
      </div>
    </div>

    <!-- Edit Dataset -->
    <div class="modal fade" role="dialog" :id="'datasetEdit' + dataset.id">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ dataset.name }}</h5>
            <button
              type="button"
              class="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div class="form-group">
                <label>Default Categories</label>
                <TagsInput
                  v-model="selectedCategories"
                  element-id="changeDataset"
                  :existing-tags="categoryTags"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                />
              </div>

              <Metadata
                :metadata="defaultMetadata"
                title="Default Annotation Metadata"
                key-name="Default Key"
                value-name="Default Value"
                ref="defaultAnnotation"
              />
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="onSave"
              data-dismiss="modal"
            >
              Save
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Share Dataset -->
    <div class="modal fade" role="dialog" :id="'datasetShare' + dataset.id">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ dataset.name }}</h5>
            <button
              type="button"
              class="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div class="form-group">
                <label>Users shared with</label>
                <TagsInput
                  v-model="sharedUsers"
                  element-id="usersList"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                  placeholder="Add usernames"
                />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="onShare"
              data-dismiss="modal"
            >
              Save
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import Metadata from "@/components/Metadata";

import TagsInput from "@/components/TagsInput";

import { mapMutations } from "vuex";

export default {
  name: "DatasetCard",
  components: { Metadata, TagsInput },
  props: {
    dataset: {
      type: Object,
      required: true
    },
    categories: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      imageError: false,
      selectedCategories: [],
      defaultMetadata: this.dataset.default_annotation_metadata,
      noImageUrl: require("@/assets/no-image.png"),
      notFoundImageUrl: require("@/assets/404-image.png"),
      sharedUsers: this.dataset.users
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    onImageClick() {
      let identifier = this.dataset.id;
      this.$router.push({ name: "dataset", params: { identifier } });
    },
    onShare() {
      axios
        .post("/api/dataset/" + this.dataset.id + "/share", {
          users: this.sharedUsers
        })
        .then(() => {
          this.$parent.updatePage();
        });
    },
    onCocoDownloadClick() {
      let process = "Generating COCO for " + this.dataset.name;
      this.addProcess(process);

      axios
        .get("/api/dataset/" + this.dataset.id + "/coco")
        .then(reponse => {
          let dataStr =
            "data:text/json;charset=utf-8," +
            encodeURIComponent(JSON.stringify(reponse.data));

          this.downloadURI(dataStr, this.dataset.name + ".json");
        })
        .finally(() => this.removeProcess(process));
    },
    onDeleteClick() {
      axios.delete("/api/dataset/" + this.dataset.id).then(() => {
        this.$parent.updatePage();
      });
    },
    onSave() {
      this.dataset.categories = this.selectedCategories;

      axios
        .post("/api/dataset/" + this.dataset.id, {
          categories: this.selectedCategories,
          default_annotation_metadata: this.$refs.defaultAnnotation.export()
        })
        .then(() => {
          this.$parent.updatePage();
        });
    },
    downloadURI(uri, exportName) {
      let link = document.createElement("a");
      link.href = uri;
      link.download = exportName;
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
    createSelectedCategories() {
      let tagValues = Array.from([]);
      this.listCategories.forEach(category => {
        tagValues.push(category.name);
      });
      this.selectedCategories = tagValues;
    }
  },
  computed: {
    percent() {
      return 100 * (this.dataset.numberAnnotated / this.dataset.numberImages);
    },
    imageUrl() {
      if (this.imageError) {
        return this.notFoundImageUrl;
      }
      if (this.dataset.numberImages > 0) {
        return "/api/image/" + this.dataset.first_image_id + "?width=250";
      }

      return this.noImageUrl;
    },
    listCategories() {
      let list = [];
      if (!this.dataset.hasOwnProperty("categories")) return [];
      if (this.dataset.categories.length === 0) return [];

      this.dataset.categories.forEach(category => {
        let elements = this.categories.filter(
          element => element.id === category
        );

        if (elements.length === 1) {
          list.push(elements[0]);
        }
      });

      return list;
    },
    categoryTags() {
      let tags = {};
      this.categories.forEach(category => {
        tags[category.name] = category.name;
      });

      return tags;
    },
    user() {
      return this.$store.state.user.user;
    }
  },
  mounted() {
    this.createSelectedCategories();
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

.category-badge {
  float: left;
  margin: 0 2px 5px 0;
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

.progress {
  margin: 0 5px 7px 5px;
  height: 5px;
}
.card-footer {
  padding: 2px;
  font-size: 11px;
}

.delete {
  color: darkred;
}
</style>
