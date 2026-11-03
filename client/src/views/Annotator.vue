<template>
  <div style="display: block; height: inherit;">
    
    <aside v-show="panels.show.left" class="left-panel shadow-lg">
      <div v-show="mode == 'segment'">
        <hr />

        <SelectTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="select"
        />
        <hr />

        <BBoxTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="bbox"
        />

        <RotatedBBoxTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="rbbox"
        />

        <PolygonTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="polygon"
        />

        <MagicWandTool
          v-model:selected="activeTool"
          :width="image.raster.width"
          :height="image.raster.height"
          :image-data="image.data"
          @setcursor="setCursor"
          ref="magicwand"
        />

        <BrushTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="brush"
        />
        <EraserTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="eraser"
        />

        <KeypointTool
          v-model:selected="activeTool"
          @setcursor="setCursor"
          ref="keypoint"
        />
        <SAMTool
          v-model:selected="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="sam"
        />
      </div>
      <hr />

      <ModelButton @open="$refs.modelRun.open()" />
      <AnnotateButton :annotate-url="dataset.annotate_url" />

      <div v-show="mode == 'segment'">
        <CopyAnnotationsButton
          :categories="categories"
          :image-id="image.id"
          :next="image.next"
          :previous="image.previous"
        />
        <ShowAllButton />
        <HideAllButton />
        <ClearAnnotationsButton />
      </div>
      <hr>
      <CenterButton />
      <UndoButton />

      <hr />

      <DownloadButton :image="image" />
      <SaveButton />
      <ModeButton v-model:mode="mode" />
      <SettingsButton
        :metadata="image.metadata"
        :commands="commands"
        ref="settings"
      />

      <hr />
      <DeleteButton :image="image" />
    </aside>

    <aside v-show="panels.show.right" class="right-panel shadow-lg">
      <hr />
      <FileTitle
        :previousimage="image.previous"
        :nextimage="image.next"
        :filename="image.filename"
        ref="filetitle"
      />

      <ReviewBar
        v-if="image.id != null"
        ref="reviewBar"
        :image-id="image.id"
        :dataset-id="dataset && dataset.id"
        :filename="image.filename"
        :review="review"
        :can-edit="!!(permissions.dataset && permissions.dataset.edit)"
        :can-review="!!(permissions.dataset && permissions.dataset.review)"
        @before-submit="done => save(() => done(true), { onError: () => done(false) })"
        :get-region="zoomedRegion"
        @updated="review = $event"
        @show-regions="drawReviewMarks(true)"
      />

      <HelpPanel
        v-if="image.id != null && loginEnabledForHelp"
        :image-id="image.id"
        :selected-annotation-id="currentAnnotation && currentAnnotation.annotation ? currentAnnotation.annotation.id : null"
        :focus-id="$route.query.help ? Number($route.query.help) : null"
        :get-region="viewRegion"
        @show-annotation="showAnnotationById"
        @show-region="showRegion"
      />

      <ImageClassPicker
        v-if="image.id != null && (!dataset.task || dataset.task === 'classify' || image.imageClass != null)"
        v-model:value="image.imageClass"
        :image-id="image.id"
        :categories="categories"
        :can-edit="!!(permissions.dataset && permissions.dataset.edit)"
        :next-image-id="image.next"
        :collapsible="dataset.task !== 'classify'"
        @navigate="id => $refs.filetitle.route(id)"
      />

      <div v-if="categories.length > 5">
        <div style="padding: 0px 5px">
          <input
            v-model="search"
            class="search"
            :placeholder="$t('annotator.categorySearch')"
          />
        </div>
      </div>

      <div v-if="soloCategory != null && mode == 'segment'" class="solo-tag">
        <i class="fa fa-crosshairs" />
        <span class="text-truncate">{{ $t('annotator.onlyCategory', { name: soloName }) }}</span>
        <button type="button" class="btn-close btn-close-white" :aria-label="$t('annotator.soloOff')" @click="soloCategory = null" />
      </div>

      <div
        class="sidebar-section"
      >
        <p
          v-if="categories.length == 0"
          style="color: lightgray; font-size: 12px"
        >
          {{ $t('annotator.noCategoriesHaveBeenEnabled') }}
        </p>

        <div
          v-show="mode == 'segment'"
          style="overflow: auto; max-height: 100%"
        >
          <template v-for="(category, index) in categories" :key="category.id + '-category'">
          <div v-if="groupTitle(index) !== null && !search" class="parent-title">
            <i class="fa fa-folder-open-o" /> {{ groupTitle(index) ? pathLabel(groupTitle(index)) : $t('parents.none') }}
          </div>
          <Category
            :simplify="simplify"
            :categorysearch="search"
            :category="category"
            :all-categories="categories"
            :opacity="focusCategory != null && focusCategory !== category.id ? 0.08 : shapeOpacity"
            :solo="soloCategory === category.id"
            :hover="hover"
            :index="index"
            @click="onCategoryClick"
            @keypoints-complete="onKeypointsComplete"
            @focus="id => (hoverCategory = id)"
            @solo="toggleSoloCategory"
            :current="current"
            :active-tool="activeTool"
            :scale="image.scale"
            ref="category"
          />
          </template>
        </div>

        <div v-show="mode == 'label'" style="overflow: auto; max-height: 100%">
          <template v-for="(category, index) in categories" :key="category.id + '-label'">
            <div v-if="groupTitle(index) !== null && !search" class="parent-title">
              <i class="fa fa-folder-open-o" /> {{ groupTitle(index) ? pathLabel(groupTitle(index)) : $t('parents.none') }}
            </div>
            <CLabel
              v-model:categoryIds="image.categoryIds"
              :category="category"
              :search="search"
            />
          </template>
        </div>
      </div>

      <div v-show="mode == 'segment'" class="tool-area">
        <hr />
        <h6 class="sidebar-title text-center">{{ $tr('toolbar', activeTool) }}</h6>

        <div class="tool-section" style="color: lightgray">
          <div v-if="refsReady && $refs.bbox != null">
            <BBoxPanel :bbox="$refs.bbox" />
          </div>
          <div v-if="refsReady && $refs.polygon != null">
            <PolygonPanel :polygon="$refs.polygon" />
          </div>

          <div v-if="refsReady && $refs.select != null">
            <SelectPanel :select="$refs.select" />
          </div>

          <div v-if="refsReady && $refs.magicwand != null">
            <MagicWandPanel :magicwand="$refs.magicwand" />
          </div>

          <div v-if="refsReady && $refs.brush != null">
            <BrushPanel :brush="$refs.brush" />
          </div>

          <div v-if="refsReady && $refs.eraser != null">
            <EraserPanel :eraser="$refs.eraser" />
          </div>

          <div v-if="refsReady && $refs.keypoint != null">
            <KeypointPanel
              :keypoint="$refs.keypoint"
              :current-annotation="currentAnnotation"
            />
          </div>
          <div v-if="refsReady && $refs.rbbox != null">
            <RotatedBBoxPanel :rbbox="$refs.rbbox" />
          </div>
          <div v-if="refsReady && $refs.sam != null">
            <SAMPanel :sam="$refs.sam" />
          </div>
        </div>
      </div>
    </aside>

    <div class="middle-panel" :style="{ cursor: cursor }">
      <div id="frame" ref="frame" class="frame" @wheel="onwheel">
        <canvas class="canvas" id="editor" ref="image" resize />
      </div>
      <!-- the keypoint asked for next -->
      <div v-if="kpGuide" class="kp-guide">
        <template v-if="!kpGuide.hasBox">
          <i class="fa fa-object-group" />
          <span>{{ $t('kpGuide.needBox') }}</span>
          <button type="button" class="btn btn-sm btn-light" @click="activeTool = 'BBox'">
            {{ $t('kpGuide.drawBox') }} <kbd>R</kbd>
          </button>
        </template>
        <template v-else-if="kpGuide.name">
          <span class="kp-dot" :style="{ background: kpGuide.color }" />
          <span>{{ $t('kpGuide.next') }}</span>
          <b class="kp-name">{{ kpGuide.name }}</b>
          <span class="kp-count">{{ kpGuide.done }} / {{ kpGuide.total }}</span>
          <button type="button" class="btn btn-sm btn-light" :title="$t('kpGuide.skipHint')" @click="skipKeypoint">
            {{ $t('kpGuide.skip') }} <kbd>Q</kbd>
          </button>
          <button type="button" class="btn btn-sm btn-outline-light" @click="stopKeypoints">
            {{ $t('kpGuide.finish') }} <kbd>Esc</kbd>
          </button>
        </template>
        <template v-else>
          <i class="fa fa-check" />
          <span>{{ $t('kpGuide.allDone', { n: kpGuide.done, total: kpGuide.total }) }}</span>
        </template>
      </div>
    </div>

    <div v-show="annotating.length > 0" class="fixed-bottom alert alert-warning alert-dismissible fade show">
      <span>
      <i18n-t keypath="annotator.beingAnnotated" tag="span"><template #users><b>{{ annotating.join(', ') }}</b></template></i18n-t>
      </span>
      
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>

    <ModelRunModal
      ref="modelRun"
      modal-id="modelRunImage"
      :categories="categories"
      :running="modelRunning"
      @run="runModelOnImage"
    />
    <ChatWidget
      v-if="dataset && dataset.id"
      :dataset-id="dataset.id"
      :dataset-name="dataset.name"
      :image-id="image.id"
      :image-name="image.filename"
      side="left"
    />
  </div>
