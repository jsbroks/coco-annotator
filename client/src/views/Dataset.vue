<template>
  <div @mousemove="mouseMove">
    <div style="padding-top: 55px" />
    
    <div
      class="bg-light"
      :style="{ 'margin-left': sidebar.width + 'px' }"
    >
      <nav class="nav border-bottom shadow-sm" style="background-color: #4b5162">
        <a class="btn tab" @click="tab = 'images'" :style="{'color': tab == 'images' ? 'white' : 'darkgray'}">
          <i class="fa fa-picture-o" aria-hidden="true"></i> Images
        </a>
        <a class="btn tab" @click="tab = 'exports'" :style="{'color': tab == 'exports' ? 'white' : 'darkgray'}">
          <i class="fa fa-share" aria-hidden="true"></i> Exports
        </a>
        <a class="btn tab" @click="tab = 'members'" :style="{'color': tab == 'members' ? 'white' : 'darkgray'}">
          <i class="fa fa-users" aria-hidden="true"></i> Members
        </a>
        <a class="btn tab" @click="tab = 'statistics'" :style="{'color': tab == 'statistics' ? 'white' : 'darkgray'}">
          <i class="fa fa-bar-chart" aria-hidden="true"></i> Statistics
        </a>
        <a class="btn tab" @click="tab = 'settings'" :style="{'color': tab == 'settings' ? 'white' : 'darkgray'}">
          <i class="fa fa-cog" aria-hidden="true"></i> Settings
        </a>
      </nav>
    
      <div class="bg-light text-left" style="overflow: auto; height: calc(100vh - 100px); margin: 10px">
        <div class="container" v-show="tab == 'images'">
          
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
            <Pagination :pages="pages" @pagechange="updatePage" />
          </div>

        </div>
        <div class="container" v-show="tab == 'exports'">
          <div class="card my-3 p-3 shadow-sm mr-2">
            <h6 class="border-bottom border-gray pb-2"><b>Exports</b></h6>
            
            <div class="media text-muted pt-3" v-for="exp in datasetExports">
              <div class="media-body lh-125 border-bottom border-gray">
                  {{exp.id}}. Exported {{ exp.ago.length > 0 ? exp.ago : 0 + " seconds" }} ago
                  <div style="display: inline">
                    <span
                      v-for="tag in exp.tags"
                      class="badge badge-secondary"
                      style="margin: 1px"
                    >
                      {{tag}}
                    </span>
                  </div>
                  <button 
                    class="btn btn-sm btn-success"
                    style="float: right; margin: 2px; padding: 2px"
                    @click="downloadExport(exp.id)"
                  >
                    Download
                  </button>
              </div>
            </div>
          </div>
        </div>

        <div class="container" v-show="tab == 'members'">

          <div class="card my-3 p-3 shadow-sm mr-2">
            <h6 class="border-bottom border-gray pb-2"><b>Invite Members</b></h6>
            
          </div>
          
          <div class="card my-3 p-3 shadow-sm mr-2">
            <h6 class="border-bottom border-gray pb-2"><b>Existing Members</b></h6>
            
            <div class="media text-muted pt-3" v-for="user in users">
              <img src="https://d1nhio0ox7pgb.cloudfront.net/_img/o_collection_png/green_dark_grey/256x256/plain/user.png" class="mr-2 rounded" style="width: 32px; height: 32px;">
              <div class="media-body pb-3 mb-0 small lh-125 border-bottom border-gray">
                <div class="d-flex justify-content-between align-items-center w-100">
                  <div class="text-gray-dark">
                    <strong>{{ user.name }}</strong> @{{user.username}}
                  </div>
                  <a href="#">{{ user.group }}</a>
                </div>
                <span class="d-block">Last seen: {{ new Date(user.last_seen['$date']).toISOString().slice(0, 19).replace('T', ' ') }} UTC</span>
              </div>
            </div>
          </div>

        </div>
        <div class="container" v-show="tab == 'statistics'">
          <div v-if="stats == null">
            Crunching numbers...
          </div>

          <div v-else>
            <div class="row">
              
              <div v-if="stats.total" class="card my-3 p-3 shadow-sm col-3 mr-2">
                <h6 class="border-bottom border-gray pb-2"><b>Total</b></h6>
                <div class="row" v-for="stat in Object.keys(stats.total)">
                  <strong class="col-8">{{stat}}:</strong>
                  <span class="col-4">{{stats.total[stat].toFixed(0)}}</span>
                </div>
              </div>

              <div v-if="stats.average" class="card my-3 p-3 shadow-sm col-4 mr-2">
                <h6 class="border-bottom border-gray pb-2"><b>Average</b></h6>
                <div class="row" v-for="stat in Object.keys(stats.average)">
                  <strong class="col-8">{{stat}}:</strong>
                  <span class="col-4">{{stats.average[stat].toFixed(0)}}</span>
                </div>
              </div>

              <div v-if="stats.categories" class="card my-3 p-3 shadow-sm col-4 mr-2">
                <h6 class="border-bottom border-gray pb-2"><b>Annotations Per Category</b></h6>
                <div class="row" v-for="stat in Object.keys(stats.categories)">
                  <strong class="col-8">{{stat}}:</strong>
                  <span class="col-4">{{stats.categories[stat].toFixed(0)}}</span>
                </div>
              </div>

              <div v-if="stats.images_per_category" class="card my-3 p-3 shadow-sm col-4 mr-2">
                <h6 class="border-bottom border-gray pb-2"><b>Annotated Images Per Category</b></h6>
                <div class="row" v-for="stat in Object.keys(stats.images_per_category)">
                  <strong class="col-8">{{stat}}:</strong>
                  <span class="col-4">{{stats.images_per_category[stat].toFixed(0)}}</span>
                </div>
              </div>

            </div>
            
          </div>
        </div>
        <div class="container" v-show="tab == 'settings'">
          <div class="card my-3 p-3 shadow-sm mr-2">
            <h6 class="border-bottom border-gray pb-2"><b>Metadata</b></h6>
            
            <button 
              class="btn btn-sm btn-block btn-danger"
              @click="resetMetadata"
            >
              Rest All Metadata
            </button>
          </div>
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

        <button
          type="button"
          class="btn btn-primary btn-block"
          @click="importModal"
        >
          <div v-if="importing.id != null" class="progress">
            <div
              class="progress-bar bg-primary"
              :style="{ 'width': `${importing.progress}%` }"
            >
              Importing
            </div>
          </div>
          <div v-else>Import COCO</div>
        </button>

        <button
          type="button"
          class="btn btn-dark btn-block"
          @click="exportModal"
        >
          <div v-if="exporting.id != null" class="progress">
            <div
              class="progress-bar bg-dark"
              :style="{ 'width': `${exporting.progress}%` }"
            >
              Exporting
            </div>
          </div>
          <div v-else>Export COCO</div>
        </button>
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
        <PanelDropdown name="Order" v-model="order" :values="orderTypes" />
      </div>
        <div
          class="sidebar-section"
          style="max-height: 30%; color: lightgray"
        >
          <div class="form-group">
            <label>Show Annotated Categories </label>
            <TagsInput
              v-model="selected.categories"
              element-id="selectedCategories"
              title="Only shows images annotated with the selected categories for 'Show Annotated' button. Leave empty to show all annotated images."
              :existing-tags="categoryTags"
              :typeahead="true"
              :typeahead-activation-threshold="0"
            ></TagsInput>
          </div>
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

    <div class="modal fade" tabindex="-1" role="dialog" id="exportDataset">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Export {{dataset.name}}</h5>
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
                <label>Categories (Empty export all)</label>
                <TagsInput
                  v-model="exporting.categories"
                  element-id="exportCategories"
                  :existing-tags="categoryTags"
                  :typeahead="true"
                  :typeahead-activation-threshold="0"
                ></TagsInput>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              @click="exportCOCO"
            >
              Export
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
import Export from "@/models/exports";
import ImageCard from "@/components/cards/ImageCard";
import Pagination from "@/components/Pagination";
import PanelString from "@/components/PanelInputString";
import PanelToggle from "@/components/PanelToggle";
import PanelDropdown from "@/components/PanelInputDropdown"
import JQuery from "jquery";
import TagsInput from "@/components/TagsInput";

