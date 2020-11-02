<template>
  <div
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <li
      v-show="showSideMenu"
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

      <button
          class="btn btn-sm btn-link collapsed text-left annotation-text"
          :style="{
            float: 'left',
            width: '70%',
            color: isVisible ? 'white' : 'gray'
          }"
          aria-expanded="false"
          :aria-controls="'collapse_keypoints' + annotation.id"
          @click="onAnnotationClick(!showKeypoints);"
        >
        <template v-if="name.length === 0">
          {{ index + 1 }}
        </template>
        <template v-else> {{ name }} </template>
        {{ annotation.name }}
        <i v-if="isEmpty" style="padding-left: 5px; color: lightgray"
          >(Empty)</i
        >
        <i v-else style="padding-left: 5px; color: lightgray"
          >(id: {{ annotation.id }})</i
        >

        </button>

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

    <ul v-show="showKeypoints" ref="collapse_keypoints"
        class="list-group keypoint-list">
      <li v-for="(kp, index) in keypointListView" :key="index"
          :style="{'background-color': kp.backgroundColor}"
          class="list-group-item text-left keypoint-item">
        <div>
          <i class="fa fa-map-marker keypoint-icon"
              :style="{ color: kp.iconColor}"
              />
        </div>
        <a
          @click="onAnnotationKeypointClick(index)"
          :style="{
            float: 'left',
            width: '70%',
            color: 'white'
          }"
        >
          <span> {{ kp.label }} </span> 
        </a>
        <i
          v-if="kp.visibility !== 0"
          @click="onAnnotationKeypointSettingsClick(index)"
          class="fa fa-gear annotation-icon"
          style="float:right; color: lightgray;"
          data-toggle="modal"
          :data-target="'#keypointSettings' + annotation.id"
        />
        <i
          v-if="kp.visibility !== 0"
          @click="onDeleteKeypointClick(index)"
          class="fa fa-trash-o annotation-icon"
          style="float:right; color: lightgray;"
        />
      </li>
    </ul>

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
              {{ getKeypointLabel(currentKeypoint) }}
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
                <label class="col-sm-3 col-form-label">Visibility</label>
                <div class="col-sm-8">
                  <select v-model="keypoint.visibility" class="form-control">
                    <option v-for="(desc, label) in visibilityOptions" 
                      :key="label" :value="label" :selected="keypoint.visibility == label">{{desc}}</option>
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
                <label class="col-sm-3 col-form-label">Color</label>
                <div class="col-sm-8">
                  <input v-model="color" type="color" class="form-control" />
                </div>
              </div>
              <div class="form-group row">
                <label class="col-sm-3 col-form-label">Name</label>
                <div class="col-sm-8">
                  <input v-model="name" class="form-control" />
                </div>
              </div>
              <div class="form-group row">
                <label class="col-sm-3 col-form-label">Category</label>
                <div class="col-sm-8">
                  <select class="form-control" @change="setCategory">
                    <option
                      v-for="option in allCategories"
                      :selected="annotation.category_id === option.value"
                      :key="option.text"
                    >
                      {{ option.text }}
                    </option>
                  </select>
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
              @click="deleteAnnotation"
              type="button"
              class="btn btn-danger"
              data-dismiss="modal"
            >
              Delete
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
import paper from "paper";
import axios from "axios";
import simplifyjs from "simplify-js";
import JQuery from "jquery";

import { Keypoint, Keypoints, VisibilityOptions } from "@/libs/keypoints";
import { mapMutations } from "vuex";
import UndoAction from "@/undo";

import TagsInput from "@/components/TagsInput";
import Metadata from "@/components/Metadata";

let $ = JQuery;

