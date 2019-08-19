<template>
  <div style="display: block; height: inherit;">
    
    <aside v-show="panels.show.left" class="left-panel shadow-lg">
      <div v-show="mode == 'segment'">
        <hr />

        <SelectTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="select"
        />
        <hr />

        <BBoxTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="bbox"
        />

        <PolygonTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="polygon"
        />

        <MagicWandTool
          v-model="activeTool"
          :width="image.raster.width"
          :height="image.raster.height"
          :image-data="image.data"
          @setcursor="setCursor"
          ref="magicwand"
        />

        <BrushTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="brush"
        />
        <EraserTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="eraser"
        />

        <KeypointTool
          v-model="activeTool"
          @setcursor="setCursor"
          ref="keypoint"
        />
        <DEXTRTool
          v-model="activeTool"
          :scale="image.scale"
          @setcursor="setCursor"
          ref="dextr"
        />
      </div>
      <hr />

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
      </div>
      <hr>
      <CenterButton />
      <UndoButton />

      <hr />

      <DownloadButton :image="image" />
      <SaveButton />
      <ModeButton v-model="mode" />
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

      <div v-if="categories.length > 5">
        <div style="padding: 0px 5px">
          <input
            v-model="search"
            class="search"
            placeholder="Category Search"
          />
        </div>
      </div>

      <div
        class="sidebar-section"
        :style="{ 'max-height': mode == 'label' ? '100%' : '57%' }"
      >
        <p
          v-if="categories.length == 0"
          style="color: lightgray; font-size: 12px"
        >
          No categories have been enabled for this image.
        </p>

        <div
          v-show="mode == 'segment'"
          style="overflow: auto; max-height: 100%"
        >
          <Category
            v-for="(category, index) in categories"
            :key="category.id + '-category'"
            :simplify="simplify"
            :categorysearch="search"
            :category="category"
            :all-categories="categories"
            :opacity="shapeOpacity"
            :hover="hover"
            :index="index"
            @click="onCategoryClick"
            :current="current"
            :active-tool="activeTool"
            :scale="image.scale"
            ref="category"
          />
        </div>

        <div v-show="mode == 'label'" style="overflow: auto; max-height: 100%">
          <CLabel
            v-for="category in categories"
            v-model="image.categoryIds"
            :key="category.id + '-label'"
            :category="category"
            :search="search"
          />
        </div>
      </div>

      <div v-show="mode == 'segment'">
        <hr />
        <h6 class="sidebar-title text-center">{{ activeTool }}</h6>

        <div class="tool-section" style="max-height: 30%; color: lightgray">
          <div v-if="$refs.bbox != null">
            <BBoxPanel :bbox="$refs.bbox" />
          </div>
          <div v-if="$refs.polygon != null">
            <PolygonPanel :polygon="$refs.polygon" />
          </div>

          <div v-if="$refs.select != null">
            <SelectPanel :select="$refs.select" />
          </div>

          <div v-if="$refs.magicwand != null">
            <MagicWandPanel :magicwand="$refs.magicwand" />
          </div>

          <div v-if="$refs.brush != null">
            <BrushPanel :brush="$refs.brush" />
          </div>

          <div v-if="$refs.eraser != null">
            <EraserPanel :eraser="$refs.eraser" />
          </div>

          <div v-if="$refs.keypoint != null">
            <KeypointPanel
              :keypoint="$refs.keypoint"
              :current-annotation="currentAnnotation"
            />
          </div>
          <div v-if="$refs.dextr != null">
            <DEXTRPanel
              :dextr="$refs.dextr"
            />
          </div>
        </div>
      </div>
    </aside>

    <div class="middle-panel" :style="{ cursor: cursor }">
      <div id="frame" class="frame" @wheel="onwheel">
        <canvas class="canvas" id="editor" ref="image" resize />
      </div>
    </div>

    <div v-show="annotating.length > 0" class="fixed-bottom alert alert-warning alert-dismissible fade show">
      <span>
      This image is being annotated by <b>{{ annotating.join(', ') }}</b>.
      </span>
      
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  </div>
</template>

<script>
import paper from "paper";
import axios from "axios";

import toastrs from "@/mixins/toastrs";
import shortcuts from "@/mixins/shortcuts";

import FileTitle from "@/components/annotator/FileTitle";
import Category from "@/components/annotator/Category";
import Label from "@/components/annotator/Label";
import Annotations from "@/models/annotations";

import PolygonTool from "@/components/annotator/tools/PolygonTool";
import BBoxTool from "@/components/annotator/tools/BBoxTool";
import SelectTool from "@/components/annotator/tools/SelectTool";
import MagicWandTool from "@/components/annotator/tools/MagicWandTool";
import EraserTool from "@/components/annotator/tools/EraserTool";
import BrushTool from "@/components/annotator/tools/BrushTool";
import KeypointTool from "@/components/annotator/tools/KeypointTool";
import DEXTRTool from "@/components/annotator/tools/DEXTRTool";