import { mapMutations } from "vuex";

let $ = JQuery;

export default {
  name: "Dataset",
  components: {
    ImageCard,
    Pagination,
    PanelString,
    PanelToggle,
    PanelDropdown,
    TagsInput
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
      categories: [],
      images: [],
      folders: [],
      dataset: {
        id: 0
      },
      users: [],
      subdirectories: [],
      status: {
        data: { state: true, message: "Loading data" }
      },
      keyword: "",
      mouseDown: false,
      sidebar: {
        drag: false,
        width: window.innerWidth * 0.2,
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
        categories: [],
        progress: 0,
        id: null
      },
      selected: {
        categories: []
      },
      datasetExports: [],
      tab: "images",
      order: "file_name",
      orderTypes: {
        file_name: "File Name",
        id: "Id",
        path: "File Path"
      },
      query: {
        file_name__icontains: "",
        ...this.$route.query
      },
      panel: {
        showAnnotated: true,
        showNotAnnotated: true
      },
      stats: null
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
        annotated: this.queryAnnotated,
        category_ids__in: encodeURI(this.selected.categories),
        order: this.order
      })
        .then(response => {
          let data = response.data;

          this.images = data.images;
          this.dataset = data.dataset;
          this.categories = data.categories;

          this.imageCount = data.total;
          this.pages = data.pages;

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
    getUsers() {
      Dataset.getUsers(this.dataset.id).then(response => {
        this.users = response.data;
      });
    },
    downloadExport(id) {
      Export.download(id, this.dataset.name);
    },
    getExports() {
      Dataset.getExports(this.dataset.id).then(response => {
        this.datasetExports = response.data;
      });
    },
    resetMetadata() {
      let r = confirm("You can not undo reseting of all metadata in"
        + "this dataset. This includes metadata of images"
        + "and annotations.");
      
      if (r) {
        Dataset.resetMetadata(this.dataset.id);
      }
    },
    getStats() {
      Dataset.getStats(this.dataset.id).then(response => {
        this.stats = response.data;
      });
    },
    createScanTask() {
      if (this.scan.id != null) {
        this.$router.push({ path: "/tasks", query: { id: this.scan.id } });
        return;
      }

      Dataset.scan(this.dataset.id)
        .then(response => {
          let id = response.data.id;
          this.scan.id = id;
        })
        .catch(error => {
          this.axiosReqestError(
            "Scanning Dataset",
            error.response.data.message
          );
        })
        .finally(() => this.removeProcess(process));
    },
    exportModal() {
      if (this.exporting.id != null) {
        this.$router.push({ path: "/tasks", query: { id: this.exporting.id } });
        return;
      }
      $("#exportDataset").modal("show");
    },
    exportCOCO() {
      $("#exportDataset").modal("hide");
      Dataset.exportingCOCO(this.dataset.id, this.exporting.categories)
        .then(response => {
          let id = response.data.id;
          this.exporting.id = id;
        })
        .catch(error => {
          this.axiosReqestError("Exporting COCO", error.response.data.message);
        })
        .finally(() => this.removeProcess(process));
    },
    removeFolder(folder) {
      let index = this.folders.indexOf(folder);
      this.folders.splice(index + 1, this.folders.length);
    },
    importModal() {
      if (this.importing.id != null) {
        this.$router.push({ path: "/tasks", query: { id: this.importing.id } });
        return;
      }

      $("#cocoUpload").modal("show");
    },
    importCOCO() {
      let uploaded = document.getElementById("coco");
      Dataset.uploadCoco(this.dataset.id, uploaded.files[0])
        .then(response => {
          let id = response.data.id;
          this.importing.id = id;
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
        this.sidebar.width = Math.min(Math.max(event.x, 150), max);
        localStorage.setItem("dataset/sideWidth", this.sidebar.width)
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

      if (showAnnotated && showNotAnnotated) return null;
      if (!showAnnotated && !showNotAnnotated) return " ";

      return showAnnotated;
    },
    categoryTags() {
      let tags = {};
      this.categories.forEach(c => tags[c.id] = c.name);
      return tags;
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

      if (data.id === this.exporting.id) {
        this.exporting.progress = data.progress;
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
    tab(tab) {
      localStorage.setItem("dataset/tab", tab);
      if (tab == "members") this.getUsers();
      if (tab == "statistics") this.getStats();
      if (tab == "exports") this.getExports();
    },
    order(order) {
      localStorage.setItem("dataset/order", order);
      this.updatePage();
    },
    queryAnnotated() {
      this.updatePage();
    },
    "selected.categories"(val) {
      this.updatePage();
    },
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
        }, 1000);
      }
    },
    "importing.progress"(progress) {
      if (progress >= 100) {
        setTimeout(() => {
          this.importing.progress = 0;
          this.importing.id = null;
        }, 1000);
      }
    },
    "exporting.progress"(progress) {
      if (progress >= 100) {
        setTimeout(() => {
          this.exporting.progress = 0;
          this.exporting.id = null;

          this.getExports();
        }, 1000);
      }
    }
  },
  beforeRouteUpdate() {
    this.dataset.id = parseInt(this.identifier);
    this.updatePage();
  },
  created() {
    let tab = localStorage.getItem("dataset/tab");
    let order = localStorage.getItem("dataset/order");
    let sideWidth = localStorage.getItem("dataset/sideWidth");
    
    if (sideWidth !== null) this.sidebar.width = parseInt(sideWidth);
    if (tab !== null) this.tab = tab;
    if (order !== null) this.order = order;

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
