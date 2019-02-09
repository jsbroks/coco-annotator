<template>
  <div @mousemove="mouseMove">
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light"
      style="overflow: auto; height: calc(100vh - 55px)"
      :style="{ 'margin-left': sidebar.width + 'px' }"
    >
      <div class="container">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"></li>
          <li class="breadcrumb-item active">
            <button class="btn btn-sm btn-link" @click="folders = []">
              {{ dataset.name }}
            </button>
          </li>
          <li
            v-for="(folder, folderId) in folders"
            :key="folderId"
            class="breadcrumb-item"
          >
            <button
              class="btn btn-sm btn-link"
              :disabled="folders[folders.length - 1] === folder"
              @click="removeFolder(folder)"
            >
              {{ folder }}
            </button>
          </li>
        </ol>

        <p class="text-center" v-if="images.length < 1">
          No images found in directory.
        </p>
        <div v-else>
          <Pagination :pages="pages" @pagechange="updatePage" />
          <div class="row">
            <ImageCard v-for="image in images" :key="image.id" :image="image" />
          </div>
          <hr />
        </div>
      </div>
    </div>

    <div
      id="filter"
      ref="sidebar"
      class="sidebar"
      :style="{ width: sidebar.width + 'px' }"
    >
      <div style="padding-top: 10px" />
      <h3>{{ dataset.name }}</h3>
      <p class="text-center" style="color: lightgray">
        Total of <strong style="color: white">{{ imageCount }}</strong> images
        displayed on <strong style="color: white">{{ pages }}</strong> pages.
      </p>
      <div class="row justify-content-md-center sidebar-section-buttons">
        <button
          type="button"
          class="btn btn-success btn-block"
          data-toggle="modal"
          data-target="#generateDataset"
        >
          <div v-if="generate.id != null" class="progress">
            <div
              class="progress-bar bg-success"
              :style="{ 'width': `${generate.progress}%` }"
            >
              Generating
            </div>
          </div>
          <div v-else>Generate</div>
        </button>
        <button
          type="button"
          class="btn btn-primary btn-block"
          data-toggle="modal"
          data-target="#cocoUpload"
        >
          <div v-if="importing.id != null" class="progress">
            <div
              class="progress-bar bg-primary"
              :style="{ 'width': `${importing.progress}%` }"
            >
              Importing
            </div>
          </div>
          <div v-else>Importing COCO</div>
        </button>
        <button
          type="button"
          class="btn btn-secondary btn-block"
          @click="createScanTask"
        >
          <div v-if="scan.id != null" class="progress">
            <div
              class="progress-bar bg-secondary"
              :style="{ 'width': `${scan.progress}%` }"
            >
              Scanning
            </div>
          </div>
          <div v-else>Scan</div>
        </button>

        <!-- <button type="button" class="btn btn-info">
          Download COCO
        </button> -->
      </div>
      <hr>
      <h6 class="sidebar-title text-center">Subdirectories</h6>
      <div class="sidebar-section" style="max-height: 30%; color: lightgray">
        <div v-if="subdirectories.length > 0">
          <button
            v-for="(subdirectory, subId) in subdirectories"
            :key="subId"
            class="btn badge badge-pill badge-primary category-badge"
            style="margin: 2px"
            @click="folders.push(subdirectory)"
          >
            {{ subdirectory }}
          </button>
        </div>
        <p v-else style="margin: 0; font-size: 13px; color: gray">
          No subdirectory found.
        </p>
      </div>
      <hr>
      <h6 class="sidebar-title text-center">Filtering Options</h6>
      <div
        class="sidebar-section"
        style="max-height: 30%; color: lightgray"
      >
        <PanelString name="Contains" v-model="query.file_name__icontains" @submit="updatePage" />
        <PanelToggle name="Show Annotated" v-model="panel.showAnnotated" />
        <PanelToggle name="Show Not Annotated" v-model="panel.showNotAnnotated" />
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="generateDataset">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Generate a Dataset</h5>
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
                <label>Keyword</label>
                <input class="form-control" v-model="keyword" />
              </div>
              <div class="form-group">
                <label>Limit</label>
                <input
                  class="form-control"
                  type="number"
                  v-model="generateLimit"
                />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              @click="generateDataset"
            >
              Generate
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
    <div class="modal fade" tabindex="-1" role="dialog" id="cocoUpload">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Upload COCO Annotaitons</h5>
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
                <label for="coco">COCO Annotation file (.json)</label>
                <input type="file" class="form-control-file" id="coco" />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              @click="importCOCO"
              data-dismiss="modal"
            >
              Upload
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
import toastrs from "@/mixins/toastrs";
import Dataset from "@/models/datasets";
import ImageCard from "@/components/cards/ImageCard";
import Pagination from "@/components/Pagination";
import PanelString from "@/components/PanelInputString";
import PanelToggle from "@/components/PanelToggle";

