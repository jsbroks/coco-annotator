<template>
  <div style="display: block; height: inherit;">
    <aside v-show="panels.show.left" class="left-panel shadow-lg">
      <hr>

      <SelectTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="select" />

      <hr>

      <PolygonTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="polygon" />
      <MagicWandTool v-model="activeTool" :raster="image.raster" @setcursor="setCursor" ref="magicwand" />

      <BrushTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="brush" />
      <EraserTool v-model="activeTool" :scale="image.scale" @setcursor="setCursor" ref="eraser" />
      <hr>

      <CenterButton />

      <hr>

      <DownloadButton :image="image" />
      <SaveButton />
      <SettingsButton :metadata="image.metadata" :commands="commands" ref="settings" />

      <hr>
      <DeleteButton :image="image" />

    </aside>

    <aside v-show="panels.show.right" class="right-panel shadow-lg">
      <hr>
      <FileTitle :previousimage="image.previous" :nextimage="image.next" :filename="image.filename" />

      <div class="sidebar-section" style="max-height: 57%">
        <p v-if="categories.length == 0" style="color: lightgray; font-size: 12px">
          No categories have been added to this image.
        </p>
        <div v-else id="accordion" style="overflow: auto; max-height: 100%">
          <Category v-for="(category, index) in categories" :key="category.id + '-category'" :category="category" :opacity="shapeOpacity" :hover="hover" :index="index" @click="onCategoryClick" :current="current" ref="category" />
        </div>
      </div>
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
    </aside>

    <div class="middle-panel" :style="{ cursor: cursor }">
      <div id="frame" class="frame" @wheel="onwheel">
        <canvas class="canvas" id="editor" ref="image" resize />
      </div>
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

import PolygonTool from "@/components/annotator/tools/PolygonTool";
import SelectTool from "@/components/annotator/tools/SelectTool";
import MagicWandTool from "@/components/annotator/tools/MagicWandTool";
import EraserTool from "@/components/annotator/tools/EraserTool";
import BrushTool from "@/components/annotator/tools/BrushTool";

import CenterButton from "@/components/annotator/tools/CenterButton";

import DownloadButton from "@/components/annotator/tools/DownloadButton";
import SaveButton from "@/components/annotator/tools/SaveButton";
import SettingsButton from "@/components/annotator/tools/SettingsButton";
import DeleteButton from "@/components/annotator/tools/DeleteButton";

import PolygonPanel from "@/components/annotator/panels/PolygonPanel";
import SelectPanel from "@/components/annotator/panels/SelectPanel";
import MagicWandPanel from "@/components/annotator/panels/MagicWandPanel";
import BrushPanel from "@/components/annotator/panels/BrushPanel";
import EraserPanel from "@/components/annotator/panels/EraserPanel";

export default {
  name: "Annotator",
  components: {
    FileTitle,
    Category,
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
    EraserPanel
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
        showText: true,
        text: null,
        box: null,
        textShift: 0,
        fontSize: 0,
        shift: 0,
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
        filename: ""
      },
      categories: [],
      dataset: {}
    };
  },
  methods: {
    save(callback) {
      let refs = this.$refs;

      let data = {
        user: {
          keyboardShortcuts: []
        },
        image: {
          id: this.image.id,
          metadata: this.$refs.settings.exportMetadata(),
          settings: {
            selectedLayers: this.current
          }
        },
        settings: {
          activeTool: this.activeTool,
          zoom: this.zoom,
          tools: {}
        },
        categories: []
      };

      if (refs.category != null) {
        refs.category.forEach(category => {
          data.categories.push(category.export());
        });
      }

      axios
        .post("/api/annotator/data", JSON.stringify(data))
        .then(() => {
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
      let canvas = document.getElementById("editor");

      this.paper.setup(canvas);
      this.paper.view.viewSize = [
        this.paper.view.size.width,
        window.innerHeight
      ];

      this.paper.activate();

      let img = new Image();
      //this.status.image.state = false;

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

        //this.status.image.state = true;
      };
      img.src = this.image.url;
    },
    getData(callback) {
      //this.status.data.state = false;

      axios
        .get("/api/annotator/data/" + this.image.id)
        .then(response => {
          // Set image data
          this.image.metadata = response.data.image.metadata;
          this.image.filename = response.data.image.file_name;
          this.image.next = response.data.image.next;
          this.image.previous = response.data.image.previous;

          // Set other data
          this.dataset = response.data.dataset;
          this.categories = response.data.categories;

          // Update status
          //this.status.data.state = true;
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
      if (
        this.current.annotation === indices.annotation &&
        this.current.category === indices.category
      ) {
        this.current = { category: -1, annotation: -1 };
      } else {
        this.current = indices;
      }
    },
    getCategory: function(index) {
      if (index == null) return null;
      if (index < 0) return null;

      let ref = this.$refs.category;

      if (ref == null) return null;
      if (ref.length < 1 || index >= ref.length) return null;

      return this.$refs.category[index];
    },
    // Current Annotation Operations
    uniteCurrentAnnotation(compound, flatten) {
      let category = this.current.category;
      let annotation = this.current.annotation;

      if (category === -1) return;
      if (annotation === -1) return;

      this.getCategory(category)
        .getAnnotation(annotation)
        .unite(compound, flatten);
    },
    subtractCurrentAnnotation(compound, flatten) {
      let category = this.current.category;
      let annotation = this.current.annotation;

      if (category === -1) return;
      if (annotation === -1) return;

      this.getCategory(category)
        .getAnnotation(annotation)
        .subtract(compound, flatten);
    },

    setCursor(newCursor) {
      this.cursor = newCursor;
    }
  },
  beforeRouteUpdate(to, from, next) {
    this.current.annotation = -1;
    this.image.id = parseInt(to.params.identifier);
    this.image.url = "/api/image/" + this.image.id;
    this.initCanvas();
    this.getData();

    next();
  },
  mounted() {
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

.tool-input-group {
  padding-top: 4px;
}

.tool-input-button {
  height: 20px;
  border-color: #4b5162;
  padding: 0 0 0 11px;
  font-size: 12px;
  width: 100%;
}

.tool-input-button:hover {
  border-color: lightgray;
  background-color: white;
}

.tool-option-pre {
  background-color: #383c4a;
  height: 20px;
}

.tool-option-font {
  border-color: #4b5162;
  background-color: #383c4a;
  color: white;
  font-size: 12px;
}

.tool-option-input {
  border-color: #4b5162;
  color: white;
  padding: 0 0 0 3px;
  background-color: #383c4a;
  height: 20px;
  font-size: 12px;
  width: 100%;
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
</style>