export default {
  name: "Annotation",
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
      required: true
    },
    keypointLabels: {
      type: Array,
      required: true
    },
    keypointColors: {
      type: Array,
      required: true
    },
    activeTool: {
      type: String,
      required: true
    },
    allCategories: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      isVisible: true,
      showKeypoints: false,
      color: this.annotation.color,
      compoundPath: null,
      keypoints: null,
      metadata: [],
      isEmpty: true,
      name: "",
      uuid: "",
      pervious: [],
      count: 0,
      currentKeypoint: null,
      keypoint: {
        tag: [],
        visibility: 0,
        next: {
          label: -1,
          visibility: 2
        }
      },
      sessions: [],
      session: {
        start: Date.now(),
        tools: [],
        milliseconds: 0
      },
      tagRecomputeCounter: 0,
      visibilityOptions: VisibilityOptions,
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
      this.compoundPath.onDoubleClick = () => {
        if (this.activeTool !== "Select") return;
        $(`#annotationSettings${this.annotation.id}`).modal("show");
      };
      this.keypoints = new Keypoints(this.keypointEdges, this.keypointLabels,
        this.keypointColors, {
          annotationId: this.annotation.id,
          categoryName: this.$parent.category.name,
        });
      this.keypoints.radius = this.scale * 6;
      this.keypoints.lineWidth = this.scale * 2;

      let keypoints = this.annotation.keypoints;
      if (keypoints) {
        for (let i = 0; i < keypoints.length; i += 3) {
          let x = keypoints[i] - width / 2,
            y = keypoints[i + 1] - height / 2,
            v = keypoints[i + 2];

          if (keypoints[i] === 0 && keypoints[i + 1] === 0 && v === 0) continue;

          this.addKeypoint(new paper.Point(x, y), v, i / 3 + 1);
        }
      }

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
      this.compoundPath.data.categoryId = this.categoryIndex;

      this.compoundPath.fullySelected = this.isCurrent;
      this.compoundPath.opacity = this.opacity;

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
      if (this.keypoints != null) {
        this.keypoints._keypoints.forEach( keypoint => {
          this.keypoints.deleteKeypoint(keypoint);
        });
        this.keypoints.remove();
      }
    },
    onAnnotationClick(showKeypoints) {
      if (this.keypointLabels.length) {
        this.showKeypoints = showKeypoints;
      }
      if (this.isVisible) {
        this.$emit("click", this.index);
      }
    },
    onAnnotationKeypointClick(labelIndex) {
      if (this.isKeypointLabeled(labelIndex)) {
        this.keypoint.tag = [String(labelIndex+1)];
        this.currentKeypoint = this.keypoints._labelled[this.keypoint.tag];
      }
      if (this.isVisible) {
        this.$emit("keypoint-click", labelIndex);
      }
    },
    onAnnotationKeypointSettingsClick(labelIndex) {
      this.keypoint.tag = [String(labelIndex+1)];
      let indexLabel = parseInt(String(this.keypoint.tag));
      if (this.keypoints && indexLabel in this.keypoints._labelled) {
        let labelled = this.keypoints._labelled[indexLabel];
        this.currentKeypoint = labelled;
      }
      this.keypoint.visibility = this.getKeypointVisibility(labelIndex);
    },
    onDeleteKeypointClick(labelIndex) {
      let label = String(labelIndex + 1);
      if (label in this.keypoints._labelled) {
        this.deleteKeypoint(this.keypoints._labelled[label]);
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
        name: "Annotation " + this.annotation.id,
        action: actionName,
        func: this.undoCompound,
        args: {}
      });
      this.addUndo(action);
    },
    simplifyPath() {
      if (this.compoundPath != null && this.compoundPath.isEmpty() && this.keypoints.isEmpty()) {
          this.deleteAnnotation();
          return;
      }
      let simplify = this.simplify;

      this.compoundPath.flatten(1);

      if (this.compoundPath instanceof paper.Path) {
        this.compoundPath = new paper.CompoundPath(this.compoundPath);
        this.compoundPath.data.annotationId = this.index;
        this.compoundPath.data.categoryId = this.categoryIndex;
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
      this.keypoints.bringToFront();
      this.emitModify();
    },
    undoCompound() {
      if (this.pervious.length == 0) return;
      this.compoundPath.remove();
      this.compoundPath = this.pervious.pop();
      this.compoundPath.fullySelected = this.isCurrent;
    },
    addKeypoint(point, visibility, label) {
      if (label == null && this.keypoints.contains(point)) return;

      visibility = visibility || parseInt(this.keypoint.next.visibility);
      label = label || parseInt(this.keypoint.next.label);

      let keypoint = new Keypoint(point.x, point.y, {
        visibility: visibility || 0,
        indexLabel: label || -1,
        fillColor: this.keypointColors[label - 1],
        radius: this.scale * 6,
        onClick: event => {
          if (!["Select", "Keypoints"].includes(this.activeTool)) return;
          
          let keypoint = event.target.keypoint;
          // Remove if already selected
          if (keypoint == this.currentKeypoint) {
            this.currentKeypoint = null;
            return;
          }

          this.onAnnotationClick(true);
          this.onAnnotationKeypointClick(keypoint.indexLabel - 1);

          if (this.currentKeypoint) {
            let i1 = this.currentKeypoint.indexLabel;
            let i2 = keypoint.indexLabel;
            if (this.keypoints && i1 > 0 && i2 > 0) {
              let edge = [i1, i2];

              if (!this.keypoints.getLine(edge)) {
                this.$parent.addKeypointEdge(edge);
              } else {
                this.$parent.removeKeypointEdge(edge);
              }
            }
          }

          this.currentKeypoint = keypoint;
        },
        onDoubleClick: event => {
          if (!this.$parent.isCurrent) return;
          if (!["Select", "Keypoints"].includes(this.activeTool)) return;
          this.currentKeypoint = event.target.keypoint;
          let id = `#keypointSettings${this.annotation.id}`;
          let indexLabel = this.currentKeypoint.indexLabel;

          this.keypoint.tag = indexLabel == -1 ? [] : [indexLabel.toString()];
          this.keypoint.visibility = this.currentKeypoint.visibility;

          $(id).modal("show");
        },
        onMouseDrag: event => {
          let keypoint = event.target.keypoint;
          if (!["Select", "Keypoints"].includes(this.activeTool)) return;

          this.keypoints.moveKeypoint(event.point, keypoint);
        }
      });

      this.keypoints.addKeypoint(keypoint);
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
      
      let unusedLabels = this.notUsedKeypointLabels;
      delete unusedLabels[String(label)];
      let unusedLabelKeys = Object.keys(unusedLabels);
      if (unusedLabelKeys.length > 0) {
        let nextLabel = unusedLabelKeys[0];
        for (let ul in unusedLabels) {
          if (ul > label) {
            nextLabel = ul;
            break;
          }
        }
        this.keypoint.next.label = nextLabel;
      } else {
        this.keypoint.next.label = -1;
        this.$emit('keypoints-complete');
      }
      this.tagRecomputeCounter++;
    },
    deleteKeypoint(keypoint) {
      this.keypoints.deleteKeypoint(keypoint);
    },
    /**
     * Unites current annotation path with anyother path.
     * @param {paper.CompoundPath} compound compound to unite current annotation path with
     * @param {boolean} simplify simplify compound after unite
     * @param {undoable} undoable add an undo action.
     * @param {isBBox} isBBox mark annotation as bbox.
     */
    unite(compound, simplify = true, undoable = true, isBBox = false) {
      if (this.compoundPath == null) this.createCompoundPath();

      let newCompound = this.compoundPath.unite(compound);
      newCompound.strokeColor = null;
      newCompound.strokeWidth = 0;
      newCompound.onDoubleClick = this.compoundPath.onDoubleClick;
      newCompound.onClick = this.compoundPath.onClick;
      this.annotation.isbbox = isBBox;
      
      if (undoable) this.createUndoAction("Unite");

      this.compoundPath.remove();
      this.compoundPath = newCompound;
      this.keypoints.bringToFront();

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
      newCompound.onDoubleClick = this.compoundPath.onDoubleClick;
      if (undoable) this.createUndoAction("Subtract");

      this.compoundPath.remove();
      this.compoundPath = newCompound;
      this.keypoints.bringToFront();

      if (simplify) this.simplifyPath();
    },
    setColor() {
      if (this.compoundPath == null) return;

      if (!this.$parent.showAnnotations) {
        this.$parent.setColor();
        return;
      }

      this.compoundPath.opacity = this.opacity;
      this.compoundPath.fillColor = this.color;
      this.keypoints.color = this.darkHSL;
    },
    setCategory(event) {
      const newCategoryName = event.target.value;
      const annotation = this.annotation;
      const oldCategory = this.$parent.category;

      this.$parent.$parent.updateAnnotationCategory(
        annotation,
        oldCategory,
        newCategoryName
      );
      $(`#annotationSettings${annotation.id}`).modal("hide");
    },
    export() {
      if (this.compoundPath == null) this.createCompoundPath();
      let metadata = this.$refs.metadata.export();
      if (this.name.length > 0) metadata.name = this.name;
      let annotationData = {
        id: this.annotation.id,
        isbbox: this.annotation.isbbox,
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

      // Export sessions and reset
      annotationData.sessions = this.sessions;
      this.sessions = [];

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
    },
    getKeypointLabel(keypoint) {
      return keypoint && keypoint.keypoints.labels[keypoint.indexLabel - 1];
    },
    isKeypointSelected(tag, index) {
      return tag == (index + 1);
    },
    isKeypointLabeled(index) {
      return this.keypoints && !!this.keypoints._labelled[index + 1];
    },
    getKeypointVisibility(index) {
      let visibility = 0;
      if (this.keypoints && this.keypoints._labelled) {
        let labelled = this.keypoints._labelled[index + 1];
        if (labelled) {
          visibility = labelled.visibility;
        }
      }
      return visibility;
    },
    getKeypointBackgroundColor(index) {
      if (this.isHover && this.$parent.isHover) return "#646c82";

      // if (this.keypoint.tag == index + 1) return "#4b624c";
      let activeIndex = this.keypoint.next.label;
      if (this.activeTool === "Select") {
        activeIndex = this.keypoint.tag;
      }
      if (this.isCurrent && activeIndex == index + 1) return "rgb(30, 86, 36)";

      return "#383c4a";
    }
  },
  watch: {
    activeTool(tool) {
      if (this.isCurrent) {
        this.session.tools.push(tool);
      
        if (tool === "Keypoints") {
          if (!this.showKeypoints) {
            this.showKeypoints = true;
          }
          var labelIndex = -1;
          for(let i=0; i < this.keypointLabels.length; ++i) {
            
            if (this.isKeypointLabeled(i)) {
              if (labelIndex < 0) {
                labelIndex = i;
              }
            } else {
              labelIndex = i;
              break;
            }
          }

          if (labelIndex > -1) {
            this.keypoint.tag = [String(labelIndex+1)];
            this.currentKeypoint = this.keypoints._labelled[this.keypoint.tag];
            this.$emit("keypoint-click", labelIndex);
          }
        }
      }
    },
    opacity(opacity) {
      this.compoundPath.opacity = opacity;
    },
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
      this.setColor();
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
    },
    keypoints() {
      this.isEmpty = this.compoundPath.isEmpty() && this.keypoints.isEmpty();
    },
    annotation() {
      this.initAnnotation();
    },
    isCurrent(current, wasCurrent) {
      if (current) {
        // Start new session
        this.session.start = Date.now();
        this.session.tools = [this.activeTool];
      } else {
        this.currentKeypoint = null;
      }
      if (wasCurrent) {
        // Close session
        this.session.milliseconds = Date.now() - this.session.start;
        this.sessions.push(this.session);
      }

      if (this.compoundPath == null) return;
      this.compoundPath.fullySelected = this.isCurrent;
    },
    currentKeypoint(point, old) {
      if (old) old.selected = false;
      if (point) point.selected = true;
    },
    "keypoint.tag"(newVal) {
      let id = newVal.length === 0 ? -1 : newVal[0];
      if (id !== -1) {
        this.currentKeypoint = this.keypoints._labelled[id];
      }
      this.tagRecomputeCounter++;
    },
    "keypoint.visibility"(newVal) {
      if (!this.currentKeypoint) return;
      this.currentKeypoint.visibility = newVal;
    },
    keypointEdges(newEdges) {
      this.keypoints.color = this.darkHSL;
      newEdges.forEach(e => this.keypoints.addEdge(e));
    },
    scale: {
      immediate: true,
      handler(scale) {
        if (!this.keypoints) return;

        this.keypoints.radius = scale * 6;
        this.keypoints.lineWidth = scale * 2;
      }
    }
  },
  computed: {
    categoryIndex() {
      return this.$parent.index;
    },
    isCurrent() {
      if (this.index === this.current && this.$parent.isCurrent) {
        // if (this.compoundPath != null) this.compoundPath.bringToFront();
        if (this.keypoints != null) this.keypoints.bringToFront();
        return true;
      }
      return false;
    },
    keypointListView() {
      let listView = [];
      for (let i=0; i < this.keypointLabels.length; ++i) {
        let visibility = this.getKeypointVisibility(i);
        let iconColor = 'rgb(40, 42, 49)';
        if (visibility == 1) {
          iconColor = 'lightgray';
        } else if (visibility == 2) {
          iconColor = this.keypointColors[i];
        }
        listView.push({
          label: this.keypointLabels[i],
          visibility,
          iconColor,
          backgroundColor: this.getKeypointBackgroundColor(i),
        });
      }
      return listView;
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
    darkHSL() {
      let color = new paper.Color(this.color);
      let h = Math.round(color.hue);
      let l = Math.round(color.lightness * 50);
      let s = Math.round(color.saturation * 100);
      return "hsl(" + h + "," + s + "%," + l + "%)";
    },
    notUsedKeypointLabels() {
      this.tagRecomputeCounter;
      let tags = {};

      for (let i = 0; i < this.keypointLabels.length; i++) {
        // Include it tags if it is the current keypoint or not in use.
        if (this.keypoints && !this.keypoints._labelled[i + 1]) {
          tags[i + 1] = this.keypointLabels[i];
        }
      }

      return tags;
    },
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
    $(`#keypointSettings${this.annotation.id}`).on("hidden.bs.modal", () => {
      this.currentKeypoint = null;
    });
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

.annotation-text {
  padding: 0;
  padding-bottom: 4px;
  margin: 0;
  line-height: 1;
}

.keypoint-list {
  float: left;
  width: 100%;
  overflow: hidden;
}

.keypoint-item {
  background-color: #383c4a;
  cursor: pointer;
}

.annotation-icon {
  margin: 0;
  padding: 3px;
}
.keypoint-icon {
  margin: 0;
  padding: 3px;
  float: left;
  padding-right: 10px;
  padding-left: 6px;
}
</style>