import CopyAnnotationsButton from "@/components/annotator/tools/CopyAnnotationsButton";
import CenterButton from "@/components/annotator/tools/CenterButton";
import DownloadButton from "@/components/annotator/tools/DownloadButton";
import SaveButton from "@/components/annotator/tools/SaveButton";
import SettingsButton from "@/components/annotator/tools/SettingsButton";
import ModeButton from "@/components/annotator/tools/ModeButton";
import DeleteButton from "@/components/annotator/tools/DeleteButton";
import UndoButton from "@/components/annotator/tools/UndoButton";
import ShowAllButton from "@/components/annotator/tools/ShowAllButton";
import HideAllButton from "@/components/annotator/tools/HideAllButton";
import AnnotateButton from "@/components/annotator/tools/AnnotateButton";

import PolygonPanel from "@/components/annotator/panels/PolygonPanel";
import BBoxPanel from "@/components/annotator/panels/BBoxPanel";
import SelectPanel from "@/components/annotator/panels/SelectPanel";
import MagicWandPanel from "@/components/annotator/panels/MagicWandPanel";
import BrushPanel from "@/components/annotator/panels/BrushPanel";
import EraserPanel from "@/components/annotator/panels/EraserPanel";
import KeypointPanel from "@/components/annotator/panels/KeypointPanel";
import DEXTRPanel from "@/components/annotator/panels/DEXTRPanel";

import { mapMutations } from "vuex";

