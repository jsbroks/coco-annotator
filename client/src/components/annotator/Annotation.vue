<template>
  <div
    v-show="showSideMenu"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <li
      class="list-group-item btn btn-link btn-sm text-left"
      :style="{ 'background-color': backgroundColor, color: 'white' }"
    >
      <div @click="isVisible = !isVisible">
        <i
          v-if="isVisible"
          class="fa fa-eye annotation-icon"
          :style="{ float: 'left', 'padding-right': '10px', color: color }"
        />
        <i
          v-else
          class="fa fa-eye-slash annotation-icon"
          style="float: left; padding-right: 10px; color: gray"
        />
      </div>

      <a
        @click="onAnnotationClick"
        :style="{
          float: 'left',
          width: '70%',
          color: isVisible ? 'white' : 'gray'
        }"
      >
        <span v-if="name.length === 0">{{ index + 1 }}</span>
        <span v-else> {{ name }} </span> {{ annotation.name }}
        <i v-if="isEmpty" style="padding-left: 5px; color: lightgray"
          >(Empty)</i
        >
        <i v-else style="padding-left: 5px; color: lightgray"
          >(id: {{ annotation.id }})</i
        >
      </a>

      <i
        class="fa fa-gear annotation-icon"
        style="float:right"
        data-toggle="modal"
        :data-target="'#annotationSettings' + annotation.id"
      />
      <i
        @click="deleteAnnotation"
        class="fa fa-trash-o annotation-icon"
        style="float:right"
      />
    </li>
    <div
      class="modal fade"
      tabindex="-1"
      role="dialog"
      :id="'keypointSettings' + annotation.id"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ currentKeypoint }}
            </h5>
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
                <label>Label</label>
                <TagsInput
                  v-model="keypoint.tag"
                  element-id="keypointTags"
                  :existing-tags="keypointLabelTags"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                  :limit="1"
                ></TagsInput>
              </div>
              <div class="form-group row">
                <label class="col-sm-3 col-form-label">Visibility</label>
                <div class="col-sm-8">
                  <select v-model="keypoint.visibility" class="form-control">
                    <option :value="0">NOT LABELED</option>
                    <option :value="1">LABELED NOT VISIBLE</option>
                    <option :value="2">LABELED VISIBLE</option>
                  </select>
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

    <div
      class="modal fade"
      tabindex="-1"
      role="dialog"
      :id="'annotationSettings' + annotation.id"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ index + 1 }}
              <i style="color: darkgray">(id: {{ annotation.id }})</i>
            </h5>
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

              <div class="form-group row">
                <label class="col-sm-2 col-form-label">Name</label>
                <div class="col-sm-9">
                  <input v-model="name" class="form-control" />
                </div>
              </div>

              <Metadata
                :metadata="annotation.metadata"
                ref="metadata"
                exclude="name"
              />
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
import simplifyjs from "simplify-js";
import JQuery from "jquery";

import { Keypoint, Keypoints } from "@/libs/keypoints";
import { mapMutations } from "vuex";
import UndoAction from "@/undo";

import TagsInput from "@/components/TagsInput";
import Metadata from "@/components/Metadata";

let $ = JQuery;

