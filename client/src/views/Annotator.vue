<template>
  <div style="display: block; height: inherit;">
    <aside 
      v-show="panels.show.left" 
      class="left-panel shadow-lg"
    >
      <ToolBar 
        v-model="activeTool" 
        ref="toolBar" 
        :current="current"
      />
    </aside>

    <aside 
      v-show="panels.show.right" 
      class="right-panel shadow-lg"
    >
      <hr>
      <div />
    </aside>

    <div class="middle-panel">
      <div 
        id="frame"
        class="frame" 
        @wheel="onwheel"
      >
        <canvas
          class="canvas"
          id="editor"
          ref="image" 
          resize
        />
      </div>
    </div>
  </div>
</template>

<script>
import paper from "paper";
import axios from "axios";

import ToolBar from "@/components/annotator/ToolBar";

export default {
  name: "Annotator",
  components: { ToolBar },
  data() {
    return {
      activeTool: "Select",
      paper: null,
      current: {
        category: -1,
        annotation: -1
      },
      zoom: 0.2,
      panels: {
        show: {
          left: true,
          right: true
        }
      },
      image: {
        scale: 0,
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
      dataset: {},
      keys: {
        ctrl: false,
        shift: false
      }
    };
  },
  methods: {
    onwheel(e) {
      let view = this.paper.view;

      if (this.keys.ctrl) {
        // Pan up and down
        let delta = new paper.Point(0, 0.5 * e.deltaY);
        this.paper.view.setCenter(view.center.add(delta));
      } else if (this.keys.shift) {
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
    onkeydown(e) {
      //let activeTool = this.activeTool;

      let key = e.key.toLowerCase();

      if (key === "control") this.keys.ctrl = true;
      if (key === "shift") this.keys.shift = true;

      // Action shortcuts
      if (key === "r" && this.keys.ctrl) location.reload();
    },
    onkeyup(e) {
      let key = e.key.toLowerCase();

      if (key === "control") this.keys.ctrl = false;
      if (key === "shift") this.keys.shift = false;

      e.preventDefault();
      return false;
    },
    initCanvas() {
      let canvas = document.getElementById("editor");

      this.paper = new paper.PaperScope();
      this.paper.setup(canvas);
      this.paper.view.viewSize = [
        this.paper.view.size.width,
        window.innerHeight
      ];

      this.paper.activate();

      let img = new Image();
      //this.status.image.state = false;

      img.onload = () => {
        this.image.raster = new paper.Raster({
          source: this.image.url,
          position: new paper.Point(0, 0)
        });

        this.image.raster.sendToBack();
        this.fit();
        //tools.initTools(this);

        let categories = this.$refs.category;
        if (categories != null) {
          categories.forEach(category => {
            category.initCategory();
          });
        }

        this.image.ratio =
          (this.image.raster.width * this.image.raster.height) / 1000000;

        //this.status.image.state = true;
      };
      img.src = this.image.url;
    },
    getData() {
      //this.status.data.state = false;

      axios.get("/api/annotator/data/" + this.image.id).then(response => {
        // Set image data
        this.image.metadata = response.data.image.metadata;
        this.image.filename = response.data.image.file_name;
        this.image.categories = response.data.image.categories;
        this.image.next = response.data.image.next;
        this.image.previous = response.data.image.previous;

        // Set other data
        this.dataset = response.data.dataset;
        this.categories = response.data.categories;

        // Update status
        //this.status.data.state = true;
      });
    }
  },
  mounted() {
    this.initCanvas();

    window.addEventListener("keyup", (this.onKeyup = this.onkeyup.bind(this)));
    window.addEventListener(
      "keydown",
      (this.onKeydown = this.onkeydown.bind(this))
    );
  },
  created() {
    paper.install(window);

    this.image.id = parseInt(this.$route.params.id);
    this.image.url = "/api/image/" + this.image.id;

    this.getData();
  },
  destroyed() {
    window.removeEventListener("keydown", this.onKeydown);
    window.removeEventListener("keydup", this.onKeyup);
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

/* Images Section*/

/* Categories/Annotations section */

.category-icon {
  display: block;
  float: left;
  margin: 0;
  padding: 5px 10px 5px 10px;
}

.annotation-icon {
  margin: 0;
  padding: 3px;
}

.list-group-item {
  height: 21px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}

.card {
  background-color: #404552;
}

.card-header {
  display: block;
  margin: 0;
  padding: 0;
}

.btn-link {
  margin: 0;
  padding: 0;
}

.image-arrows {
  color: white;
  position: relative;
  margin: 0 10px 15px 10px;
}

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