export default {
  name: "Annotator",
  components: {
    FileTitle,
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
    KeypointPanel,
    AnnotateButton,
    DEXTRTool,
    DEXTRPanel
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
      activeTool: "Select",
      paper: null,
      shapeOpacity: 0.6,
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
        annotation: -1
      },
      hover: {
        category: -1,
        annotation: -1
      },
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
      annotating: []
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess", "resetUndo", "setDataset"]),
    save(callback) {
      let process = "Saving";
      this.addProcess(process);
      let refs = this.$refs;

      let data = {
        mode: this.mode,
        user: {
          bbox: this.$refs.bbox.export(),
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
        this.image.categoryIds = [];
        refs.category.forEach(category => {
          let categoryData = category.export();
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

      axios
        .post("/api/annotator/data", JSON.stringify(data))
        .then(() => {
          //TODO: updateUser
          if (callback != null) callback();
        })
        .finally(() => this.removeProcess(process));
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

        let tempCtx = document.createElement("canvas").getContext("2d");
        tempCtx.canvas.width = width;
        tempCtx.canvas.height = height;
        tempCtx.drawImage(this.image.raster.image, 0, 0);

        this.image.data = tempCtx.getImageData(0, 0, width, height);
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
    setPreferences(preferences) {
      let refs = this.$refs;

      refs.bbox.setPreferences(preferences.bbox || preferences.polygon || {});
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
          // Set image data
          this.image.metadata = data.image.metadata || {};
          this.image.filename = data.image.file_name;
          this.image.next = data.image.next;
          this.image.previous = data.image.previous;
          this.image.categoryIds = data.image.category_ids || [];

          this.annotating = data.image.annotating || [];

          // Set other data
          this.dataset = data.dataset;
          this.categories = data.categories;

          // Update status

          this.setDataset(this.dataset);

          let preferences = data.preferences;
          this.setPreferences(preferences);

          if (this.text.topLeft != null) {
            this.text.topLeft.content = this.image.filename;
          }

          this.$nextTick(() => {
            this.showAll();
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
      this.current.annotation = indices.annotation;
      this.current.category = indices.category;
    },
    getCategory(index) {
      if (index == null) return null;
      if (index < 0) return null;

      let ref = this.$refs.category;

      if (ref == null) return null;
      if (ref.length < 1 || index >= ref.length) return null;

      return this.$refs.category[index];
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

    selectLastEditorTool() {
      this.activeTool = localStorage.getItem("editorTool") || "Select";
    },

    setCursor(newCursor) {
      this.cursor = newCursor;
    },
    moveUp() {
      if (this.current.category < 0) {
        this.current.category = this.categories.length - 1;
        return;
      }

      if (this.currentCategory != null) {
        if (this.currentAnnotation != null) {
          // If at start of annotations, go to pervious category
          if (this.current.annotation === 0) {
            this.current.category -= 1;
            // Check if category is open so we can go to the bottom annotation
            if (
              this.currentCategory != null &&
              this.currentCategory.showAnnotations
            ) {
              this.current.annotation = this.currentAnnotationLength - 1;
            }
          } else {
            // otherwise go to pervious annotation
            this.current.annotation -= 1;
          }
        } else {
          // When the new annotation is added, the currentAnnotation
          // is null since the annotations are not instantly loaded in
          if (
            this.current.annotation !== -1 &&
            this.current.annotation < this.currentAnnotationLength
          ) {
            this.current.annotation -= 1;
          } else {
            this.current.category -= 1;

            // Check if category is open so we can go to the bottom annotation
            if (
              this.currentCategory != null &&
              this.currentCategory.showAnnotations
            ) {
              this.current.annotation = this.currentAnnotationLength - 1;
            }
          }
        }
      } else {
        this.current.category -= 1;
      }
    },
    moveDown() {
      if (this.currentCategory == null) {
        this.current.category = 0;
        return;
      }

      if (this.currentCategory != null) {
        let numOfAnnotaitons = this.currentCategory.category.annotations.length;

        if (this.currentAnnotation != null) {
          // If at end of annotations, go to next category
          if (numOfAnnotaitons - 1 === this.current.annotation) {
            this.current.annotation = -1;
            this.current.category += 1;

            if (
              this.currentCategory != null &&
              this.currentCategory.showAnnotations
            ) {
              this.current.annotation = 0;
            }
          } else {
            // otherwise go to next annotation
            this.current.annotation += 1;
          }
        } else {
          // If at a category which has annotations showing, go through annotations
          this.current.category += 1;
          if (
            this.currentCategory != null &&
            this.currentCategory.showAnnotations
          ) {
            this.current.annotation = 0;
          }
        }
      } else {
        this.current.category += 1;
      }
    },
    stepIn() {
      if (this.currentCategory != null) {
        if (!this.currentCategory.isVisible) {
          this.currentCategory.isVisible = true;
        } else if (
          !this.currentCategory.showAnnotations &&
          this.currentAnnotationLength > 0
        ) {
          this.currentCategory.showAnnotations = true;
          this.current.annotation = 0;
        }
      }
    },
    stepOut() {
      if (this.currentCategory != null) {
        if (this.currentCategory.showAnnotations) {
          this.currentCategory.showAnnotations = false;
          this.current.annotation = -1;
        } else if (this.currentCategory.isVisible) {
          this.currentCategory.isVisible = false;
        }
      }
    },
    scrollElement(element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    },
    showAll() {
      if (this.$refs.category == null) return;

      this.$refs.category.forEach(category => {
        category.isVisible = category.category.annotations.length > 0;
      });
    },
    hideAll() {
      if (this.$refs.category == null) return;

      this.$refs.category.forEach(category => {
        category.isVisible = false;
        category.showAnnotations = false;
      });
    },
    findCategoryByName(categoryName) {
      let categoryComponent = this.$refs.category.find(
        category =>
          category.category.name.toLowerCase() === categoryName.toLowerCase()
      );
      if (!categoryComponent) return null;
      return categoryComponent.category;
    },
    addAnnotation(categoryName, segments, keypoints) {
      segments = segments || [];
      keypoints = keypoints || [];

      if (keypoints.length == 0 && segments.length == 0) return;

      let category = this.findCategoryByName(categoryName);
      if (category == null) return;

      Annotations.create({
        image_id: this.image.id,
        category_id: category.id,
        segmentation: segments,
        keypoints: keypoints
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

    removeFromAnnotatingList() {
      if (this.user == null) return;

      var index = this.annotating.indexOf(this.user.username);
      //Remove self from list
      if (index > -1) {
        this.annotating.splice(index, 1);
      }
    },
    nextImage() {
      if(this.image.next != null)
        this.$refs.filetitle.route(this.image.next);
    },
    previousImage() {
      if(this.image.previous != null)
        this.$refs.filetitle.route(this.image.previous);
    }
  },
  watch: {
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
    },
    "current.category"(cc) {
      if (cc < -1) this.current.category = -1;
      let max = this.categories.length;
      if (cc > max) {
        this.current.category = -1;
      }
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
    annotating() {
      this.removeFromAnnotatingList();
    },
    user() {
      this.removeFromAnnotatingList();
    }
  },
  computed: {
    doneLoading() {
      return !this.loading.image && !this.loading.data;
    },
    currentAnnotationLength() {
      if (this.currentCategory == null) return null;
      return this.currentCategory.category.annotations.length;
    },
    currentCategory() {
      return this.getCategory(this.current.category);
    },
    currentAnnotation() {
      if (this.currentCategory == null) {
        return null;
      }
      return this.currentCategory.getAnnotation(this.current.annotation);
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
        this.annotating.splice(this.annotating.indexOf(data.username), 1);
      }
    }
  },
  beforeRouteLeave(to, from, next) {
    this.current.annotation = -1;

    this.$nextTick(() => {
      this.$socket.emit("annotating", {
        image_id: this.image.id,
        active: false
      });
      this.save(next);
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

    this.initCanvas();
    this.getData();

    this.$socket.emit("annotating", { image_id: this.image.id, active: true });
  },
  created() {
    this.paper = new paper.PaperScope();

    this.image.id = parseInt(this.identifier);
    this.image.url = "/api/image/" + this.image.id;
  }
};
</script>

<style scoped>
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

.right-panel {
  padding-top: 40px;
  background-color: #4b5162;
  width: 250px;
  height: inherit;
  float: right;
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