</template>

<script>
import paper from "paper";
import { makeColorSampler } from "@/libs/colorSampler";
import { toolCursor } from "@/libs/cursors";

// images already asked for ahead of time (the browser keeps them)
const prefetched = new Set();
// "only this category" carries over to the next image of the same dataset
const keptSolo = { dataset: null, category: null };
import axios from "axios";
import { hideModal } from "@/libs/modal";
import UndoAction, { restoreAnnotations } from "@/undo";
import { groupByParent, parentsOf, pathLabel } from "@/libs/parents";

// save automatically this long after the last change (ms)
const AUTOSAVE_DELAY = 2000;
import Hammer from "hammerjs";

import toastrs from "@/mixins/toastrs";
import shortcuts from "@/mixins/shortcuts";

import FileTitle from "@/components/annotator/FileTitle.vue";
import ReviewBar from "@/components/annotator/ReviewBar.vue";
import ChatWidget from "@/components/ChatWidget.vue";
import HelpPanel from "@/components/annotator/HelpPanel.vue";
import ImageClassPicker from "@/components/annotator/ImageClassPicker.vue";
import { TASK_TOOLS } from "@/components/TaskPicker.vue";
import Category from "@/components/annotator/Category.vue";
import Label from "@/components/annotator/Label.vue";
import Annotations from "@/models/annotations";

import PolygonTool from "@/components/annotator/tools/PolygonTool.vue";
import BBoxTool from "@/components/annotator/tools/BBoxTool.vue";
import SelectTool from "@/components/annotator/tools/SelectTool.vue";
import MagicWandTool from "@/components/annotator/tools/MagicWandTool.vue";
import EraserTool from "@/components/annotator/tools/EraserTool.vue";
import BrushTool from "@/components/annotator/tools/BrushTool.vue";
import KeypointTool from "@/components/annotator/tools/KeypointTool.vue";
import RotatedBBoxTool from "@/components/annotator/tools/RotatedBBoxTool.vue";
import SAMTool from "@/components/annotator/tools/SAMTool.vue";

import CopyAnnotationsButton from "@/components/annotator/tools/CopyAnnotationsButton.vue";
import CenterButton from "@/components/annotator/tools/CenterButton.vue";
import DownloadButton from "@/components/annotator/tools/DownloadButton.vue";
import SaveButton from "@/components/annotator/tools/SaveButton.vue";
import SettingsButton from "@/components/annotator/tools/SettingsButton.vue";
import ModeButton from "@/components/annotator/tools/ModeButton.vue";
import DeleteButton from "@/components/annotator/tools/DeleteButton.vue";
import UndoButton from "@/components/annotator/tools/UndoButton.vue";
import ShowAllButton from "@/components/annotator/tools/ShowAllButton.vue";
import ClearAnnotationsButton from "@/components/annotator/tools/ClearAnnotationsButton.vue";
import HideAllButton from "@/components/annotator/tools/HideAllButton.vue";
import AnnotateButton from "@/components/annotator/tools/AnnotateButton.vue";
import ModelButton from "@/components/annotator/tools/ModelButton.vue";
import ModelRunModal from "@/components/ModelRunModal.vue";

import PolygonPanel from "@/components/annotator/panels/PolygonPanel.vue";
import BBoxPanel from "@/components/annotator/panels/BBoxPanel.vue";
import SelectPanel from "@/components/annotator/panels/SelectPanel.vue";
import MagicWandPanel from "@/components/annotator/panels/MagicWandPanel.vue";
import BrushPanel from "@/components/annotator/panels/BrushPanel.vue";
import EraserPanel from "@/components/annotator/panels/EraserPanel.vue";
import KeypointPanel from "@/components/annotator/panels/KeypointPanel.vue";
import RotatedBBoxPanel from "@/components/annotator/panels/RotatedBBoxPanel.vue";
import SAMPanel from "@/components/annotator/panels/SAMPanel.vue";

import { mapMutations } from "vuex";

