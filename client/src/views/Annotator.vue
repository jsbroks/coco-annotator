<template>
  <div style="display: block; height: inherit;">
    <aside v-show="panels.show.left" class="left-panel shadow-lg">
      
      <div v-show="mode == 'segment'">
        <hr>
        
        <SelectTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="select" />
        <hr>

        <PolygonTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="polygon" />
        <MagicWandTool v-model="activeTool" :raster="image.raster" @setcursor="setCursor" ref="magicwand" />

        <BrushTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="brush" />
        <EraserTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="eraser" />
      </div>
      <hr>

      <div v-show="mode == 'segment'">
        <CopyAnnotationsButton :categories="categories" :image-id="image.id" :next="image.next" :previous="image.previous"/>
        <ShowAllButton />
        <HideAllButton />
      </div>
      
      <CenterButton />
      <UndoButton />

      <hr>

      <DownloadButton :image="image" />
      <SaveButton />
      <ModeButton v-model="mode"/>
      <SettingsButton :metadata="image.metadata" :commands="commands" ref="settings" />

      <hr>
      <DeleteButton :image="image" />

    </aside>

    <aside v-show="panels.show.right" class="right-panel shadow-lg">
      <hr>
      <FileTitle :previousimage="image.previous" :nextimage="image.next" :filename="image.filename" />

      <div v-if="categories.length > 5">
        <div style="padding: 0px 5px">
          <input v-model="search" class="search" placeholder="Category Search">
        </div>
      </div>
      
      <div class="sidebar-section" :style="{'max-height': mode == 'label' ? '100%': '57%'}">
        <p v-if="categories.length == 0" style="color: lightgray; font-size: 12px">
          No categories have been added to this image.
        </p>

        <div v-show="mode == 'segment'" style="overflow: auto; max-height: 100%">
          <Category v-for="(category, index) in categories" :key="category.id + '-category'" :simplify="simplify" :categorysearch="search" :category="category" :opacity="shapeOpacity" :hover="hover" :index="index" @click="onCategoryClick" :current="current" ref="category" />
        </div>

        <div v-show="mode == 'label'" style="overflow: auto; max-height: 100%">
          <CLabel v-for="category in categories" v-model="image.categoryIds" :key="category.id + '-label'" :category="category" :search="search"/>
        </div>
      </div>

      <div v-show="mode == 'segment'">
        <hr>
        <h6 class="sidebar-title text-center">{{ activeTool }}</h6>

        <div class="tool-section" style="max-height: 30%; color: lightgray">

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

        </div>
      </div>
    </aside>

    <div class="middle-panel" :style="{ cursor: cursor }">
      <div id="frame" class="frame" @wheel="onwheel">
        <canvas class="canvas" id="editor" ref="image" resize />
      </div>

      <!-- <div v-show="!doneLoading">
        <i class="fa fa-spinner fa-pulse fa-x fa-fw status-icon"></i>
      </div> -->

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

import PolygonTool from "@/components/annotator/tools/PolygonTool";
import SelectTool from "@/components/annotator/tools/SelectTool";
import MagicWandTool from "@/components/annotator/tools/MagicWandTool";
import EraserTool from "@/components/annotator/tools/EraserTool";
import BrushTool from "@/components/annotator/tools/BrushTool";

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

import PolygonPanel from "@/components/annotator/panels/PolygonPanel";
import SelectPanel from "@/components/annotator/panels/SelectPanel";
import MagicWandPanel from "@/components/annotator/panels/MagicWandPanel";
import BrushPanel from "@/components/annotator/panels/BrushPanel";
import EraserPanel from "@/components/annotator/panels/EraserPanel";

import { mapMutations } from "vuex";