export default {
  name: "Annotaiton",
  components: {
    Metadata,
    TagsInput
  },
  props: {
    annotation: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    current: {
      type: Number,
      required: true
    },
    hover: {
      type: Number,
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
    search: {
      type: String,
      default: ""
    },
    simplify: {
      type: Number,
      default: 1
    },
    keypointEdges: {
      type: Array,
      default: []
    },
    keypointLabels: {
      type: Array,
      default: []
    }
  },
  data() {
    return {
      isVisible: true,
      color: this.annotation.color,
      compoundPath: null,
      keypoints: null,
      metadata: [],
      isEmpty: true,
      name: "",
      uuid: "",
      pervious: [],
      edges: [[1, 3], [3, 5], [2, 4], [4, 5], [5, 6], [5, 7], [7, 8], [6, 8]],
      count: 0,
      currentKeypoint: null,
      keypoint: {
        tag: [],
        visibility: 0
      },
      tagRecomputeCounter: 0
    };
  },
  methods: {
    ...mapMutations(["addUndo"]),
    initAnnotation() {
      let metaName = this.annotation.metadata.name;
      if (metaName) {
        this.name = metaName;
        delete this.annotation.metadata["name"];
      }

      if (this.compoundPath != null) {
        this.compoundPath.remove();
        this.compoundPath = null;
      }

      this.createCompoundPath(
        this.annotation.paper_object,
        this.annotation.segmentation
      );
    },
    createCompoundPath(json, segments) {
      json = json || null;
      segments = segments || null;

      let width = this.annotation.width;
      let height = this.annotation.height;

      // Validate json
      if (json != null) {
        if (json.length !== 2) {
          json = null;
        }
      }

      // Validate segments
      if (segments != null) {
        if (segments.length === 0) {
          segments = null;
        }
      }

      if (this.compoundPath != null) this.compoundPath.remove();
      if (this.keypoints != null) this.keypoints.remove();

      // Create new compoundpath
      this.compoundPath = new paper.CompoundPath();
      this.keypoints = new Keypoints(this.edges, this.annotation.keypoints, width, height);

      if (json != null) {
        // Import data directroy from paperjs object
        this.compoundPath.importJSON(json);
      } else if (segments != null) {
        // Load segments input compound path
        let center = new paper.Point(width / 2, height / 2);

        for (let i = 0; i < segments.length; i++) {
          let polygon = segments[i];
          let path = new paper.Path();

          for (let j = 0; j < polygon.length; j += 2) {
            let point = new paper.Point(polygon[j], polygon[j + 1]);
            path.add(point.subtract(center));
          }
          path.closePath();
          this.compoundPath.addChild(path);
        }
      }

      this.compoundPath.data.annotationId = this.index;
      this.compoundPath.fullySelected = this.isCurrent;

      this.setColor();

      this.compoundPath.onClick = () => {
        this.$emit("click", this.index);
      };
    },
    deleteAnnotation() {
      axios.delete("/api/annotation/" + this.annotation.id).then(() => {
        this.$socket.emit("annotation", {
          action: "delete",
          annotation: this.annotation
        });
        this.delete();

        this.$emit("deleted", this.index);
      });
    },
    delete() {
      this.$parent.category.annotations.splice(this.index, 1);
      if (this.compoundPath != null) this.compoundPath.remove();
    },
    onAnnotationClick() {
      if (this.isVisible) {
        this.$emit("click", this.index);
      }
    },
    onMouseEnter() {
      if (this.compoundPath == null) return;

      this.compoundPath.selected = true;
    },
    onMouseLeave() {
      if (this.compoundPath == null) return;

      this.compoundPath.selected = false;
    },
    getCompoundPath() {
      if (this.compoundPath == null) {
        this.createCompoundPath();
      }
      return this.compoundPath;
    },
    createUndoAction(actionName) {
      if (this.compoundPath == null) this.createCompoundPath();

      let copy = this.compoundPath.clone();
      copy.fullySelected = false;
      copy.visible = false;
      this.pervious.push(copy);

      let action = new UndoAction({
        name: "Annotaiton " + this.annotation.id,
        action: actionName,
        func: this.undoCompound,
        args: {}
      });
      this.addUndo(action);
    },
    simplifyPath() {
      let simplify = this.simplify;

      this.compoundPath.flatten(1);

      if (this.compoundPath instanceof paper.Path) {
        this.compoundPath = new paper.CompoundPath(this.compoundPath);
        this.compoundPath.data.annotationId = this.index;
      }

      let newChildren = [];
      this.compoundPath.children.forEach(path => {
        let points = [];

        path.segments.forEach(seg => {
          points.push({ x: seg.point.x, y: seg.point.y });
        });
        points = simplifyjs(points, simplify, true);

        let newPath = new paper.Path(points);
        newPath.closePath();

        newChildren.push(newPath);
      });

      this.compoundPath.removeChildren();
      this.compoundPath.addChildren(newChildren);

      this.compoundPath.fullySelected = this.isCurrent;

      this.emitModify();
    },
    undoCompound() {
      if (this.pervious.length == 0) return;
      this.compoundPath.remove();
      this.compoundPath = this.pervious.pop();
      this.compoundPath.fullySelected = this.isCurrent;
    },
    addKeypoint(point) {
      let keypoint = new Keypoint(point.x, point.y, {
        onClick: (event) => {
          this.currentKeypoint = event.target.keypoint
          let id = `#keypointSettings${this.annotation.id}`;
          let indexLabel = this.currentKeypoint.indexLabel;

          this.keypoint.tag = indexLabel == -1 ? [] : [indexLabel.toString()];
          this.keypoint.visibility = this.currentKeypoint.visibility;
          
          $(id).modal("show");
        }
      });

      this.keypoints.addKeypoint(keypoint);
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
    },
    /**
     * Unites current annotation path with anyother path.
     * @param {paper.CompoundPath} compound compound to unite current annotation path with
     * @param {boolean} simplify simplify compound after unite
     * @param {undoable} undoable add an undo action
     */
    unite(compound, simplify = true, undoable = true) {
      if (this.compoundPath == null) this.createCompoundPath();

      let newCompound = this.compoundPath.unite(compound);
      if (undoable) this.createUndoAction("Unite");

      this.compoundPath.remove();
      this.compoundPath = newCompound;

      if (simplify) this.simplifyPath();
    },
    /**
     * Subtract current annotation path with anyother path.
     * @param {paper.CompoundPath} compound compound to subtract current annotation path with
     * @param {boolean} simplify simplify compound after subtraction
     * @param {undoable} undoable add an undo action
     */
    subtract(compound, simplify = true, undoable = true) {
      if (this.compoundPath == null) this.createCompoundPath();

      let newCompound = this.compoundPath.subtract(compound);
      if (undoable) this.createUndoAction("Subtract");

      this.compoundPath.remove();
      this.compoundPath = newCompound;

      if (simplify) this.simplifyPath();
    },
    setColor() {
      if (this.compoundPath == null) return;

      if (!this.$parent.showAnnotations) {
        this.$parent.setColor();
        return;
      }

      this.compoundPath.fillColor = this.color;
      let h = Math.round(this.compoundPath.fillColor.hue);
      let l = Math.round(this.compoundPath.fillColor.lightness * 50);
      let s = Math.round(this.compoundPath.fillColor.saturation * 100);

      let hsl =  "hsl(" + h + "," + s + "%," + l + "%)";
      this.compoundPath.strokeColor = hsl;
      this.keypoints.color = hsl;
    },
    export() {
      if (this.compoundPath == null) this.createCompoundPath();

      let metadata = this.$refs.metadata.export();
      if (this.name.length > 0) metadata.name = this.name;
      let annotationData = {
        id: this.annotation.id,
        color: this.color,
        metadata: metadata
      };

      this.simplifyPath();
      this.compoundPath.fullySelected = false;
      let json = this.compoundPath.exportJSON({
        asString: false,
        precision: 1
      });

      if (!this.keypoints.isEmpty()) {
        annotationData.keypoints = this.keypoints.exportJSON(
          this.keypointLabels,
          this.annotation.width,
          this.annotation.height
        );
      }

      this.compoundPath.fullySelected = this.isCurrent;
      if (this.annotation.paper_object !== json) {
        annotationData.compoundPath = json;
      }

      return annotationData;
    },
    emitModify() {
      this.uuid = Math.random()
        .toString(36)
        .replace(/[^a-z]+/g, "");
      this.annotation.paper_object = this.compoundPath.exportJSON({
        asString: false,
        precision: 1
      });
      this.$socket.emit("annotation", {
        uuid: this.uuid,
        action: "modify",
        annotation: this.annotation
      });
    }
  },
  watch: {
    color() {
      this.setColor();
    },
    isVisible(newVisible) {
      if (this.compoundPath == null) return;

      this.compoundPath.visible = newVisible;
      this.keypoints.visible = newVisible;      
    },
    compoundPath() {
      if (this.compoundPath == null) return;

      this.compoundPath.visible = this.isVisible;
      this.$parent.group.addChild(this.compoundPath);
      this.setColor();
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
    },
    keypoints() {
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
    },
    annotation() {
      this.initAnnotation();
    },
    isCurrent() {
      if (this.compoundPath == null) return;
      this.compoundPath.fullySelected = this.isCurrent;
    },
    "keypoint.tag"(newVal) {
      let id = newVal.length === 0 ? -1 : newVal[0];
      this.keypoints.setKeypointIndex(this.currentKeypoint, id)
      this.tagRecomputeCounter++;
    },
    "keypoint.visibility"(newVal) {
      this.currentKeypoint.visibility = newVal;
    }
  },
  computed: {
    isCurrent() {
      if (this.index === this.current && this.$parent.isCurrent) {
        if (this.compoundPath != null) this.compoundPath.bringToFront();
        return true;
      }
      return false;
    },
    isHover() {
      return this.index === this.hover;
    },
    backgroundColor() {
      if (this.isHover && this.$parent.isHover) return "#646c82";

      if (this.isCurrent) return "#4b624c";

      return "inherit";
    },
    showSideMenu() {
      let search = this.search.toLowerCase();
      if (search.length === 0) return true;
      if (search === String(this.annotation.id)) return true;
      if (search === String(this.index + 1)) return true;
      return this.name.toLowerCase().includes(this.search);
    },
    hsl() {
      if (this.compoundPath == null) return [0, 0, 0];
      let h = Math.round(this.compoundPath.fillColor.hue);
      let l = Math.round(this.compoundPath.fillColor.lightness * 50);
      let s = Math.round(this.compoundPath.fillColor.saturation * 100);

      return [h, s, l]
    },
    keypointLabelTags() {
      this.tagRecomputeCounter;
      let tags = {};

      for(let i = 0; i < this.keypointLabels.length; i++) {
        // Include it tags if it is the current keypoint or not in use.
        if (
          (this.keypoints && !this.keypoints._labelled[i+1]) ||
          (this.currentKeypoint &&this.currentKeypoint.indexLabel == i+1)
        ) {
          tags[i+1] = this.keypointLabels[i];
        }
      }
      return tags;
    }
  },
  sockets: {
    annotation(data) {
      let annotation = data.annotation;

      if (this.uuid == data.uuid) return;
      if (annotation.id != this.annotation.id) return;

      if (data.action == "modify") {
        this.createCompoundPath(
          annotation.paper_object,
          annotation.segmentation
        );
      }

      if (data.action == "delete") {
        this.delete();
      }
    }
  },
  mounted() {
    this.initAnnotation();
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

.annotation-icon {
  margin: 0;
  padding: 3px;
}
</style>
