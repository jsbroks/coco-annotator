<template>
  <div class="col-sm-6 col-md-4 col-xl-3 col-xxl-2">
    <div class="card mb-4 box-shadow" @click="onCardClick">
      <div class="card-body">
        <span class="d-inline-block text-truncate" style="max-width: 75%; float: left">
          <i class="fa fa-circle color-icon" aria-hidden="true" :style="{ color: category.color }" />
          <strong class="card-title">{{ category.name }}</strong>
        </span>

        <i
          class="card-text fa fa-ellipsis-v fa-x icon-more"
          :id="'dropdownCategory' + category.id + uid"
          data-bs-toggle="dropdown"
          aria-haspopup="true"
          aria-expanded="false"
          aria-hidden="true"
        />

        <br />

        <div>
          <p v-if="category.numberAnnotations > 0">
            {{ $t('categoryCard.objects', { n: category.numberAnnotations }) }}
          </p>
          <p v-else>{{ $t('categoryCard.noAnnotationsUseThisCategory') }}</p>
        </div>

        <div v-if="below" class="parent-line text-truncate" :title="pathLabel(below)">
          <i class="fa fa-folder-open-o" /> {{ pathLabel(below, groupParent) }}
        </div>
        <div v-if="otherParents.length" class="parent-line text-truncate" :title="otherParents.map(p => pathLabel(p)).join('、')">
          <i class="fa fa-folder-o" />
          {{ groupParent || below ? $t('parents.alsoIn', { names: otherParents.map(p => pathLabel(p)).join('、') }) : otherParents.map(p => pathLabel(p)).join('、') }}
        </div>

        <div class="dropdown-menu" :aria-labelledby="'dropdownCategory' + category.id + uid">
          <a class="dropdown-item" @click="onDeleteClick">{{ $t('categoryCard.delete') }}</a>
          <!--<a class="dropdown-item" @click="onDownloadClick"
            >{{ $t('categoryCard.downloadCocoImages') }}</a
          >-->
          <button
            class="dropdown-item"
            data-bs-toggle="modal"
            :data-bs-target="'#categoryEdit' + category.id + uid"
          >{{ $t('categoryCard.edit') }}</button>
        </div>
      </div>

      <div
        v-show="$store.getters['user/loginEnabled']"
        class="card-footer text-muted"
      >{{ $t('common.createdBy', { name: category.creator }) }}</div>
    </div>

    <div class="modal fade" role="dialog" ref="category_settings"
        :id="'categoryEdit' + category.id + uid" >
      <div class="modal-dialog" :class="{ 'modal-xl': kpRows > 3, 'modal-lg': kpRows > 0 && kpRows <= 3, 'modal-dialog-scrollable': kpRows > 3 }" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('categoryCard.title', { name: category.name }) }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <form>
              <div class="mb-3">
                <label>{{ $t('categoryCard.name') }}</label>
                <input
                  type="text"
                  :value="name"
                  required="true"
                  class="form-control"
                  :class="{'is-invalid': name.length === 0}"
                  @input="name = $event.target.value"
                />
              </div>

              <div class="mb-3">
                <label>{{ $t('categoryCard.supercategory') }}</label>
                <ParentInput v-model="parents" :known="knownParents" />
                <div class="form-text">{{ $t('parents.hint') }}</div>
              </div>

              <div class="mb-3 row">
                <label class="col-sm-2 col-form-label">{{ $t('categoryCard.color') }}</label>
                <div class="col-sm-9">
                  <input v-model="color" type="color" class="form-control form-control-color w-100" />
                </div>
              </div>

              <div class="mb-3">
                <KeypointsDefinition @rows="kpRows = $event"
                  ref="keypoints"
                  v-model:value="keypoint"
                  element-id="keypoints"
                  :placeholder="$t('categoryCard.addAKeypoint')"
                ></KeypointsDefinition>
                <div v-if="kpSave" class="small mt-1" :class="kpSave === 'error' ? 'text-danger' : 'text-muted'">
                  <i class="fa" :class="{ 'fa-spinner fa-spin': kpSave === 'saving', 'fa-check text-success': kpSave === 'saved', 'fa-exclamation-triangle': kpSave === 'error' }" />
                  {{ $t('keypointsDefinition.autosave.' + kpSave) }}
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="onUpdateClick"
              :disabled="!isFormValid"
              :class="{ disabled: !isFormValid }"
              data-bs-dismiss="modal"
            >{{ $t('categoryCard.update') }}</button>
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t('categoryCard.close') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { onModalHidden } from "@/libs/modal";
import axios from "axios";
import toastrs from "@/mixins/toastrs";
// import TagsInput from "@/components/TagsInput.vue";
import KeypointsDefinition from "@/components/KeypointsDefinition.vue";
import ParentInput from "@/components/ParentInput.vue";
import { isUnder, parentsOf, pathLabel } from "@/libs/parents";