export default {
  name: "Annotator",
  components: {
    ChatWidget,
    FileTitle,
    ReviewBar,
    HelpPanel,
    ImageClassPicker,
    CopyAnnotationsButton,
    Category,
    CLabel: Label,
    BBoxTool,
    BBoxPanel,
    PolygonTool,
    PolygonPanel,
    SelectTool,
    MagicWandTool,
    EraserTool,
    BrushTool,
    KeypointTool,
    DownloadButton,
    SaveButton,
    SettingsButton,
    DeleteButton,
    CenterButton,
    SelectPanel,
    MagicWandPanel,
    BrushPanel,
    EraserPanel,
    ModeButton,
    UndoButton,
    HideAllButton,
    ShowAllButton,
    ClearAnnotationsButton,
    KeypointPanel,
    AnnotateButton,
    ModelButton,
    ModelRunModal,
    RotatedBBoxTool,
    RotatedBBoxPanel,
    SAMTool,
    SAMPanel
  },
  mixins: [toastrs, shortcuts],
  props: {
    identifier: {
      type: [Number, String],
      required: true
    }
  },
  data() {
    return {
      goingNext: false,
      copying: false,
      activeTool: "Select",
      // a box was just drawn for an object with keypoints: they are placed
      // next, then this tool comes back for the next object
      kpFlow: null,
      // the box tool used last (an object with keypoints starts with it)
      lastBoxTool: "BBox",
      paper: null,
      shapeOpacity: 0.6,
      // "only this category": hovered in the list, or kept with the crosshairs icon
      hoverCategory: null,
      soloCategory: null,
      // the category new rotated boxes go to: the one picked in the list or
      // with the keyboard; clicking another box on the image to edit it
      // does not change it
      drawCategoryId: null,
      canvasPick: false,
      zoom: 0.2,
      cursor: "move",
      mode: "segment",
      simplify: 1,
      panels: {
        show: {
          left: true,
          right: true
        }
      },
      current: {
        category: -1,
        annotation: -1,
        keypoint: -1,
      },
      hover: {
        category: -1,
        annotation: -1,
        keypoint: -1,
      },
      review: {},
      // marks of where the reviewer saw problems (paper items)
      reviewMarks: [],
      pendingReviewMarks: null,
      permissions: {},
      image: {
        raster: {},
        scale: 0,
        metadata: {},
        ratio: 0,
        rotate: 0,
        id: null,
        url: "",
        dataset: 0,
        previous: null,
        next: null,
        filename: "",
        categoryIds: [],
        imageClass: null,
        data: null
      },
      text: {
        topLeft: null,
        topRight: null
      },
      categories: [],
      dataset: {
        annotate_url: ""
      },
      loading: {
        image: true,
        data: true,
        loader: null
      },
      search: "",
      refsReady: false,
      modelRunning: false,
      // left + right button together: Select tool until both are released
      chord: { active: false, prevTool: null, first: null },
      dblPress: null,
      autosave: {
        saved: null, // signature of the last saved state (null: not loaded yet)
        pending: null,
        since: 0,
        saving: false,
        prefs: null,
        timer: null
      },
      hammer: null,
      annotating: [],
      pinching: {
        old_zoom: 1
      }
    };
  },
  methods: {
    toggleSoloCategory(id) {
      this.soloCategory = this.soloCategory === id ? null : id;
      this.hoverCategory = null;
    },
    keepSolo() {
      keptSolo.dataset = this.dataset && this.dataset.id;
      keptSolo.category = this.soloCategory;
    },
    ...mapMutations(["addProcess", "removeProcess", "resetUndo", "addUndo", "setDataset"]),
    // Vue 3 does not keep v-for ref arrays in source order: sort by index
    categoryRefs() {
      return [...(this.$refs.category || [])].sort((a, b) => a.index - b.index);
    },
    /** Everything that a save would write, without side effects */
    changeSignature() {
      let parts = this.categoryRefs().map(c => c.signature());
      if (this.$refs.settings) parts.push(JSON.stringify(this.$refs.settings.exportMetadata()));
      return parts.join("\n#\n");
    },
    /** Tool settings and zoom, saved with the annotations */
    prefsSignature() {
      const r = this.$refs;
      const tools = ["bbox", "rbbox", "sam", "polygon", "eraser", "brush", "magicwand", "select", "settings"];
      try {
        return JSON.stringify([tools.map(t => (r[t] ? r[t].export() : null)), this.activeTool, this.zoom]);
      } catch (e) {
        return null;
      }
    },
    isDirty() {
      return this.autosave.saved !== null && this.changeSignature() !== this.autosave.saved;
    },
    /**
     * Runs every second: saves once the annotations changed and then stayed
     * the same for a moment (so not in the middle of a drag).
     */
    autosaveTick() {
      const a = this.autosave;
      if (!this.doneLoading || a.saving || this.image.id == null) return;
      const signature = this.changeSignature();
      if (a.saved === null) {
        a.saved = signature; // baseline right after loading
        a.prefs = this.prefsSignature();
        return;
      }
      if (signature === a.saved) {
        a.pending = null;
        return;
      }
      if (signature !== a.pending) {
        a.pending = signature;
        a.since = Date.now();
        return;
      }
      if (Date.now() - a.since >= AUTOSAVE_DELAY) {
        a.pending = null;
        this.save(null, { auto: true });
      }
    },
    /**
     * The time spent on an image counts only while someone is working: no
     * input for a few minutes, or the tab hidden, pauses it (and the
     * "annotating" mark others see) until the next mouse / key input.
     */
    startIdleWatch() {
      const IDLE_MS = 3 * 60 * 1000;
      const idle = (this.idleWatch = { last: Date.now(), paused: false });
      // idleMs: the time since the last input, not counted (gone idle); a
      // hidden tab stops the clock when it is hidden
      const pause = (idleMs = 0) => {
        if (idle.paused || this.image.id == null) return;
        idle.paused = true;
        this.$socket.emit("annotating", { image_id: this.image.id, active: false, idle: true, idle_ms: Math.round(idleMs) });
      };
      idle.activity = () => {
        idle.last = Date.now();
        if (idle.paused && !document.hidden) {
          idle.paused = false;
          this.$socket.emit("annotating", { image_id: this.image.id, active: true });
        }
      };
      idle.visibility = () => (document.hidden ? pause() : idle.activity());
      idle.timer = setInterval(() => {
        if (document.hidden) pause();
        else if (Date.now() - idle.last > IDLE_MS) pause(Date.now() - idle.last);
      }, 15000);
      ["mousemove", "mousedown", "keydown", "wheel", "touchstart"].forEach(name =>
        window.addEventListener(name, idle.activity, { passive: true, capture: true }));
      document.addEventListener("visibilitychange", idle.visibility);
    },
    stopIdleWatch() {
      const idle = this.idleWatch;
      if (!idle) return;
      clearInterval(idle.timer);
      ["mousemove", "mousedown", "keydown", "wheel", "touchstart"].forEach(name =>
        window.removeEventListener(name, idle.activity, { capture: true }));
      document.removeEventListener("visibilitychange", idle.visibility);
      this.idleWatch = null;
    },
    onPageHide(event) {
      // leaving or hiding the tab: save what has not been saved yet
      if (this.autosave.saving || !this.isDirty()) return;
      if (document.visibilityState === "hidden" || event.type === "beforeunload") {
        const data = this.buildSaveData({ auto: true });
        this.autosave.saved = this.changeSignature();
        const blob = new Blob([JSON.stringify(data)], { type: "application/json" });
        if (!(navigator.sendBeacon && navigator.sendBeacon("/api/annotator/data", blob))) {
          axios.post("/api/annotator/data", JSON.stringify(data));
        }
      }
    },
    /**
     * Leaving the image: save, unless nothing changed since the last (auto)save;
     * then switching does not wait for the server to store the same thing again.
     */
    saveIfChanged(callback, options = {}) {
      const a = this.autosave;
      if (!a.saving && a.saved !== null && !this.isDirty() && this.prefsSignature() === a.prefs) {
        if (callback != null) callback();
        return Promise.resolve(true);
      }
      return this.save(callback, options);
    },
    /**
     * Save the annotations. ``callback`` runs once saved; when saving fails a
     * message is shown and ``options.onError`` runs instead (the callback does
     * not: leaving the image then would lose the edits).
     */
    save(callback, options = {}) {
      // someone who may only look at this dataset has nothing to save
      if (this.permissions.dataset && this.permissions.dataset.edit === false) {
        if (callback != null) callback();
        return Promise.resolve(true);
      }
      let process = options.auto ? "Autosaving" : "Saving";
      this.addProcess(process);
      this.autosave.saving = true;
      let data = this.buildSaveData(options);
      // what is being saved now (export may have simplified the shapes)
      let signature = this.changeSignature();
      let prefs = this.prefsSignature();

      return axios
        .post("/api/annotator/data", JSON.stringify(data))
        .then(
          () => {
            this.autosave.saved = signature;
            this.autosave.prefs = prefs;
            this.saveErrorAt = 0;
            // (an error in the callback is not a failed save)
            if (callback != null) callback();
            return true;
          },
          error => {
            // autosave retries by itself: say so at most once a minute
            if (!options.auto || Date.now() - (this.saveErrorAt || 0) > 60000) {
              const message = (error.response && error.response.data && error.response.data.message) || String(error);
              this.$toastr.error(message, this.$t("annotator.saveFailed"));
            }
            this.saveErrorAt = Date.now();
            if (options.onError) options.onError(error);
            return false;
          }
        )
        .finally(() => {
          this.autosave.saving = false;
          this.removeProcess(process);
        });
    },
    buildSaveData(options = {}) {
      let refs = this.$refs;

      let data = {
        mode: this.mode,
        user: {
          bbox: this.$refs.bbox.export(),
          rbbox: this.$refs.rbbox.export(),
          sam: this.$refs.sam.export(),
          polygon: this.$refs.polygon.export(),
          eraser: this.$refs.eraser.export(),
          brush: this.$refs.brush.export(),
          magicwand: this.$refs.magicwand.export(),
          select: this.$refs.select.export(),
          settings: this.$refs.settings.export()
        },
        dataset: this.dataset,
        image: {
          id: this.image.id,
          metadata: this.$refs.settings.exportMetadata(),
          settings: {
            selectedLayers: this.current
          },
          category_ids: []
        },
        settings: {
          activeTool: this.activeTool,
          zoom: this.zoom,
          tools: {}
        },
        categories: []
      };

      if (refs.category != null && this.mode === "segment") {
        refs = { category: this.categoryRefs() };
        this.image.categoryIds = [];
        refs.category.forEach(category => {
          let categoryData = category.export(options);
          data.categories.push(categoryData);

          if (categoryData.annotations.length > 0) {
            let categoryIds = this.image.categoryIds;
            if (categoryIds.indexOf(categoryData.id) === -1) {
              categoryIds.push(categoryData.id);
            }
          }
        });
      }

      data.image.category_ids = this.image.categoryIds;
      return data;
    },
    onpinchstart(e) {
      e.preventDefault();
      if (!this.doneLoading) return;
      let view = this.paper.view;
      this.pinching.old_zoom = this.paper.view.zoom;
      return false;
    },
    onpinch(e) {
      e.preventDefault();
      if (!this.doneLoading) return;
      let view = this.paper.view;
      let viewPosition = view.viewToProject(
        new paper.Point(e.center.x, e.center.y)
      );
      let curr_zoom = e.scale * this.pinching.old_zoom;
      let beta = this.paper.view.zoom / curr_zoom;
      let pc = viewPosition.subtract(this.paper.view.center);
      let a = viewPosition.subtract(pc.multiply(beta)).subtract(this.paper.view.center);  
      let transform = {zoom: curr_zoom, offset: a}
      if (transform.zoom < 10 && transform.zoom > 0.01) {
        this.image.scale = 1 / transform.zoom;
        this.paper.view.zoom = transform.zoom;
        this.paper.view.center = view.center.add(transform.offset);
      }
      return false;
    },
    onwheel(e) {
      e.preventDefault();
      if (!this.doneLoading) return;

      let view = this.paper.view;

      if (e.ctrlKey) {
        // Pan up and down
        let delta = new paper.Point(0, 0.5 * e.deltaY);
        this.paper.view.setCenter(view.center.add(delta));
      } else if (e.shiftKey) {
        // Pan left and right
        let delta = new paper.Point(0.5 * e.deltaY, 0);
        this.paper.view.setCenter(view.center.add(delta));
      } else {
        let viewPosition = view.viewToProject(
          new paper.Point(e.offsetX, e.offsetY)
        );

        let transform = this.changeZoom(e.deltaY, viewPosition);
        if (transform.zoom < 10 && transform.zoom > 0.01) {
          this.image.scale = 1 / transform.zoom;
          this.paper.view.zoom = transform.zoom;
          this.paper.view.center = view.center.add(transform.offset);
        }
      }

      return false;
    },
    fit() {
      let canvas = document.getElementById("editor");

      let parentX = this.image.raster.width;
      let parentY = this.image.raster.height;

      this.paper.view.zoom = Math.min(
        (canvas.width / parentX) * 0.95,
        (canvas.height / parentY) * 0.8
      );

      this.image.scale = 1 / this.paper.view.zoom;
      this.paper.view.setCenter(0, 0);
    },
    changeZoom(delta, p) {
      let oldZoom = this.paper.view.zoom;
      let c = this.paper.view.center;
      let factor = 1 + this.zoom;

      let zoom = delta < 0 ? oldZoom * factor : oldZoom / factor;
      let beta = oldZoom / zoom;
      let pc = p.subtract(c);
      let a = p.subtract(pc.multiply(beta)).subtract(c);

      return { zoom: zoom, offset: a };
    },

    initCanvas() {
      let process = "Initializing canvas";
      this.addProcess(process);
      this.loading.image = true;

      let canvas = document.getElementById("editor");
      this.paper.setup(canvas);
      this.paper.view.viewSize = [
        this.paper.view.size.width,
        window.innerHeight
      ];
      this.paper.activate();

      this.image.raster = new paper.Raster(this.image.url);
      this.image.raster.onLoad = () => {
        let width = this.image.raster.width;
        let height = this.image.raster.height;

        this.image.raster.sendToBack();
        this.fit();
        this.image.ratio = (width * height) / 1000000;
        this.removeProcess(process);

        // full-size pixels are only needed by the magic wand: made when it is picked
        // (copying a 12 MP photo takes about a second)
        this.image.data = null;
        // after the first paint (the image is decoded by then)
        this.colorSampler = null;
        const raster = this.image.raster;
        setTimeout(() => {
          if (this.image.raster === raster) this.colorSampler = makeColorSampler(raster.image, width, height);
        }, 400);
        if (this.activeTool === "Magic Wand") this.ensureImageData();
        this.prefetchNeighbours();
        if (this.pendingReviewMarks) {
          const zoom = this.pendingReviewMarks === "zoom";
          this.pendingReviewMarks = null;
          this.$nextTick(() => this.drawReviewMarks(zoom));
        }
        if (this.pendingRegion) {
          const region = this.pendingRegion;
          this.pendingRegion = null;
          this.$nextTick(() => this.showRegion(region));
        }
        let fontSize = width * 0.025;

        let positionTopLeft = new paper.Point(
          -width / 2,
          -height / 2 - fontSize * 0.5
        );
        this.text.topLeft = new paper.PointText(positionTopLeft);
        this.text.topLeft.fontSize = fontSize;
        this.text.topLeft.fillColor = "white";
        this.text.topLeft.content = this.image.filename;

        let positionTopRight = new paper.Point(
          width / 2,
          -height / 2 - fontSize * 0.4
        );
        this.text.topRight = new paper.PointText(positionTopRight);
        this.text.topRight.justification = "right";
        this.text.topRight.fontSize = fontSize;
        this.text.topRight.fillColor = "white";
        this.text.topRight.content = width + "x" + height;

        this.loading.image = false;
      };
    },
    /** the part of the image on screen now, in image pixels */
    viewRegion() {
      const raster = this.image.raster;
      if (!this.paper || !raster || !raster.width) return null;
      const b = this.paper.view.bounds;
      const w = raster.width, h = raster.height;
      const x0 = Math.max(0, b.x + w / 2), y0 = Math.max(0, b.y + h / 2);
      const x1 = Math.min(w, b.x + b.width + w / 2), y1 = Math.min(h, b.y + b.height + h / 2);
      if (x1 <= x0 || y1 <= y0) return null;
      return { x: Math.round(x0), y: Math.round(y0), w: Math.round(x1 - x0), h: Math.round(y1 - y0) };
    },
    /** the zoomed-in part of the image, or null when (nearly) all of it is on screen */
    zoomedRegion() {
      const v = this.viewRegion();
      const raster = this.image.raster;
      if (!v || !raster) return null;
      return v.w * v.h < raster.width * raster.height * 0.8 ? v : null;
    },
    /** zoom so that a region {x, y, w, h} (image pixels) fills the screen */
    zoomToRegion(region) {
      const raster = this.image.raster;
      const w = raster.width, h = raster.height;
      const canvas = document.getElementById("editor");
      const zoom = Math.min(canvas.width / region.w, canvas.height / region.h) * 0.85;
      if (zoom > 0.01 && zoom < 60) {
        this.paper.view.zoom = zoom;
        this.image.scale = 1 / zoom;
      }
      const cx = region.x + region.w / 2 - w / 2, cy = region.y + region.h / 2 - h / 2;
      this.paper.view.setCenter(cx, cy);
    },
    /** mark where the reviewer saw problems on a rejected image (and zoom there) */
    drawReviewMarks(zoomTo = false) {
      this.reviewMarks.forEach(m => m.remove());
      this.reviewMarks = [];
      const regions = (this.review.status === "rejected" && this.review.review_regions) || [];
      if (!regions.length || !this.paper) return;
      const raster = this.image.raster;
      if (!raster || !raster.loaded) {
        this.pendingReviewMarks = zoomTo ? "zoom" : "draw";
        return;
      }
      const w = raster.width, h = raster.height;
      if (zoomTo) {
        const x0 = Math.min(...regions.map(r => r[0])), y0 = Math.min(...regions.map(r => r[1]));
        const x1 = Math.max(...regions.map(r => r[0] + r[2])), y1 = Math.max(...regions.map(r => r[1] + r[3]));
        this.zoomToRegion({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
      }
      this.reviewMarks = regions.map(r => {
        const mark = new paper.Path.Rectangle({
          point: [r[0] - w / 2, r[1] - h / 2],
          size: [r[2], r[3]],
          strokeColor: "#ff6b6b",
          strokeWidth: 3,
          dashArray: [10, 6],
          strokeScaling: false,
          locked: true,
          // not hit by the tools
          guide: true
        });
        mark.data.reviewMark = true;
        return mark;
      });
    },
    /** zoom to a question's place and mark it (null: remove the mark) */
    showRegion(region) {
      if (this.helpMark) {
        this.helpMark.remove();
        this.helpMark = null;
      }
      if (!region) return;
      const raster = this.image.raster;
      if (!raster || !raster.loaded) {
        // the image is still loading: do it then
        this.pendingRegion = region;
        return;
      }
      const w = raster.width, h = raster.height;
      this.zoomToRegion(region);
      this.helpMark = new paper.Path.Rectangle({
        point: [region.x - w / 2, region.y - h / 2],
        size: [region.w, region.h],
        strokeColor: "#ffc107",
        strokeWidth: 3 / this.paper.view.zoom,
        dashArray: [10 / this.paper.view.zoom, 6 / this.paper.view.zoom],
        locked: true,
        // not hit by the tools (select, click-to-switch)
        guide: true
      });
      this.helpMark.data.helpMark = true;
    },
    /** select the annotation a question is about */
    showAnnotationById(id) {
      const categories = this.categoryRefs();
      for (const category of categories) {
        const annotations = category.annotationRefs();
        const index = annotations.findIndex(a => a.annotation && a.annotation.id === id);
        if (index >= 0) {
          this.onCategoryClick({ category: category.index, annotation: index, keypoint: -1 });
          return;
        }
      }
      this.$toastr.info(this.$t("help.annotationGone"));
    },
    /* ---------- left + right button: temporary Select tool ---------- */
    toolRef(name) {
      return Object.values(this.$refs).find(r => r && r.name === name && r.tool) || null;
    },
    /** what the active tool has in progress (to take back a press) */
    toolSnapshot(tool = this.activeTool) {
      const r = this.$refs;
      switch (tool) {
        case "Polygon": {
          const path = r.polygon.polygon.path;
          return { path: !!path, n: path ? path.segments.length : 0 };
        }
        case "BBox":
          return { path: !!r.bbox.polygon.path };
        case "Rotated BBox":
          return { drawing: !!r.rbbox.drawing, drag: !!r.rbbox.drag };
        default:
          return {};
      }
    },
    /** the first button's press started something with the drawing tool: undo it */
    undoFirstPress(first) {
      if (!first || Date.now() - first.time > 3000) return;
      const r = this.$refs;
      const snap = first.snap;
      if (first.tool === "Polygon" && r.polygon) {
        const path = r.polygon.polygon.path;
        if (path && !snap.path) r.polygon.deletePolygon();
        else if (path) while (path.segments.length > snap.n) path.removeSegment(path.segments.length - 1);
        r.polygon.actionPoints = 0;
      } else if (first.tool === "BBox" && r.bbox) {
        if (r.bbox.polygon.path && !snap.path) r.bbox.deleteBbox();
      } else if (first.tool === "Rotated BBox" && r.rbbox) {
        if (r.rbbox.drawing && !snap.drawing) r.rbbox.cancelDrawing();
        if (r.rbbox.drag && !snap.drag) {
          r.rbbox.drag = null;
          r.rbbox.syncFromAnnotation();
        }
      }
    },
    onChordDown(e) {
      if (this.chord.active) return;
      const both = (e.buttons & 3) === 3;
      if (!both) {
        if (e.button === 2) {
          // a right press alone does not draw (it may be the start of left + right)
          e.stopPropagation();
          this.chord.first = null;
        } else if (e.button === 0) {
          this.chord.first = { time: Date.now(), tool: this.activeTool, snap: this.toolSnapshot() };
        }
        return;
      }
      const first = this.chord.first;
      this.chord.active = true;
      this.chord.prevTool = first && Date.now() - first.time < 3000 ? first.tool : this.activeTool;
      this.undoFirstPress(first);
      this.chord.first = null;

      // end paper's drag of the first press without telling the drawing tool
      const idle = this.chordIdleTool || (this.chordIdleTool = new this.paper.Tool());
      idle.activate();
      document.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: e.clientX, clientY: e.clientY }));

      // the Select tool gets this press (a click selects, dragging moves)
      const select = this.$refs.select;
      select.tool.activate();
      this.activeTool = "Select";
    },
    onChordUp(e) {
      if (!this.chord.active) {
        // the release of a right press that was kept from the tools
        if (e.button === 2 && e.isTrusted) e.stopPropagation();
        return;
      }
      if (!e.isTrusted) return;
      if (e.buttons & 3) return; // one button still held
      // let the Select tool finish this release, then go back
      setTimeout(this.endChord, 0);
    },
    endChord() {
      if (!this.chord.active) return;
      const prev = this.chord.prevTool;
      this.chord.active = false;
      this.chord.prevTool = null;
      if (prev && prev !== "Select") {
        const ref = this.toolRef(prev);
        if (ref && !ref.isDisabled) {
          ref.tool.activate();
          this.activeTool = prev;
        }
      }
    },
    onCanvasContextMenu(e) {
      // right button is used with the left one (temporary Select): no browser menu
      e.preventDefault();
    },
    /** Pixels of the whole image for the magic wand (once per image) */
    ensureImageData() {
      const raster = this.image.raster;
      if (this.image.data || !raster || !raster.loaded) return;
      const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
      ctx.canvas.width = raster.width;
      ctx.canvas.height = raster.height;
      ctx.drawImage(raster.image, 0, 0);
      this.image.data = ctx.getImageData(0, 0, raster.width, raster.height);
    },
    /** "#rrggbb" of the image around a point, for tools that pick a contrasting stroke */
    averageColor(point, radius) {
      return this.colorSampler ? this.colorSampler.average(point, radius) : null;
    },
    /** Start downloading the next and previous images so switching shows them at once */
    prefetchNeighbours() {
      if (!this.image.raster || !this.image.raster.loaded || this.loading.data) return;
      [this.image.next, this.image.previous].forEach(id => {
        if (id == null || prefetched.has(id)) return;
        prefetched.add(id);
        const img = new Image();
        img.src = "/api/image/" + id;
        if (prefetched.size > 50) prefetched.clear();
      });
    },
    setPreferences(preferences) {
      let refs = this.$refs;

      refs.bbox.setPreferences(preferences.bbox || preferences.polygon || {});
      refs.rbbox.setPreferences(preferences.rbbox || {});
      refs.sam.setPreferences(preferences.sam || {});
      refs.polygon.setPreferences(preferences.polygon || {});
      refs.select.setPreferences(preferences.select || {});
      refs.magicwand.setPreferences(preferences.magicwand || {});
      refs.brush.setPreferences(preferences.brush || {});
      refs.eraser.setPreferences(preferences.eraser || {});
    },
    getData(callback) {
      let process = "Loading annotation data";
      this.addProcess(process);
      this.loading.data = true;
      axios
        .get("/api/annotator/data/" + this.image.id)
        .then(response => {
          let data = response.data;

          this.loading.data = false;
          this.autosave.saved = null;
          this.autosave.pending = null;
          // Set image data
          this.image.metadata = data.image.metadata || {};
          this.image.filename = data.image.file_name;
          this.image.next = data.image.next;
          this.image.previous = data.image.previous;
          this.image.categoryIds = data.image.category_ids || [];
          this.image.imageClass = data.image.image_class ?? null;

          this.annotating = data.image.annotating || [];

          this.review = data.review || {};
          this.applyTaskTool(data.dataset);
          this.permissions = data.permissions || {};

          // Set other data
          this.dataset = data.dataset;
          if (keptSolo.dataset === (data.dataset && data.dataset.id) && keptSolo.category != null &&
              (data.categories || []).some(c => c.id === keptSolo.category)) {
            this.soloCategory = keptSolo.category;
          }
          // grouped by (first) parent category, keeping the dataset order inside a group
          this.categories = groupByParent(data.categories, { firstOnly: true }).flatMap(g => g.items);

          // Update status

          this.setDataset(this.dataset);

          let preferences = data.preferences;
          this.setPreferences(preferences);

          if (this.text.topLeft != null) {
            this.text.topLeft.content = this.image.filename;
          }

          this.$nextTick(() => {
            this.showAll();
            this.prefetchNeighbours();
          });

          if (callback != null) callback();
        })
        .catch(() => {
          this.axiosReqestError(
            "Could not find requested image",
            "Redirecting to previous page."
          );
          this.$router.go(-1);
        })
        .finally(() => this.removeProcess(process));
    },
    onCategoryClick(indices) {
      if (indices.fromCanvas) {
        // only skip the category watcher when it will actually fire
        this.canvasPick = indices.category !== this.current.category;
      } else {
        const c = this.categories[indices.category];
        if (c) this.drawCategoryId = c.id;
      }
      this.current.annotation = indices.annotation;
      this.current.category = indices.category;
      if (!indices.hasOwnProperty('keypoint')) {
        indices.keypoint = -1;
      }
      if (indices.keypoint !== -1) {
        this.current.keypoint = indices.keypoint;
        let ann = this.currentCategory.category.annotations[this.current.annotation];
        let kpTool = this.$refs.keypoint;
        let selectTool = this.$refs.select;
        let category = this.categoryRefs()[this.current.category];
        let annotation = category.annotationRefs()[this.current.annotation];
        annotation.showKeypoints = true;
        let keypoints = annotation.keypoints;
        if (keypoints._labelled[indices.keypoint + 1]) {
          let indexLabel = String(this.current.keypoint + 1);
          let keypoint = keypoints._labelled[indexLabel];
          keypoint.selected = true;
          selectTool.click();
        } else {
          this.currentAnnotation.keypoint.next.label = String(indices.keypoint + 1);
          kpTool.click();
        }
      }
    },
    onKeypointsComplete() {
      // also emitted while annotations load, before anything is selected
      if (this.currentAnnotation == null) return;
      this.currentAnnotation.keypoint.next.label = -1;
      if (this.activeTool !== "Keypoints") return;
      // box first, then its keypoints: on to the next object's box
      const back = this.kpFlow && this.kpFlow.tool;
      this.kpFlow = null;
      if (back) this.activeTool = back;
      else this.$refs.select.click();
    },
    /** an object with keypoints but no box yet: the box tool, then (once
     *  the box is drawn) the keypoint tool. Only from the select or keypoint
     *  tool: a shape being drawn with another tool is left alone. */
    boxFirst() {
      if (this.activeTool !== "Keypoints" && this.activeTool !== "Select") return;
      const annotation = this.currentAnnotation;
      if (!annotation || !annotation.keypointLabels || !annotation.keypointLabels.length) return;
      const a = annotation.annotation;
      if (a.isbbox || a.isrbbox) return;
      // already outlined some other way, or keypoints placed: not a new object
      if (annotation.compoundPath && !annotation.compoundPath.isEmpty()) return;
      if (annotation.keypoints && !annotation.keypoints.isEmpty()) return;
      this.activeTool = this.lastBoxTool;
    },
    /** a box tool finished a box: an object with keypoints gets them next */
    afterBoxDrawn(tool) {
      this.$nextTick(() => {
        const annotation = this.currentAnnotation;
        if (!annotation || !annotation.keypointLabels || !annotation.keypointLabels.length) return;
        // a box changed on an object that already has its keypoints
        if (annotation.keypoints && !annotation.keypoints.isEmpty()) return;
        annotation.kpSkipped = [];
        this.kpFlow = { tool };
        this.activeTool = "Keypoints";
      });
    },
    /** the keypoint asked for cannot be seen: on to the one after it */
    skipKeypoint() {
      if (this.activeTool !== "Keypoints" || !this.currentAnnotation) return;
      this.currentAnnotation.skipKeypoint();
    },
    /** done with this object's keypoints (the rest stay unplaced) */
    stopKeypoints() {
      if (this.activeTool !== "Keypoints") return;
      const back = this.kpFlow && this.kpFlow.tool;
      this.kpFlow = null;
      if (this.currentAnnotation) this.currentAnnotation.keypoint.next.label = -1;
      if (back) this.activeTool = back;
      else this.$refs.select.click();
    },
    /** parent name to show above the category at ``index`` ("" = no parent), or null for no title */
    pathLabel,
    groupTitle(index) {
      return this.groupTitles[index] ?? null;
    },
    getCategory(index) {
      if (index == null) return null;
      if (index < 0) return null;

      let ref = this.categoryRefs();

      if (ref == null) return null;
      if (ref.length < 1 || index >= ref.length) return null;

      return this.categoryRefs()[index];
    },
    // Current Annotation Operations
    uniteCurrentAnnotation(compound, simplify = true, undoable = true, isBBox = false) {
      if (this.currentAnnotation == null) return;
      this.currentAnnotation.unite(compound, simplify, undoable, isBBox);
    },
    subtractCurrentAnnotation(compound, simplify = true, undoable = true) {
      if (this.currentCategory == null) return;
      this.currentAnnotation.subtract(compound, simplify, undoable);
    },

    /** First visit to a dataset in this browser session: the tool for its task */
    applyTaskTool(dataset) {
      const tool = dataset && TASK_TOOLS[dataset.task];
      if (!tool) return;
      const key = `annotator/taskTool/${dataset.id}`;
      try {
        if (sessionStorage.getItem(key)) return;
        sessionStorage.setItem(key, "1");
        localStorage.setItem("editorTool", tool);
      } catch {
        // storage unavailable: keep the current tool
      }
    },
    selectLastEditorTool() {
      this.activeTool = localStorage.getItem("editorTool") || "Select";
    },

    setCursor(newCursor) {
      // drawing tools get a crosshair that does not get lost on the picture
      this.cursor = toolCursor(newCursor);
    },
    incrementCategory() {
      if (this.current.category >= this.categories.length - 1) {
        this.current.category = -1;
      } else {
        this.current.category += 1;
        if (this.currentKeypoint) {
          this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        }
      }
    },
    decrementCategory() {
      if (this.current.category === -1) {
        this.current.category = this.categories.length - 1;
        let annotationCount = this.currentCategory.category.annotations.length;
        if (annotationCount > 0) {
          this.current.annotation = annotationCount - 1;
        }
      } else {
        this.current.category -= 1;
      }
    },
    incrementAnnotation() {
      let annotationCount = this.currentCategory.category.annotations.length;
      if (this.current.annotation === annotationCount - 1) {
        this.incrementCategory();
        this.current.annotation = -1;
      } else {
        this.current.annotation += 1;
        if (this.currentAnnotation != null && this.currentAnnotation.showKeypoints) {
          this.current.keypoint = 0;
          this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        } else {
          this.current.keypoint = -1;
        }
      }
    },
    decrementAnnotation() {
      let annotationCount = this.currentCategory.category.annotations.length;
      if (this.current.annotation === -1) {
        this.current.annotation = annotationCount - 1;
      } else if (this.current.annotation === 0) {
        this.decrementCategory();
      } else {
        this.current.annotation -= 1;
        if (this.currentAnnotation != null && this.currentAnnotation.showKeypoints) {
          this.current.keypoint = this.currentAnnotation.keypointLabels.length - 1;
          this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        } else {
          this.current.keypoint = -1;
        }
      }
    },
    incrementKeypoint() {
      let keypointCount = this.currentAnnotation.keypointLabels.length;
      if (this.current.keypoint === keypointCount - 1) {
        this.incrementAnnotation();
      } else {
        this.current.keypoint += 1;
      }
      if (this.currentKeypoint != null) {
        this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        // this.currentAnnotation.$emit("keypoint-click", this.current.keypoint);
      }
    },
    decrementKeypoint() {
      if (this.current.keypoint === 0) {
        this.decrementAnnotation();
      } else {
        this.current.keypoint -= 1;
      }
      if (this.currentKeypoint != null) {
        this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        // this.currentAnnotation.$emit("keypoint-click", this.current.keypoint);
      }
    },
    moveUp() {
      if (this.currentCategory != null) {
        if (this.currentAnnotation != null) {
          if (this.currentKeypoint != null) {
            this.decrementKeypoint();
          } else if (this.currentAnnotation.showKeypoints && this.current.keypoint == -1) {
            this.decrementKeypoint();
          } else {
            this.decrementAnnotation();
          }
        } else if (this.current.annotation == -1) {
          this.decrementAnnotation();
        } else {
          this.decrementCategory();
        }
      } else {
        this.decrementCategory();
      }
    },
    moveDown() {
      if (this.currentCategory != null) {
        if (this.currentAnnotation != null) {
          if (this.currentKeypoint != null) {
            this.incrementKeypoint();
          } else if (this.currentAnnotation.showKeypoints && this.current.keypoint == -1) {
            this.incrementKeypoint();
          } else {
            this.incrementAnnotation();
          }
        } else if (this.current.annotation == -1) {
          this.incrementAnnotation();
        } else {
          this.incrementCategory();
        }
      } else {
        this.incrementCategory();
      }
    },
    stepIn() {
      if (this.currentCategory != null) {
        if (!this.currentCategory.isVisible) {
          this.currentCategory.isVisible = true;
          this.current.annotation = 0;
          this.currentAnnotation.showKeypoints = false;
          this.current.keypoint = -1;
        } else if (
          !this.currentCategory.showAnnotations &&
          this.currentAnnotationLength > 0
        ) {
          this.currentCategory.showAnnotations = true;
          this.current.annotation = 0;
          this.currentAnnotation.showKeypoints = false;
          this.current.keypoint = -1;
        } else if (
          !this.currentAnnotation.showKeypoints &&
          this.currentAnnotation.keypointLabels.length > 0
        ) {
          this.currentAnnotation.showKeypoints = true;
          this.current.keypoint = 0;
          this.currentAnnotation.onAnnotationKeypointClick(this.current.keypoint);
        }
      }
    },
    stepOut() {
      if (this.currentCategory != null) {
        if (
          this.currentAnnotation != null &&
          this.currentAnnotation.showKeypoints
        ) {
          this.currentAnnotation.showKeypoints = false;
          this.current.keypoint = -1;
        } else if (this.currentCategory.showAnnotations) {
          this.currentCategory.showAnnotations = false;
          this.current.annotation = -1;
        } else if (this.currentCategory.isVisible) {
          this.currentCategory.isVisible = false;
        }
      }
    },
    /**
     * Bring a category into view inside the sidebar list only, and only when
     * it is out of view. (scrollIntoView centred it every time the current
     * annotation changed, e.g. at the first point of a shape, so the sidebar
     * jumped; it could also scroll the page itself.)
     */
    scrollElement(element) {
      if (!element) return;
      let box = element.parentElement;
      while (box && box !== document.body) {
        const style = getComputedStyle(box);
        if (/(auto|scroll)/.test(style.overflowY) && box.scrollHeight > box.clientHeight) break;
        box = box.parentElement;
      }
      if (!box || box === document.body) return;
      // already in view: leave the list where it is (no jumping while drawing)
      const boxRect = box.getBoundingClientRect();
      const rect = element.getBoundingClientRect();
      const header = Math.min(rect.height, 40); // the category's own row is enough
      if (rect.top >= boxRect.top && rect.top + header <= boxRect.bottom) return;
      // otherwise the smallest move that shows it
      const offset = rect.top < boxRect.top ? rect.top - boxRect.top - 8 : rect.top + header - boxRect.bottom + 8;
      box.scrollTo({ top: Math.max(0, box.scrollTop + offset), behavior: "smooth" });
    },
    showAll() {
      if (this.categoryRefs() == null) return;

      this.categoryRefs().forEach(category => {
        category.isVisible = category.category.annotations.length > 0;
      });
    },
    hideAll() {
      if (this.categoryRefs() == null) return;

      this.categoryRefs().forEach(category => {
        category.isVisible = false;
        category.showAnnotations = false;
      });
    },
    findCategoryByName(categoryName) {
      let categoryComponent = this.categoryRefs().find(
        category =>
          category.category.name.toLowerCase() === categoryName.toLowerCase()
      );
      if (!categoryComponent) return null;
      return categoryComponent.category;
    },
    addAnnotation(categoryName, segments, keypoints, isbbox=false) {
      segments = segments || [];
      keypoints = keypoints || [];

      if (keypoints.length == 0 && segments.length == 0) return;

      let category = this.findCategoryByName(categoryName);
      if (category == null) return;

      Annotations.create({
        image_id: this.image.id,
        category_id: category.id,
        segmentation: segments,
        keypoints: keypoints,
        isbbox: isbbox
      }).then(response => {
        let annotation = response.data;
        category.annotations.push(annotation);
      });
    },

    updateAnnotationCategory(annotation, oldCategory, newCategoryName) {
      const newCategory = this.findCategoryByName(newCategoryName);
      if (!newCategory || !annotation) return;

      Annotations.update(annotation.id, { category_id: newCategory.id }).then(
        response => {
          let newAnnotation = {
            ...response.data,
            ...annotation,
            metadata: response.data.metadata,
            category_id: newCategory.id
          };

          if (newAnnotation) {
            oldCategory.annotations = oldCategory.annotations.filter(
              a => a.id !== annotation.id
            );
            newCategory.annotations.push(newAnnotation);
          }
        }
      );
    },

    /** The tool matching the annotation shape under ``point`` (box, rotated box, polygon) */
    /** the annotation (its component) drawn at a point, or null; a keypoint
     *  there counts as none (it has its own settings) */
    annotationAt(point) {
      if (!this.paper || !this.paper.project) return null;
      const hit = this.paper.project.hitTest(point, {
        fill: true,
        stroke: true,
        tolerance: 3,
        match: result => {
          let item = result.item;
          if (item && item.keypoint) return true;
          while (item && item.data && item.data.annotationId === undefined) item = item.parent;
          return !!(item && item.visible && item.data && item.data.annotationId !== undefined);
        }
      });
      if (!hit || hit.item.keypoint) return null;
      let item = hit.item;
      while (item && item.data.annotationId === undefined) item = item.parent;
      const category = this.categoryRefs()[item.data.categoryId];
      return (category && category.annotationRefs()[item.data.annotationId]) || null;
    },
    /* ---------- double-click on a shape: its settings ---------- */
    allAnnotationIds() {
      const ids = new Set();
      this.categoryRefs().forEach(c => c.annotationRefs().forEach(a => a.annotation && ids.add(a.annotation.id)));
      return ids;
    },
    /** first press of a possible double-click: what was going on before it */
    onDblPress(e) {
      if (e.button !== 0 || e.detail !== 1) return;
      const snaps = {};
      ["Polygon", "BBox", "Rotated BBox"].forEach(t => (snaps[t] = this.toolSnapshot(t)));
      this.dblPress = { time: Date.now(), tool: this.activeTool, snaps, ids: this.allAnnotationIds() };
    },
    /** double-click on a shape, with any tool: open its settings; what the
     *  two presses started (a point, a box, an empty annotation) is taken back */
    onCanvasDblClick(e) {
      const press = this.dblPress;
      this.dblPress = null;
      if (!press || Date.now() - press.time > 1500 || !this.paper || !this.paper.view) return;
      // in the middle of drawing (e.g. placing polygon points): not for us
      const before = press.snaps[press.tool] || {};
      if (before.path || before.drawing) return;
      const rect = this.paper.view.element.getBoundingClientRect();
      const point = this.paper.view.viewToProject(new paper.Point(e.clientX - rect.left, e.clientY - rect.top));
      const target = this.annotationAt(point);
      if (!target) return;
      ["Polygon", "BBox", "Rotated BBox"].forEach(tool => this.undoFirstPress({ time: press.time, tool, snap: press.snaps[tool] }));
      // an annotation the presses created (to draw in) goes again
      setTimeout(() => {
        this.categoryRefs().forEach(c =>
          c.annotationRefs().forEach(a => {
            if (a.annotation && !press.ids.has(a.annotation.id) && a.isEmpty) a.deleteAnnotation({ undoable: false });
          })
        );
      }, 600);
      this.showAnnotationById(target.annotation.id);
      this.$nextTick(() => target.openSettings && target.openSettings());
    },
    toolForShapeAt(point) {
      if (!this.paper || !this.paper.project) return null;
      const hit = this.paper.project.hitTest(point, {
        fill: true,
        stroke: true,
        tolerance: 2,
        match: result => {
          let item = result.item;
          while (item && item.data && item.data.annotationId === undefined) item = item.parent;
          return !!(item && item.visible && item.data && item.data.annotationId !== undefined);
        }
      });
      if (!hit) return null;
      let item = hit.item;
      while (item && item.data.annotationId === undefined) item = item.parent;
      const category = this.categoryRefs()[item.data.categoryId];
      const annotation = category && category.annotationRefs()[item.data.annotationId];
      return annotation && annotation.matchingTool ? annotation.matchingTool() : null;
    },
    /** C: copy every annotation of the previous image onto this one (Ctrl+Z takes it back) */
    copyFromPrevious() {
      const from = this.image.previous;
      const to = this.image.id;
      if (from == null) {
        this.$toastr.info(this.$t("annotator.noPreviousImage"));
        return;
      }
      if (this.copying) return;
      this.copying = true;
      this.current.annotation = -1;
      this.$nextTick(() => {
        this.save(() => {
          axios
            .post(`/api/image/copy/${from}/${to}/annotations`, { category_ids: [] })
            .then(r => {
              const ids = r.data.ids || [];
              if (!ids.length) {
                this.$toastr.info(this.$t("annotator.nothingToCopy"));
                return;
              }
              this.addUndo(
                new UndoAction({
                  name: this.$t("toolbar.copyAnnotations"),
                  action: "Copy",
                  func: () =>
                    axios.post(`/api/image/copy/${to}/annotations/undo`, { ids }).then(() => {
                      if (this.image.id === to) this.getData();
                    }),
                  args: null
                })
              );
              this.$toastr.success(this.$t("annotator.copiedPrevious", { n: ids.length }));
              this.getData();
            })
            .catch(error => {
              const data = (error.response && error.response.data) || {};
              this.$toastr.error(data.message || String(error), this.$t("toolbar.copyAnnotations"));
            })
            .finally(() => (this.copying = false));
        }, { onError: () => (this.copying = false) });
      });
    },
    clearAnnotations() {
      const categories = this.categoryRefs();
      const total = categories.reduce(
        (n, c) => n + c.category.annotations.length,
        0
      );
      if (total === 0) {
        this.$toastr.info(this.$t("annotator.nothingToClear"));
        return;
      }
      // no confirmation: Ctrl+Z (or the trash) brings them back

      const snapshots = [];
      categories.forEach(c =>
        c.annotationRefs().forEach(a => {
          if (!a.isBlank()) snapshots.push(a.snapshot());
        })
      );

      axios
        .delete(`/api/image/${this.image.id}/annotations`)
        .then(() => {
          this.current.annotation = -1;
          this.current.keypoint = -1;
          if (snapshots.length) {
            this.addUndo(
              new UndoAction({
                name: this.$t("toolbar.clearAnnotations"),
                action: "Clear",
                func: args =>
                  restoreAnnotations(args).then(() => {
                    this.$nextTick(() => this.showAll());
                  }),
                args: snapshots
              })
            );
          }
          // removing them from the lists also removes their shapes
          categories.forEach(c => {
            c.category.annotations.splice(0);
            // empty categories are hidden, as after deleting one by one
            c.showAnnotations = false;
            c.isVisible = false;
          });
          this.image.categoryIds = [];
          this.$toastr.success(this.$t("annotator.cleared", { n: total }));
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.axiosReqestError(this.$t("toolbar.clearAnnotations"), data.message);
        });
    },
    runModelOnImage(options) {
      this.modelRunning = true;
      const done = () => (this.modelRunning = false);
      // Save first: the predictions are added on the server and the
      // annotations are then reloaded, so unsaved edits must not be lost.
      this.save(() => {
        axios
          .post(`/api/model/yolo/image/${this.image.id}`, options)
          .then(response => {
            const result = response.data;
            hideModal("#modelRunImage");
            this.$toastr.success(
              result.boxes != null
                ? this.$t("modelRun.inBoxes.done", { boxes: result.boxes, n: result.created })
                : this.$t("modelRun.imageDone", { n: result.created })
            );
            if (result.skipped_classes && result.skipped_classes.length) {
              this.$toastr.warning(
                this.$t("modelRun.skippedClasses", {
                  classes: result.skipped_classes.join(", ")
                })
              );
            }
            if (result.keypoints_mismatch && result.keypoints_mismatch.length) {
              this.$toastr.warning(
                this.$t("modelRun.keypointsMismatch", {
                  categories: result.keypoints_mismatch.join(", ")
                })
              );
            }
            if (result.created > 0) this.getData();
          })
          .catch(error => {
            const data = (error.response && error.response.data) || {};
            this.axiosReqestError(this.$t("modelRun.titleImage"), data.message);
          })
          .finally(done);
      }, { onError: done });
    },
    removeFromAnnotatingList() {
      if (this.user == null) return;

      var index = this.annotating.indexOf(this.user.username);
      //Remove self from list
      if (index > -1) {
        this.annotating.splice(index, 1);
      }
    },
    nextImage() {
      if (this.image.next == null || this.goingNext) return;
      const next = this.image.next;
      const bar = this.$refs.reviewBar;
      if (!bar || !bar.submitOnNext) {
        this.$refs.filetitle.route(next);
        return;
      }
      // save, submit if the switch is on, then move on
      this.goingNext = true;
      this.current.annotation = -1;
      this.$nextTick(() => {
        this.save(async () => {
          let answer = "next";
          try {
            // an empty image asks first; "stay" keeps this image open
            answer = await bar.submitBeforeNext();
          } finally {
            this.goingNext = false;
            if (answer !== "stay") this.$refs.filetitle.route(next);
          }
        }, { onError: () => (this.goingNext = false) });
      });
    },
    previousImage() {
      if(this.image.previous != null)
        this.$refs.filetitle.route(this.image.previous);
    }
  },
  watch: {
    soloCategory() {
      this.keepSolo();
    },
    review() {
      // marks of a rejection follow the status (drawn on load, gone when submitted)
      this.$nextTick(() => this.drawReviewMarks(false));
    },
    activeTool(tool) {
      if (tool === "Magic Wand") setTimeout(() => this.ensureImageData(), 0);
      if (tool === "BBox" || tool === "Rotated BBox") this.lastBoxTool = tool;
      if (tool !== "Keypoints") this.kpFlow = null;
      else this.boxFirst();
    },
    doneLoading(done) {
      if (done) {
        if (this.loading.loader) {
          this.loading.loader.hide();
        }
      }
    },
    currentCategory() {
      if (this.currentCategory != null) {
        if (
          this.currentAnnotation == null ||
          !this.currentCategory.showAnnotations
        ) {
          let element = this.currentCategory.$el;
          this.scrollElement(element);
        }
      }
    },
    currentAnnotation(newElement) {
      if (newElement != null) {
        if (newElement.showAnnotations) {
          let element = newElement.$el;
          this.scrollElement(element);
        }
      }
      // a new object with keypoints: its box comes first
      this.$nextTick(() => this.boxFirst());
    },
    "current.category"(cc) {
      if (cc < -1) this.current.category = -1;
      let max = this.categories.length;
      if (cc > max) {
        this.current.category = -1;
      }
      // working on another category: show everything again (what is drawn
      // there would be faded out otherwise)
      const c = this.categories[this.current.category];
      if (this.canvasPick) this.canvasPick = false;
      else this.drawCategoryId = c ? c.id : null;
      if (this.soloCategory != null && c && c.id !== this.soloCategory) this.soloCategory = null;
    },
    "current.annotation"(ca) {
      if (ca < -1) this.current.annotation = -1;
      if (this.currentCategory != null) {
        let max = this.currentAnnotationLength;
        if (ca > max) {
          this.current.annotations = -1;
        }
      }
    },
    "current.keypoint"(sk) {
      if (sk < -1) this.current.keypoint = -1;
      if (this.currentCategory != null) {
        let max = this.currentAnnotationLength;
        if (sk > max) {
          this.current.keypoint = -1;
        }
      }
    },
    annotating: {
      deep: true,
      handler() {
        this.removeFromAnnotatingList();
      }
    },
    user() {
      this.removeFromAnnotatingList();
    }
  },
  computed: {
    /** the category shown alone (others faded): hovered in the list, else kept */
    focusCategory() {
      return this.hoverCategory != null ? this.hoverCategory : this.soloCategory;
    },
    soloName() {
      const c = (this.categories || []).find(c => c.id === this.soloCategory);
      return c ? c.name : "";
    },
    /** parent heading above each category (computed once, not on every redraw) */
    /** questions need accounts (not with login turned off) */
    loginEnabledForHelp() {
      return !!this.$store.state.info.loginEnabled;
    },
    groupTitles() {
      const firsts = this.categories.map(c => parentsOf(c)[0] || "");
      if (!firsts.some(Boolean)) return this.categories.map(() => null);
      return firsts.map((p, i) => (i > 0 && firsts[i - 1] === p ? null : p));
    },
    doneLoading() {
      return !this.loading.image && !this.loading.data;
    },
    currentAnnotationLength() {
      if (this.currentCategory == null) return null;
      return this.currentCategory.category.annotations.length;
    },
    currentKeypointLength() {
      if (this.currentAnnotation == null) return null;
      return this.currentAnnotation.annotation.keypoints.length;
    },
    currentCategory() {
      return this.getCategory(this.current.category);
    },
    /** what the keypoint tool asks for: shown over the image */
    kpGuide() {
      if (this.activeTool !== "Keypoints") return null;
      const a = this.currentAnnotation;
      if (!a || !a.keypointLabels || !a.keypointLabels.length) return null;
      const total = a.keypointLabels.length;
      const left = Object.keys(a.notUsedKeypointLabels).length;
      const next = parseInt(a.keypoint.next.label);
      return {
        hasBox: !!(a.annotation.isbbox || a.annotation.isrbbox),
        total,
        done: total - left,
        skipped: a.kpSkipped.length,
        index: next > 0 ? next : null,
        name: next > 0 ? a.keypointLabels[next - 1] : null,
        color: next > 0 ? a.keypointColors[next - 1] : null
      };
    },
    currentAnnotation() {
      if (this.currentCategory == null) {
        return null;
      }
      return this.currentCategory.getAnnotation(this.current.annotation);
    },
    currentKeypoint() {
      if (this.currentCategory == null) {
        return null;
      }
      if (this.currentAnnotation == null 
      || this.currentAnnotation.keypointLabels.length === 0 
      || !this.currentAnnotation.showKeypoints)
      {
        return null;
      }
      if (this.current.keypoint == -1) {
        return null;
      }
      return {
        label: [String(this.current.keypoint + 1)],
        visibility: this.currentAnnotation.getKeypointVisibility(this.current.keypoint)
      };
    },
    user() {
      return this.$store.getters["user/user"];
    }
  },
  sockets: {
    annotating(data) {
      if (data.image_id !== this.image.id) return;

      if (data.active) {
        let found = this.annotating.indexOf(data.username);
        if (found < 0) {
          this.annotating.push(data.username);
        }
      } else {
        // not in the list (another tab already left): splice(-1) would drop someone else
        const found = this.annotating.indexOf(data.username);
        if (found >= 0) this.annotating.splice(found, 1);
      }
    }
  },
  beforeRouteLeave(to, from, next) {
    this.current.annotation = -1;

    this.$nextTick(() => {
      // only once really leaving: others then see this person stop
      const leave = () => {
        this.$socket.emit("annotating", { image_id: this.image.id, active: false });
        next();
      };
      // already chose to leave without the last changes
      if (this.leaveWithoutSaving) return leave();
      // a failed save keeps the page (and the edits) unless they choose to go
      this.saveIfChanged(leave, {
        onError: () => (window.confirm(this.$t("annotator.leaveUnsaved")) ? leave() : next(false))
      });
    });
  },
  mounted() {
    this.setDataset(null);

    // this.loading.loader = this.$loading.show({
    //   color: "white",
    //   // backgroundColor: "#4b5162",
    //   height: 150,
    //   opacity: 0.8,
    //   width: 150
    // });

    this.refsReady = true;

    // Pinch-to-zoom on touch devices
    this.hammer = new Hammer.Manager(this.$refs.frame);
    this.hammer.add(new Hammer.Pinch());
    this.hammer.on("pinchstart", this.onpinchstart);
    this.hammer.on("pinch", this.onpinch);

    this.initCanvas();
    this.getData();

    this.$socket.emit("annotating", { image_id: this.image.id, active: true });
    this.startIdleWatch();

    this.autosave.timer = setInterval(this.autosaveTick, 1000);
    window.addEventListener("beforeunload", this.onPageHide);
    // capture phase: seen before paper.js handles the press
    this.$refs.frame.addEventListener("mousedown", this.onChordDown, true);
    this.$refs.frame.addEventListener("mousedown", this.onDblPress, true);
    this.$refs.frame.addEventListener("dblclick", this.onCanvasDblClick);
    this.$refs.frame.addEventListener("contextmenu", this.onCanvasContextMenu);
    document.addEventListener("mouseup", this.onChordUp, true);
    window.addEventListener("blur", this.endChord);
    document.addEventListener("visibilitychange", this.onPageHide);
  },
  beforeUnmount() {
    this.stopIdleWatch();
    if (this.hammer) this.hammer.destroy();
    clearInterval(this.autosave.timer);
    window.removeEventListener("beforeunload", this.onPageHide);
    if (this.$refs.frame) {
      this.$refs.frame.removeEventListener("mousedown", this.onChordDown, true);
      this.$refs.frame.removeEventListener("mousedown", this.onDblPress, true);
      this.$refs.frame.removeEventListener("dblclick", this.onCanvasDblClick);
      this.$refs.frame.removeEventListener("contextmenu", this.onCanvasContextMenu);
    }
    document.removeEventListener("mouseup", this.onChordUp, true);
    window.removeEventListener("blur", this.endChord);
    document.removeEventListener("visibilitychange", this.onPageHide);
  },
  created() {
    // undo actions belong to the image they were made on
    this.resetUndo();
    this.paper = new paper.PaperScope();

    this.image.id = parseInt(this.identifier);
    this.image.url = "/api/image/" + this.image.id;
  }
};
</script>

