<template>
  <div class="col-sm-6 col-md-4 col-xl-3 col-xxl-2">
    <!-- Dataset Card -->
    <div class="card mb-4 box-shadow">
      <!-- Display Image (with the planned task in the corner) -->
      <div class="cover">
        <img
          @click="onImageClick"
          :src="imageUrl"
          class="card-img-top"
          @error="imageError = true"
          style="width: 100%; display: block;"
        />
        <span v-if="dataset.task" class="task-tag" :title="$t('datasetTask.label')">
          <i class="fa fa-fw" :class="TASK_ICONS[dataset.task]" :style="dataset.task === 'obb' ? { transform: 'rotate(-30deg)' } : null" />
          {{ $t('datasetTask.' + dataset.task + '.name') }}
        </span>
      </div>

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
          data-bs-toggle="dropdown"
          aria-haspopup="true"
          aria-expanded="false"
          aria-hidden="true"
        />

        <br />

        <div>
          <div v-if="dataset.numberImages > 0 && statusParts" class="status-summary">
            <!-- the same statuses and colours as the dataset's progress -->
            <div class="status-legend">
              <span v-for="p in statusParts.filter(p => p.n)" :key="p.key" class="status-item" :title="p.label + ' ' + p.n + '（' + p.pct + '%）'">
                <span class="dot" :class="p.cls" />{{ p.label }} {{ p.n }}
              </span>
              <span class="ms-auto text-muted">{{ $t('review.totalImages', { n: dataset.numberImages }) }}</span>
            </div>
            <div class="progress-stacked status-bar">
              <div
                v-for="p in statusParts"
                :key="p.key"
                class="progress"
                :style="{ width: p.share + '%' }"
                :title="p.label + ' ' + p.n"
              >
                <div class="progress-bar" :class="p.cls" />
              </div>
            </div>
          </div>
          <div v-else-if="dataset.numberImages > 0">
            {{ $t('datasetCard.annotated', { done: dataset.numberAnnotated, total: dataset.numberImages }) }}
            <div class="progress">
              <div
                class="progress-bar"
                role="progressbar"
                :style="{ width: percent + '%' }"
              ></div>
            </div>
          </div>

          <p v-else>{{ $t('datasetCard.noImagesInDataset') }}</p>
          <span
            v-for="(category, index) in listCategories"
            :key="index"
            class="badge rounded-pill text-white category-badge"
            :style="{ 'background-color': category.color || 'var(--bs-primary)' }"
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
            data-bs-toggle="modal"
            :data-bs-target="'#datasetEdit' + dataset.id"
          >
            {{ $t('datasetCard.edit') }}
          </button>
          <button
            v-if="dataset.permissions.owner"
            class="dropdown-item"
            data-bs-toggle="modal"
            :data-bs-target="'#datasetShare' + dataset.id"
          >
            {{ $t('datasetCard.share') }}
          </button>
          <button
            class="dropdown-item"
            @click="onCocoDownloadClick"
            v-show="dataset.permissions.download"
          >
            {{ $t('datasetCard.downloadCoco') }}
          </button>
          <hr v-show="dataset.permissions.delete" />
          <button
            class="dropdown-item delete"
            v-show="dataset.permissions.delete"
            @click="onDeleteClick"
          >
            {{ $t('datasetCard.delete') }}
          </button>
        </div>
      </div>

      <div
        v-show="$store.getters['user/loginEnabled']"
        class="card-footer text-muted"
      >
        {{ $t('common.createdBy', { name: dataset.owner }) }}
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
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form>
              <div class="mb-3">
                <label>{{ $t('datasetCard.defaultCategories') }}</label>
                <TagsInput
                  v-model:value="selectedCategories"
                  element-id="changeDataset"
                  :existing-tags="categoryTags"
                  :only-existing-tags="!$store.getters['user/can']('create_categories')"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                />
              </div>

              <Metadata
                :metadata="defaultMetadata"
                :title="$t('datasetCard.defaultAnnotationMetadata')"
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
              data-bs-dismiss="modal"
            >
              {{ $t('datasetCard.save') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('datasetCard.close') }}
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
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form>
              <div class="mb-3">
                <label>{{ $t('datasetCard.usersSharedWith') }}</label>
                <TagsInput
                  v-model:value="sharedUsers"
                  element-id="usersList"
                  :existing-tags="users"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                  :placeholder="$t('datasetCard.addUsernames')"
                />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="onShare"
              data-bs-dismiss="modal"
            >
              {{ $t('datasetCard.save') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('datasetCard.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import noImageImg from "@/assets/no-image.png";
import notFoundImageImg from "@/assets/404-image.png";
import axios from "axios";
import { TASK_ICONS } from "@/components/TaskPicker.vue";
import Metadata from "@/components/Metadata.vue";

import TagsInput from "@/components/TagsInput.vue";

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
      TASK_ICONS,
      imageError: false,
      selectedCategories: [],
      defaultMetadata: this.dataset.default_annotation_metadata,
      noImageUrl: noImageImg,
      notFoundImageUrl: notFoundImageImg,
      sharedUsers: []
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    onImageClick() {
      let identifier = this.dataset.id;
      this.$router.push({ name: "dataset", params: { identifier } });
    },
    onShare() {
      this.dataset.users = this.sharedUsers;
      axios
        .post("/api/dataset/" + this.dataset.id + "/share", {
          users: this.sharedUsers
        })
        .then(() => {
          this.$parent.updatePage();
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(
            data.code === "no_create_categories" ? this.$t("categoryPicker.noCreate", { names: data.name }) : data.message || String(error)
          );
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
    },
    createSelectedUsers() {
      this.sharedUsers = this.dataset.users;
    }
  },
  computed: {
    /** approved / waiting / rejected / not done, like the progress panel */
    statusParts() {
      const counts = this.dataset.statusCounts;
      if (!counts) return null;
      const total = Object.values(counts).reduce((a, b) => a + b, 0);
      if (!total) return null;
      const colours = { approved: "bg-success", labeled: "bg-warning", rejected: "bg-danger", unlabeled: "bg-secondary" };
      return ["approved", "labeled", "rejected", "unlabeled"].map(key => {
        const n = counts[key] || 0;
        return { key, n, cls: colours[key], label: this.$t("review.status." + key), share: (100 * n) / total, pct: Math.round((100 * n) / total) };
      });
    },
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
    users() {
      let users = {};
      this.$parent.users.forEach(user => {
        users[user.username] = user.username;
      });

      return users;
    }
  },
  mounted() {
    this.createSelectedCategories();
    this.createSelectedUsers();
  }
};
</script>

<style scoped>
.cover {
  position: relative;
}
.task-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(17, 24, 39, 0.78);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
  padding: 2px 8px 2px 4px;
  pointer-events: none;
}
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
.status-summary {
  margin-bottom: 7px;
}
.status-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  margin-bottom: 4px;
}
.status-item {
  white-space: nowrap;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: 0;
}
.status-bar {
  height: 6px;
  margin: 0;
}
/* the parts of the stacked bar (not the outer margin rule above) */
.status-bar .progress {
  margin: 0;
  height: 100%;
}
.card-footer {
  padding: 2px;
  font-size: 11px;
}

.delete {
  color: darkred;
}
</style>
