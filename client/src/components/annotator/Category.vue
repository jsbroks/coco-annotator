<template>
  <div
    class="card"
    v-show="showCategory"
    :style="{
      'background-color': backgroundColor,
      'border-color': borderColor
    }"
  >
    <div class="card-header" :id="'heading' + category.id">
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
          data-toggle="modal"
          :data-target="'#categorySettings' + category.id"
          style="float: right; color: white"
          aria-hidden="true"
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
        v-show="this.category.annotations.length > 1"
        class="list-group-item btn btn-link btn-sm text-left"
        :style="{ 'background-color': backgroundColor, color: 'white' }"
      >
        <input
          v-model="search"
          class="annotation-search"
          placeholder="Search"
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
        :opacity="opacity"
        :index="listIndex"
        ref="annotation"
        :hover="hover.annotation"
        @deleted="annotationDeleted"
      />
    </ul>

    <div
      class="modal fade"
      tabindex="-1"
      role="dialog"
      :id="'categorySettings' + category.id"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ category.name }}</h5>
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
              <div class="form-group row">
                <label class="col-sm-2 col-form-label">Color</label>
                <div class="col-sm-9">
                  <input v-model="color" type="color" class="form-control" />
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
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
import paper from "paper";
import axios from "axios";

import Annotation from "@/components/annotator/Annotation";

export default {
  name: "Category",
  components: { Annotation },
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
    }
  },
  data: function() {
    return {
      group: null,
      color: this.category.color,
      selectedAnnotation: -1,
      showAnnotations: false,
      isVisible: false,
      search: ""
    };
  },
  methods: {
    show(index) {
      if (this.search.length === 0) return true;
      return this.filterFound.indexOf(index) > -1;
    },
    /**
     * Created
     */
    createAnnotation() {
      let parent = this.$parent;
      let categories = parent.categories;
      let annotationId = this.category.annotations.length;

      axios
        .post("/api/annotation/", {
          image_id: parent.image.id,
          category_id: this.category.id
        })
        .then(response => {
          categories.filter(element => {
            if (element.id === this.category.id) {
              return element;
            }
          });

          this.category.annotations.push(response.data);

          this.selectedAnnotation = annotationId;
          this.$nextTick(() => {
            this.$emit("click", {
              annotation: annotationId,
              category: this.index
            });
          });

          this.isVisible = true;
          this.showAnnotations = true;

          let annotations = this.$refs.annotation;
          if (annotations == null) return;

          let annotation = annotations[annotationId - 1];
          if (annotation == null) {
            this.$parent.scrollElement(this.$el);
          } else {
            this.$parent.scrollElement(annotation.$el);
          }
        });
    },
    /**
     * Exports data for send to backend
     * @returns {json} Annotation data, and settings
     */
    export() {
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
        annotations: []
      };

      if (refs.hasOwnProperty("annotation")) {
        refs.annotation.forEach(annotation => {
          categoryData.annotations.push(annotation.export());
        });
      }

      return categoryData;
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
            category: this.index
          });
        }
    },
    /**
     * Event handler for annotaiton click
     */
    onAnnotationClick(index) {
      let indices = { annotation: index, category: this.index };
      this.selectedAnnotation = index;
      this.$emit("click", indices);
    },
    /**
     * Event Handler for category click
     */
    onClick() {
      let indices = {
        annotation: this.selectedAnnotation,
        category: this.index
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
      if (this.group !== null) {
        this.group.remove();
        this.group == null;
      }
      this.group = new paper.Group();
      this.group.opacity = this.opacity;
      this.group.visible = this.isVisible;
      this.group.data.categoryId = this.index;
      this.group.clipMask = false;

      this.setColor();
    },
    /**
     * @returns {Annotation} returns annotation and provided index
     */
    getAnnotation(index) {
      let ref = this.$refs.annotation;
      if (ref == null) return null;
      return this.$refs.annotation[index];
    },
    /**
     * Sets color of current group depending on state.
     * Show annotation colors if showAnnotations is true,
     * Show as group color if showAnnotations is false
     */
    setColor() {
      if (!this.isVisible) return;

      if (this.showAnnotations) {
        let annotations = this.$refs.annotation;
        if (annotations) {
          annotations.forEach(annotation => {
            annotation.setColor();
          });
        }
      } else {
        if (this.group != null) {
          this.group.fillColor = this.color;
          let h = Math.round(this.group.fillColor.hue);
          let l = Math.round((this.group.fillColor.lightness - 0.2) * 100);
          let s = Math.round(this.group.fillColor.saturation * 100);
          this.group.strokeColor = "hsl(" + h + "," + s + "%," + l + "%)";
        }
      }
    },
    annotationDeleted(index) {
      if (this.selectedAnnotation >= index) {
        this.selectedAnnotation--;
      }

      let indices = {
        annotation: this.selectedAnnotation,
        category: this.index
      };
      this.$emit("click", indices);

      if (this.category.annotations.length === 0) this.isVisible = false;
    }
  },
  computed: {
    showCategory() {
      let search = this.categorysearch.toLowerCase();
      if (search.length === 0) return true;
      return this.category.name.toLowerCase().includes(search);
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
      if (this.isCurrent) {
        return "rgba(255, 255, 255, 0.25)";
      }
      return "#404552";
    }
  },
  watch: {
    color() {
      this.setColor();
    },
    opacity() {
      if (this.group == null) return;
      this.group.opacity = this.opacity;
    },
    isVisible(newVisible) {
      if (this.group == null) return;
      this.group.visible = newVisible;
      this.setColor();
    },
    showAnnotations(showing) {
      if (!showing) {
        this.$emit("click", {
          annotation: -1,
          category: this.index
        });
      }
      this.setColor();
    },
    category() {
      this.initCategory();
    }
  },
  mounted() {
    this.initCategory();
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
</style>