<style scoped>
.solo-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 6px;
  padding: 3px 6px 3px 10px;
  border-radius: 999px;
  background: rgba(255, 193, 7, 0.15);
  border: 1px solid #ffc107;
  color: #fff;
  font-size: 0.8rem;
}
.solo-tag .btn-close {
  margin-left: auto;
  font-size: 0.6rem;
}
.alert {
  bottom: 0;
  width: 50%;
  display: block;
  margin-left: auto;
  margin-right: auto;
}

/* width */
::-webkit-scrollbar {
  width: 7px;
}

/* Track */
::-webkit-scrollbar-track {
  box-shadow: inset 0 0 5px grey;
  border-radius: 10px;
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: white;
  border-radius: 10px;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #9feeb0;
}

.left-panel {
  background-color: #4b5162;
  width: 40px;
  padding-top: 40px;
  float: left;
  height: 100%;
  box-shadow: 5px 10px;
}

/* a column: the category list takes the space left and scrolls inside, so
   what happens in it (a new annotation, a category opening) never moves the
   tool panel or the rest of the page */
.right-panel {
  padding-top: 40px;
  background-color: #4b5162;
  width: 250px;
  height: inherit;
  float: right;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.right-panel > * {
  flex: 0 0 auto;
}
.right-panel > .sidebar-section {
  flex: 1 1 auto;
  min-height: 80px;
}
.tool-area .tool-section {
  max-height: 30vh;
}

.kp-guide {
  position: absolute;
  /* the top of this panel is under the navigation bar */
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: calc(100% - 20px);
  padding: 6px 8px 6px 12px;
  border-radius: 20px;
  background: rgba(33, 37, 41, 0.88);
  color: #fff;
  font-size: 0.85rem;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.kp-guide .kp-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
  flex: none;
}
.kp-guide .kp-name {
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kp-guide .kp-count {
  color: #adb5bd;
  font-variant-numeric: tabular-nums;
}
.kp-guide .btn {
  padding: 1px 10px;
  border-radius: 14px;
  font-size: 0.8rem;
}
.kp-guide kbd {
  font-size: 0.7rem;
  padding: 0 4px;
  background: rgba(0, 0, 0, 0.15);
  color: inherit;
}
.middle-panel {
  display: block;
  width: inherit;
  height: inherit;
  background-color: #7c818c;
  overflow: hidden;
  position: relative;
}

.frame {
  margin: 0;
  width: 100%;
  height: 100%;
}

.canvas {
  display: block;
  width: 100%;
  height: 100%;
}

#image {
  position: absolute;
}

.parent-title {
  color: #9ec5fe;
  font-size: 11px;
  text-align: left;
  padding: 6px 4px 2px;
  text-transform: none;
  border-bottom: 1px solid #495057;
  margin-bottom: 2px;
}

.sidebar-section {
  width: 100%;
  padding-left: 5px;
  padding-right: 5px;
  overflow: auto;
}

.sidebar-title {
  color: white;
}

/* Tool section */
.tool-section {
  margin: 5px;
  border-radius: 5px;
  background-color: #383c4a;
  padding: 0 5px 5px 5px;
  overflow: auto;
}

/* Categories/Annotations section */
.meta-input {
  padding: 3px;
  background-color: inherit;
  width: 100%;
  height: 100%;
  border: none;
}

.meta-item {
  background-color: inherit;
  height: 30px;
  border: none;
}

.status-icon {
  font-size: 150px;
  color: white;
  position: absolute;
  left: calc(50% - 75px);
  top: calc(50% - 75px);
}

.search {
  width: 100%;
  height: 18px;
  color: white;
  background-color: rgba(255, 255, 255, 0.1);
  border: none;
  text-align: center;
  border-radius: 4px;
}
</style>