export default {
  name: "CategoryCard",
  mixins: [toastrs],
  components: { KeypointsDefinition, ParentInput },
  emits: ["changed"],
  data() {
    return {
      // keypoints listed in the dialog (several: a wider dialog)
      kpRows: 0,
      group: null,
      parents: parentsOf(this.category),
      color: this.category.color,
      metadata: [],
      keypoint: {
        labels: [...this.category.keypoint_labels],
        edges: [...this.category.keypoint_edges],
        colors: [...this.category.keypoint_colors],
      },
      name: this.category.name,
      isMounted: false,
      // keypoints are saved as they change: '' | saving | saved | error
      kpSave: "",
    };
  },
  props: {
    category: {
      type: Object,
      required: true
    },
    /** makes element ids unique when a card is shown in several groups */
    uid: { type: String, default: "" },
    /** the group this card is shown in (its other parents are listed) */
    groupParent: { type: String, default: null },
    knownParents: { type: Array, default: () => [] }
  },
  computed: {
    /** shown in a folder above its own: the folder (below this one) it is in */
    below() {
      if (!this.groupParent) return null;
      const parents = parentsOf(this.category);
      if (parents.includes(this.groupParent)) return null;
      return parents.find(p => isUnder(p, this.groupParent)) || null;
    },
    otherParents() {
      return parentsOf(this.category).filter(p => p !== this.groupParent && p !== this.below);
    },
    isFormValid() {
      return (
        this.isMounted &&
        this.name.length !== 0 &&
        this.$refs &&
        this.$refs.keypoints &&
        this.$refs.keypoints.valid
      );
    }
  },
  watch: {
    keypoint: {
      deep: true,
      handler() {
        clearTimeout(this.kpTimer);
        this.kpTimer = setTimeout(() => this.saveKeypoints(), 500);
      }
    }
  },
  created() {
    this.resetCategorySettings();
  },
  methods: {
    pathLabel,
    resetCategorySettings() {
      this.kpSave = "";
      this.name = this.category.name;
      this.parents = parentsOf(this.category);
      this.color = this.category.color;
      this.keypoint = {
        labels: [...this.category.keypoint_labels],
        edges: [...this.category.keypoint_edges],
        colors: [...this.category.keypoint_colors],
      };
    },
    /** the keypoints, connections and their colours: saved right away */
    saveKeypoints() {
      const kp = this.keypoint;
      const same =
        JSON.stringify(kp.labels) === JSON.stringify(this.category.keypoint_labels) &&
        JSON.stringify(kp.edges) === JSON.stringify(this.category.keypoint_edges) &&
        JSON.stringify(kp.colors) === JSON.stringify(this.category.keypoint_colors);
      if (same || !this.$refs.keypoints || !this.$refs.keypoints.valid) return;
      this.kpSave = "saving";
      const sent = { labels: [...kp.labels], edges: kp.edges.map(e => [...e]), colors: [...kp.colors] };
      axios
        .put("/api/category/" + this.category.id, {
          // the rest as saved (the dialog's other fields wait for Update)
          name: this.category.name,
          color: this.category.color,
          supercategories: parentsOf(this.category),
          metadata: this.category.metadata,
          keypoint_labels: sent.labels,
          keypoint_edges: sent.edges,
          keypoint_colors: sent.colors
        })
        .then(() => {
          this.category.keypoint_labels = sent.labels;
          this.category.keypoint_edges = sent.edges;
          this.category.keypoint_colors = sent.colors;
          this.kpSave = "saved";
        })
        .catch(error => {
          this.kpSave = "error";
          this.axiosReqestError("Updating Category", (error.response && error.response.data && error.response.data.message) || String(error));
        });
    },
    onCardClick() {},
    onDownloadClick() {},
    onDeleteClick() {
      axios.delete("/api/category/" + this.category.id).then(() => {
        this.$emit("changed");
      });
    },
    onUpdateClick() {
      axios
        .put("/api/category/" + this.category.id, {
          name: this.name,
          color: this.color,
          supercategories: this.parents,
          metadata: this.metadata,
          keypoint_edges: this.keypoint.edges,
          keypoint_labels: this.keypoint.labels,
          keypoint_colors: this.keypoint.colors,
        })
        .then(() => {
          this.axiosReqestSuccess(
            "Updating Category",
            "Category successfully updated"
          );
          this.category.name = this.name;
          this.category.supercategories = [...this.parents];
          this.category.supercategory = this.parents[0] || "";
          this.category.color = this.color;
          this.category.metadata = { ...this.metadata };
          this.category.keypoint_edges = [...this.keypoint.edges];
          this.category.keypoint_labels = [...this.keypoint.labels];
          this.category.keypoint_colors = [...this.keypoint.colors];
          this.$emit("changed");
        })
        .catch(error => {
          this.axiosReqestError(
            "Updating Category",
            error.response.data.message
          );
          this.$emit("changed");
        });
    }
  },
  mounted() {
    onModalHidden(this.$refs.category_settings, this.resetCategorySettings);
    this.isMounted = true;
  }
};
</script>

<style scoped>
.icon-more {
  width: 10%;
  margin: 3px 0;
  padding: 0;
  float: right;
  color: black;
}

.card-body {
  padding: 10px 10px 0 10px;
}

.color-icon {
  display: inline;
  margin: 0;
  padding-right: 10px;
}

.parent-line {
  clear: both;
  font-size: 0.75rem;
  color: #1d5ea8;
}

.card-footer {
  padding: 2px;
  font-size: 11px;
}
</style>