import { mapMutations } from "vuex";

export default {
  name: "Dataset",
  components: {
    ImageCard,
    Pagination,
    PanelString,
    PanelToggle
  },
  mixins: [toastrs],
  props: {
    identifier: {
      type: [Number, String],
      required: true
    }
  },
  data() {
    return {
      pages: 1,
      generateLimit: 100,
      limit: 52,
      imageCount: 0,
      images: [],
      folders: [],
      dataset: {
        id: 0
      },
      subdirectories: [],
      status: {
        data: { state: true, message: "Loading data" }
      },
      keyword: "",
      mouseDown: false,
      sidebar: {
        drag: false,
        width: 300,
        canResize: false
      },
      scan: {
        progress: 0,
        id: null
      },
      generate: {
        progress: 0,
        id: null
      },
      importing: {
        progress: 0,
        id: null
      },
      exporting: {
        progress: 0,
        id: null
      },
      query: {
        file_name__icontains: "",
        ...this.$route.query
      },
      panel: {
        showAnnotated: true,
        showNotAnnotated: true
      }
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    generateDataset() {
      if (this.keyword.length === 0) return;

      Dataset.generate(this.dataset.id, {
        keywords: [this.keyword],
        limit: this.generateLimit
      });
    },
    updatePage(page) {
      let process = "Loading images from dataset";
      this.addProcess(process);

      Dataset.getData(this.dataset.id, {
        page: page,
        limit: this.limit,
        folder: this.folders.join("/"),
        ...this.query,
        annotated: this.queryAnnotated
      })
        .then(response => {
          let data = response.data;

          this.images = data.images;
          this.dataset = data.dataset;

          this.imageCount = data.pagination.total;
          this.pages = data.pagination.pages;

          this.subdirectories = data.subdirectories;
          // this.scan.id = data.scanId;
          // this.generate.id = data.generateId;
          // this.importing.id = data.importId;
          // this.exporting.id = data.exportId;
        })
        .catch(error => {
          this.axiosReqestError("Loading Dataset", error.response.data.message);
        })
        .finally(() => this.removeProcess(process));
    },
    createScanTask() {
      Dataset.scan(this.dataset.id)
        .then(response => {
          this.axiosReqestSuccess(
            "Scanning Dataset",
            `Task has been created with id ${response.data.id}`
          );
        })
        .catch(error => {
          this.axiosReqestError(
            "Scanning Dataset",
            error.response.data.message
          );
        })
        .finally(() => this.removeProcess(process));
    },
    removeFolder(folder) {
      let index = this.folders.indexOf(folder);
      this.folders.splice(index + 1, this.folders.length);
    },
    importCOCO() {
      let process = "Uploading COCO annotation file";
      this.addProcess(process);

      let uploaded = document.getElementById("coco");
      Dataset.uploadCoco(this.dataset.id, uploaded.files[0])
        .then(response => {
          this.axiosReqestSuccess(
            "Importing COCO",
            `Task has been created with id ${response.data.id}`
          );
        })
        .catch(error => {
          this.axiosReqestError("Importing COCO", error.response.data.message);
        })
        .finally(() => this.removeProcess(process));
    },
    mouseMove(event) {
      let element = this.$refs.sidebar;

      let sidebarWidth = element.offsetWidth;
      let clickWidth = event.x;
      let pixelsFromSide = Math.abs(sidebarWidth - clickWidth);

      this.sidebar.drag = pixelsFromSide < 4;

      if (this.sidebar.canResize) {
        event.preventDefault();
        let max = window.innerWidth * 0.5;
        this.sidebar.width = Math.min(Math.max(event.x, 200), max);
      }
    },
    startDrag() {
      this.mouseDown = true;
      this.sidebar.canResize = this.sidebar.drag;
    },
    stopDrag() {
      this.mouseDown = false;
      this.sidebar.canResize = false;
    }
  },
  computed: {
    queryAnnotated() {
      let showAnnotated = this.panel.showAnnotated;
      let showNotAnnotated = this.panel.showNotAnnotated;
      
      if (showAnnotated && showNotAnnotated) return null
      if (!showAnnotated && !showNotAnnotated) return " ";

      return showAnnotated;
    }
  },
  sockets: {
    taskProgress(data) {
      if (data.id === this.scan.id) {
        this.scan.progress = data.progress;
      }

      if (data.id === this.generate.id) {
        this.generate.progress = data.progress;
      }

      if (data.id === this.importing.id) {
        this.importing.progress = data.progress;
      }
    },
    annotating(data) {
      let image = this.images.find(i => i.id == data.image_id);
      if (image == null) return;

      if (data.active) {
        let found = image.annotating.indexOf(data.username);
        if (found < 0) {
          image.annotating.push(data.username);
        }
      } else {
        image.annotating.splice(image.annotating.indexOf(data.username), 1);
      }
    }
  },
  watch: {
    queryAnnotated() { this.updatePage() },
    folders() {
      this.updatePage();
    },
    "sidebar.drag"(canDrag) {
      let el = this.$refs.sidebar;
      if (canDrag) {
        this.$el.style.cursor = "ew-resize";
        el.style.borderRight = "4px solid #383c4a";
      } else {
        this.$el.style.cursor = "default";
        el.style.borderRight = "";
      }
    },
    "scan.progress"(progress) {
      if (progress >= 100) {
        setTimeout(() => {
          this.scan.progress = 0;
          this.scan.id = null;
        }, 500);
      }
    }
  },
  beforeRouteUpdate() {
    this.dataset.id = parseInt(this.identifier);
    this.updatePage();
  },
  created() {
    this.sidebar.width = window.innerWidth * 0.2;
    if (this.sidebar.width < 90) this.sidebar.width = 0;

    this.dataset.id = parseInt(this.identifier);
    this.updatePage();
  },
  mounted() {
    window.addEventListener("mouseup", this.stopDrag);
    window.addEventListener("mousedown", this.startDrag);
  },
  destroyed() {
    window.removeEventListener("mouseup", this.stopDrag);
    window.removeEventListener("mousedown", this.startDrag);
  }
};
</script>

<style scoped>
.breadcrumb {
  padding: 0px;
  margin: 5px 0;
}

.btn-link {
  padding: 0px;
}

.sidebar .title {
  color: white;
}

.progress {
  padding: 2px;
  height: 24px;
}

.sidebar {
  height: 100%;
  position: fixed;
  color: white;
  z-index: 1;
  top: 0;
  left: 0;
  background-color: #4b5162;
  overflow-x: hidden;
  padding-top: 60px;
}

.sidebar .closebtn {
  position: absolute;
  top: 0;
  right: 25px;
  font-size: 36px;
  margin-left: 50px;
}

.sidebar-title {
  color: white;
}

.sidebar-section-buttons {
  margin: 5px;
}

.sidebar-section {
  margin: 5px;
  border-radius: 5px;
  background-color: #383c4a;
  padding: 0 5px 2px 5px;
  overflow: auto;
}
</style>