export default {
  name: "Annotator",
  components: {
    FileTitle,
    CopyAnnotationsButton,
    Category,
    CLabel: Label,
    PolygonTool,
    PolygonPanel,
    SelectTool,
    MagicWandTool,
    EraserTool,
    BrushTool,
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
    ShowAllButton
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
      shapeOpacity: 0.5,
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
        categoryIds: []
      },
      categories: [],
      dataset: {},
      loading: {
        image: true,
        data: true,
        loader: null
      },
      search: ""
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess", "resetUndo"]),
    save(callback) {
      let process = "Saving";
      this.addProcess(process);
      let refs = this.$refs;

      let data = {
        mode: this.mode,
        user: {
          polygon: this.$refs.polygon.export(),
          eraser: this.$refs.eraser.export(),
          brush: this.$refs.brush.export(),
          magicwand: this.$refs.magicwand.export(),
          select: this.$refs.select.export(),
          settings: this.$refs.settings.export()
        },
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
          this.removeProcess(process);
          //TODO: updateUser
          if (callback != null) callback();
        })
        .catch(() => {});
    },
    onwheel(e) {
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
          this.image.scale = 1 / this.paper.view.zoom;
          this.paper.view.zoom = transform.zoom;
          this.paper.view.center = view.center.add(transform.offset);
        }
      }

      e.preventDefault();
      return false;
    },
    fit: function() {
      let canvas = document.getElementById("editor");

      let parentX = this.image.raster.width;
      let parentY = this.image.raster.height;

      this.paper.view.zoom = Math.min(
        (canvas.width / parentX) * 0.95,
        (canvas.height / parentY) * 0.85
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
      4;
      let canvas = document.getElementById("editor");
      this.paper.setup(canvas);
      this.paper.view.viewSize = [
        this.paper.view.size.width,
        window.innerHeight
      ];
      this.paper.activate();
      let img = new Image();
      img.onload = () => {
        // Create image object
        this.image.raster = new paper.Raster({
          source: this.image.url,
          position: new paper.Point(0, 0)
        });
        this.image.raster.sendToBack();
        this.fit();
        this.image.ratio =
          (this.image.raster.width * this.image.raster.height) / 1000000;
        this.removeProcess(process);
        this.loading.image = false;
      };
      img.src = this.image.url;
    },
    getData(callback) {
      let process = "Loading annotation data";
      this.addProcess(process);
      this.loading.data = true;
      axios
        .get("/api/annotator/data/" + this.image.id)
        .then(response => {
          // Set image data
          this.image.metadata = response.data.image.metadata || {};
          this.image.filename = response.data.image.file_name;
          this.image.next = response.data.image.next;
          this.image.previous = response.data.image.previous;
          this.image.categoryIds = response.data.image.category_ids || [];

          // Set other data
          this.dataset = response.data.dataset;
          this.categories = response.data.categories;

          // Update status
          this.removeProcess(process);
          this.loading.data = false;

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
        });
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
    uniteCurrentAnnotation(compound, simplify = true, undoable = true) {
      if (this.currentAnnotation == null) return;
      this.currentAnnotation.unite(compound, simplify, undoable);
    },
    subtractCurrentAnnotation(compound, simplify = true, undoable = true) {
      if (this.currentCategory == null) return;
      this.currentAnnotation.subtract(compound, simplify, undoable);
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
          // If at a category which has annotations showing, go though annotations
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
    }
  },
  watch: {
    doneLoading() {
      if (this.loading.loader) {
        this.loading.loader.hide();
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
    currentAnnotation() {
      if (this.currentAnnotation != null) {
        if (this.currentCategory.showAnnotations) {
          let element = this.currentAnnotation.$el;
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
      return this.$store.user.user;
    }
  },
  beforeRouteLeave(to, from, next) {
    this.save(next);
  },
  mounted() {
    this.loading.loader = this.$loading.show({
      color: "white",
      backgroundColor: "#4b5162",
      height: 150,
      opacity: 0.7,
      width: 150
    });

    this.initCanvas();
  },
  created() {
    this.paper = new paper.PaperScope();

    this.image.id = parseInt(this.identifier);
    this.image.url = "/api/image/" + this.image.id;

    this.getData();
  },
  destroyed() {
    clearInterval(this.autoSave);
  }
};
</script>


<style scoped>
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
