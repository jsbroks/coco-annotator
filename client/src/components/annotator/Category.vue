<template>
  <div
    class="card"
    v-show="showCategory"
    :style="{
      'background-color': backgroundColor,
      'border-color': borderColor
    }"
  >
    <div
      class="card-header"
      :id="'heading' + category.id"
      @mouseenter="$emit('focus', category.id)"
      @mouseleave="$emit('focus', null)"
    >
      <div :style="{ color: isVisible ? 'white' : 'gray' }">
        <div @click="onEyeClick">
          <i
            v-if="isVisible"
            class="fa fa-eye category-icon"
            :style="{ color: showAnnotations ? 'white' : color }"
            aria-hidden="true"
          />
          <i v-else class="fa fa-eye-slash category-icon" aria-hidden="true" />
        </div>

        <button
          class="btn btn-link btn-sm collapsed category-text"
          style="color: inherit"
          aria-expanded="false"
          :aria-controls="'collapse' + category.id"
          @click="onClick"
        >
          {{ category.name }} ({{ category.annotations.length }})
        </button>

        <i
          class="fa fa-gear category-icon"
          data-bs-toggle="modal"
          :data-bs-target="'#categorySettings' + category.id"
          style="float: right; color: white"
          aria-hidden="true"
        />

        <i
          class="fa fa-crosshairs category-icon solo-icon"
          :class="{ on: solo }"
          :title="solo ? $t('annotator.soloOff') : $t('annotator.soloOn')"
          style="float: right"
          aria-hidden="true"
          @click.stop="$emit('solo', category.id)"
        />

        <i
          @click="createAnnotation"
          class="fa fa-plus category-icon"
          style="float: right; color: white; padding-right: 0"
          aria-hidden="true"
        />
      </div>
    </div>

    <ul v-show="showAnnotations" ref="collapse" class="list-group">
      <li
        v-show="this.category.annotations.length > 0"
        class="list-group-item btn btn-link btn-sm text-start"
        :style="{ 'background-color': backgroundColor, color: 'white' }"
      >
        <input
          v-model="search"
          class="annotation-search"
          :placeholder="$t('category.search')"
          :disabled="this.category.annotations.length < 2"
        />
      </li>

      <Annotation
        v-for="(annotation, listIndex) in category.annotations"
        :search="search"
        :key="annotation.id"
        :simplify="simplify"
        :annotation="annotation"
        :current="current.annotation"
        @click="onAnnotationClick(listIndex)"
        @keypoint-click="onKeypointClick(listIndex, $event)"
        @keypoints-complete="$emit('keypoints-complete')"
        :opacity="opacity"
        :index="listIndex"
        :keypoint-edges="keypoint.edges"
        :keypoint-labels="keypoint.labels"
        :keypoint-colors="keypoint.colors"
        ref="annotation"
        :hover="hover.annotation"
        :active-tool="activeTool"
        :scale="scale"
        @deleted="annotationDeleted"
        :all-categories="getCategoriesList"
      />
    </ul>

    <div
      class="modal fade"
      tabindex="-1"
      role="dialog"
      ref="category_settings"
      :id="'categorySettings' + category.id"
    >
      <div class="modal-dialog" :class="{ 'modal-xl': kpRows > 3, 'modal-lg': kpRows > 0 && kpRows <= 3, 'modal-dialog-scrollable': kpRows > 3 }" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ category.name }}</h5>
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
                <label>{{ $t('category.supercategory') }}</label>
                <ParentInput v-model="parents" :known="knownParents" fetch-known />
                <div class="form-text">{{ $t('parents.hint') }}</div>
              </div>

              <div class="mb-3 row">
                <label class="col-sm-2 col-form-label">{{ $t('category.color') }}</label>
                <div class="col-sm-9">
                  <input v-model="color" type="color" class="form-control form-control-color w-100" />
                </div>
              </div>

              <div class="mb-3">
                <KeypointsDefinition @rows="kpRows = $event" ref="keypoints"
                  v-model:value="keypoint"
                  element-id="keypointLabels"
                ></KeypointsDefinition>
                <div v-if="kpApplied" class="small text-muted mt-1">
                  <i class="fa fa-check text-success" /> {{ $t('keypointsDefinition.autosave.applied') }}
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
            >{{ $t('category.update') }}</button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('category.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { onModalHidden, closeModalsIn } from "@/libs/modal";
import paper from "paper";

import Annotations from "@/models/annotations";
import Annotation from "@/components/annotator/Annotation.vue";
import KeypointsDefinition from "@/components/KeypointsDefinition.vue";
import ParentInput from "@/components/ParentInput.vue";
import { allParents, parentsOf } from "@/libs/parents";


export default {
  name: "Category",
  emits: ["click", "keypoints-complete", "focus", "solo"],
  components: { Annotation, KeypointsDefinition, ParentInput },
  props: {
    category: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    current: {
      type: Object,
      required: true
    },
    hover: {
      type: Object,
      required: true
    },
    opacity: {
      type: Number,
      required: true
    },
    scale: {
      type: Number,
      default: 1
    },
    categorysearch: {
      type: String,
      required: true
    },
    simplify: {
      type: Number,
      default: 1
    },
    activeTool: {
      type: String,
      required: true
    },
    // "only this category" is on for this one
    solo: {
      type: Boolean,
      default: false
    },
    allCategories: {
      type: Array,
      required: true
    }
  },
  data: function() {
    return {
      // keypoints listed in the settings (several: a wider dialog)
      kpRows: 0,
      group: null,
      parents: parentsOf(this.category),
      color: this.category.color,
      keypoint: {
        labels: [...this.category.keypoint_labels],
        edges: [...this.category.keypoint_edges],
        colors: [...this.category.keypoint_colors],
      },
      selectedAnnotation: -1,
      showAnnotations: false,
      isVisible: false,
      search: "",
      isMounted: false,
      kpApplied: false,
    };
  },
  methods: {
    // Vue 3 does not keep v-for ref arrays in source order: sort by index
    annotationRefs() {
      return [...(this.$refs.annotation || [])].sort((a, b) => a.index - b.index);
    },
    show(index) {
      if (this.search.length === 0) return true;
      return this.filterFound.indexOf(index) > -1;
    },
    resetCategorySettings() {
      this.parents = parentsOf(this.category);
      this.color = this.category.color;
      this.keypoint = {
        labels: [...this.category.keypoint_labels],
        edges: [...this.category.keypoint_edges],
        colors: [...this.category.keypoint_colors],
      };
    },
    /**
     * Created
     */
    createAnnotation() {
      let parent = this.$parent;
      let annotationId = this.category.annotations.length;
      // Resolves once the new annotation is mounted and selected
      return Annotations.create({
        image_id: parent.image.id,
        category_id: this.category.id,
      }).then(response => {
        this.$socket.emit("annotation", {
          action: "create",
          category_id: this.category.id,
          annotation: response.data
        });

        this.category.annotations.push(response.data);

        this.selectedAnnotation = annotationId;
        this.$nextTick(() => {
          this.$parent.selectLastEditorTool();
          this.$emit("click", {
            annotation: annotationId,
            category: this.index,
            keypoint: -1,
          });
        });

        this.isVisible = true;
        this.showAnnotations = true;

        let annotations = this.annotationRefs();
        if (annotations == null) return;

        let annotation = annotations[annotationId - 1];
        if (annotation == null) {
          this.$parent.scrollElement(this.$el);
        } else {
          this.$parent.scrollElement(annotation.$el);
        }
        return this.$nextTick();
      });
    },
    onUpdateClick() {
      this.category.keypoint_labels = [...this.keypoint.labels];
      this.category.keypoint_edges = [...this.keypoint.edges];
      this.category.keypoint_colors = [...this.keypoint.colors];
      this.category.supercategories = [...this.parents];
      this.category.supercategory = this.parents[0] || "";
    },
    /**
     * Exports data for send to backend
     * @returns {json} Annotation data, and settings
     */
    export(options = {}) {
      let refs = this.$refs;
      let categoryData = {
        // Category Identification
        id: this.category.id,
        name: this.category.name,
        // Show in side bar
        show: this.category.show,
        // Show groups on canvas
        visualize: this.isVisible,
        color: this.color,
        metadata: [],
        annotations: [],
        supercategory: this.category.supercategory,
        supercategories: parentsOf(this.category),
        keypoint_labels: this.category.keypoint_labels,
        keypoint_edges: this.category.keypoint_edges,
        keypoint_colors: this.category.keypoint_colors,
      };

      if (refs.hasOwnProperty("annotation")) {
        refs.annotation.forEach(annotation => {
          let data = annotation.export(options);
          if (data) categoryData.annotations.push(data);
        });
      }

      return categoryData;
    },
    signature() {
      let annotations = this.annotationRefs().map(a => a.signature()).filter(Boolean);
      return [
        this.category.id,
        this.color,
        JSON.stringify(this.category.keypoint_labels || []),
        JSON.stringify(this.category.keypoint_edges || []),
        ...annotations
      ].join("\n");
    },

    addKeypointEdge(edge) {
      this.keypoint.edges.push(edge);
    },
    removeKeypointEdge(edge) {
      let index = this.keypoint.edges.findIndex(e => {
        let i1 = Math.min(edge[0], edge[1]) == Math.min(e[0], e[1]);
        let i2 = Math.max(edge[0], edge[1]) == Math.max(e[0], e[1]);

        return i1 && i2;
      });

      if (index !== -1) {
        let edge = this.keypoint.edges[index];
        this.keypoint.edges.splice(index, 1);
        let annotations = this.annotationRefs();
        if (annotations) {
          annotations.forEach(a => a.keypoints.removeLine(edge));
        }
      }
    },
    /**
     * Event handler for visibility button
     */
    onEyeClick() {
      this.isVisible = !this.isVisible;

      if (this.showAnnotations && !this.isVisible) {
        this.showAnnotations = false;
      }

      if (this.showAnnotations)
        if (this.isCurrent) {
          this.$emit("click", {
            annotation: this.selectedAnnotation,
            category: this.index,
            keypoint: -1,
          });
        }
    },
    /**
     * Event handler for keypoint click
     */
    onKeypointClick(annotation_index, keypoint_index) {
      let indices = {
        annotation: annotation_index,
        category: this.index,
        keypoint: keypoint_index,
      };
      this.selectedAnnotation = annotation_index;
      this.showAnnotations = true;

      this.$emit("click", indices);
    },
    /**
     * Event handler for annotation click
     */
    onAnnotationClick(index) {
      let indices = {
        annotation: index,
        category: this.index,
        keypoint: -1 
      };
      this.selectedAnnotation = index;
      this.showAnnotations = true;

      this.$emit("click", indices);
    },
    /**
     * Event Handler for category click
     */
    onClick() {
      let indices = {
        annotation: this.selectedAnnotation,
        category: this.index,
        keypoint: -1
      };
      this.$emit("click", indices);

      if (this.category.annotations.length === 0) return;
      this.showAnnotations = !this.showAnnotations;

      if (this.showAnnotations && !this.isVisible) {
        this.isVisible = true;
      }
    },
    /**
     * Creates paperjs group
     */
    initCategory() {
      this.setColor();
    },
    /**
     * @returns {Annotation} returns annotation and provided index
     */
    getAnnotation(index) {
      let ref = this.annotationRefs();
      if (ref == null) return null;
      return this.annotationRefs()[index];
    },
    /**
     * Sets color of current group depending on state.
     * Show annotation colors if showAnnotations is true,
     * Show as group color if showAnnotations is false
     */
    setColor() {
      let annotations = this.annotationRefs();
      if (annotations == null) return;
      if (!this.isVisible) return;

      if (this.showAnnotations) {
        annotations.forEach(a => a.setColor());
      } else {
        annotations.forEach(a => {
          // annotations still being mounted have no shape yet
          if (a.compoundPath != null) a.paintShape(this.color, this.opacity);
          if (a.keypoints != null) {
            a.keypoints.color = this.darkHSL;
            a.keypoints.bringToFront();
          }
        });
      }
    },
    annotationDeleted(index) {
      if (this.selectedAnnotation >= index) {
        this.selectedAnnotation--;
      }

      let indices = {
        annotation: this.selectedAnnotation,
        category: this.index,
        keypoint: -1,
      };
      this.$emit("click", indices);

      if (this.category.annotations.length === 0) this.isVisible = false;
    }
  },
  computed: {
    knownParents() {
      return allParents(this.allCategories);
    },
    showCategory() {
      let search = this.categorysearch.toLowerCase();
      if (search.length === 0) return true;
      return this.category.name.toLowerCase().includes(search);
    },
    getCategoriesList() {
      return this.allCategories.map(category => ({
        value: category.id,
        text: category.name
      }));
    },
    isCurrent() {
      return this.current.category === this.index;
    },
    isHover() {
      return this.hover.category === this.index;
    },
    backgroundColor() {
      if (this.isHover && !this.showAnnotations) {
        return "#646c82";
      }
      return "inherit";
    },
    borderColor() {
      if (this.isCurrent) return "rgba(255, 255, 255, 0.25)";
      return "#404552";
    },
    darkHSL() {
      let color = new paper.Color(this.color);
      let h = Math.round(color.hue);
      let l = Math.round(color.lightness * 50);
      let s = Math.round(color.saturation * 100);
      return "hsl(" + h + "," + s + "%," + l + "%)";
    },
    isFormValid() {
      return (
        this.isMounted &&
        this.$refs &&
        this.$refs.keypoints &&
        this.$refs.keypoints.valid
      );
    }
  },
  watch: {
    // keypoints and their connections take effect as they are chosen (the
    // annotator saves the category with the image)
    keypoint: {
      deep: true,
      handler(kp) {
        if (!this.isMounted || !this.$refs.keypoints || !this.$refs.keypoints.valid) return;
        const same =
          JSON.stringify(kp.labels) === JSON.stringify(this.category.keypoint_labels) &&
          JSON.stringify(kp.edges) === JSON.stringify(this.category.keypoint_edges) &&
          JSON.stringify(kp.colors) === JSON.stringify(this.category.keypoint_colors);
        if (same) return;
        this.category.keypoint_labels = [...kp.labels];
        this.category.keypoint_edges = kp.edges.map(e => [...e]);
        this.category.keypoint_colors = [...kp.colors];
        this.kpApplied = true;
      }
    },
    color() {
      this.setColor();
    },
    opacity() {
      let annotations = this.annotationRefs();
      if (annotations == null) return;

      annotations.forEach(a => a.compoundPath && (a.compoundPath.opacity = this.opacity));
    },
    isVisible(newVisible) {
      let annotations = this.annotationRefs();
      if (annotations == null) return;

      annotations.forEach(a => {
        a.keypoints.visible = newVisible;
        a.isVisible = newVisible;
      });
      this.setColor();
    },
    showAnnotations(showing) {
      if (!showing) {
        this.$emit("click", {
          annotation: -1,
          keypoint: -1,
          category: this.index
        });
      }
      this.setColor();
    },
    category() {
      this.initCategory();
    }
  },
  sockets: {
    annotation(data) {
      let action = data.action;
      let annotation = data.annotation;

      if (annotation.image_id != this.$parent.image.id) return;
      if (annotation.category_id != this.category.id) return;

      let found = this.category.annotations.findIndex(
        a => a.id == annotation.id
      );

      if (found == -1) {
        if (action == "create") {
          this.category.annotations.push(annotation);
        }
      }
    }
  },
  beforeUnmount() {
    closeModalsIn(this.$el);
  },
  mounted() {
    this.initCategory();
    onModalHidden(this.$refs.category_settings, this.resetCategorySettings);
    this.isMounted = true;
  }
};
</script>

<style scoped>
.list-group-item {
  height: 22px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}

.category-icon {
  display: block;
  float: left;
  margin: 0;
  padding: 5px 10px 5px 10px;
}

.btn-link {
  margin: 0;
  padding: 0;
}
.annotation-icon {
  margin: 0;
  padding: 3px;
}

.card-header {
  display: block;
  margin: 0;
  padding: 0;
}

.card {
  background-color: #404552;
}

.annotation-search {
  width: 100%;
  height: 18px;
  color: white;
  background-color: rgba(255, 255, 255, 0.1);
  border: none;
  text-align: center;
  border-radius: 4px;
}

::-webkit-input-placeholder {
  /* WebKit, Blink, Edge */
  color: lightgray;
}
:-moz-placeholder {
  /* Mozilla Firefox 4 to 18 */
  color: lightgray;
  opacity: 1;
}
::-moz-placeholder {
  /* Mozilla Firefox 19+ */
  color: lightgray;
  opacity: 1;
}
:-ms-input-placeholder {
  /* Internet Explorer 10-11 */
  color: lightgray;
}
::-ms-input-placeholder {
  /* Microsoft Edge */
  color: lightgray;
}
::placeholder {
  /* Most modern browsers support this now. */
  color: lightgray;
}
.solo-icon {
  color: #8a91a3;
  padding-right: 0;
}
.solo-icon:hover {
  color: white;
}
.solo-icon.on {
  color: #ffc107;
}
</style>
