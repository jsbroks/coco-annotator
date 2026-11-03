<template>
  <div @mousemove="mouseMove">
    <div style="padding-top: 55px" />
    
    <div
      class="bg-light"
      :style="{ 'margin-left': (narrow ? 0 : sidebar.width) + 'px' }"
    >
      <nav class="nav border-bottom shadow-sm" :class="{ 'nav-scroll': narrow }" style="background-color: #4b5162">
        <a v-if="narrow" class="btn tab text-white" @click="sidebarOpen = !sidebarOpen">
          <i class="fa fa-sliders" aria-hidden="true"></i> {{ $t('dataset.tools') }}
        </a>
        <a class="btn tab" @click="tab = 'images'" :style="{'color': tab == 'images' ? 'white' : 'darkgray'}">
          <i class="fa fa-picture-o" aria-hidden="true"></i> {{ $t('dataset.images') }}
        </a>
        <a class="btn tab" @click="tab = 'progress'" :style="{'color': tab == 'progress' ? 'white' : 'darkgray'}">
          <i class="fa fa-tasks" aria-hidden="true"></i> {{ $t('review.tab') }}
        </a>
        <a class="btn tab" @click="tab = 'exports'" :style="{'color': tab == 'exports' ? 'white' : 'darkgray'}">
          <i class="fa fa-share" aria-hidden="true"></i> {{ $t('dataset.exports') }}
        </a>
        <a class="btn tab" @click="tab = 'members'" :style="{'color': tab == 'members' ? 'white' : 'darkgray'}">
          <i class="fa fa-users" aria-hidden="true"></i> {{ $t('dataset.members') }}
        </a>
        <a class="btn tab" @click="tab = 'health'" :style="{'color': tab == 'health' ? 'white' : 'darkgray'}">
          <i class="fa fa-bar-chart" aria-hidden="true"></i> {{ $t('dataset.statistics') }}
        </a>
        <a class="btn tab" @click="tab = 'settings'" :style="{'color': tab == 'settings' ? 'white' : 'darkgray'}">
          <i class="fa fa-cog" aria-hidden="true"></i> {{ $t('dataset.settings') }}
        </a>
      </nav>
    
      <div class="bg-light text-start" style="overflow: auto; height: calc(var(--vh) - 104px); margin: 10px">
        <div class="page-container" v-show="tab == 'images'">
          
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
            {{ $t('dataset.noImagesFoundInDirectory') }}
          </p>
          <div v-else>
            <Pagination :pages="pages" :current="page" @pagechange="updatePage" />
            <div class="row">
              <ImageCard v-for="image in images" :key="image.id" :image="image" :category-map="categoryMap" />
            </div>
            <Pagination :pages="pages" :current="page" @pagechange="updatePage" />
          </div>

        </div>
        <div class="container-fluid exports-tab" v-if="tab == 'health'">
          <DatasetHealth :dataset-id="dataset.id" />
        </div>
        <div class="container-fluid exports-tab" v-if="tab == 'progress'">
          <ReviewPanel :dataset-id="dataset.id" @changed="updatePage()" />
        </div>
        <div class="container-fluid exports-tab" v-show="tab == 'exports'">
          <div class="card my-3 p-3 shadow-sm">
            <div class="d-flex align-items-center border-bottom border-gray pb-2">
              <h6 class="mb-0 me-auto"><b>{{ $t('dataset.exports') }}</b></h6>
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="getExports">
                <i class="fa fa-refresh" /> {{ $t('exportList.refresh') }}
              </button>
            </div>

            <div v-if="!datasetExports.length" class="text-muted small pt-3">
              {{ $t('exportList.empty') }}
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-hover align-middle mb-0 export-table">
                <thead>
                  <tr>
                    <th class="text-nowrap text-center">{{ $t('exportList.id') }}</th>
                    <th class="text-nowrap text-center">{{ $t('exportList.format') }}</th>
                    <th class="text-center">{{ $t('exportList.categories') }}</th>
                    <th class="text-nowrap text-center">{{ $t('exportList.time') }}</th>
                    <th class="text-nowrap text-center">{{ $t('exportList.download') }}</th>
                    <th class="text-nowrap text-center">{{ $t('exportList.delete') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="exp in datasetExports" :key="exp.id">
                    <td class="text-nowrap fw-semibold text-center">#{{ exp.id }}</td>
                    <td class="text-nowrap text-center">
                      <span class="badge" :class="exp.format === 'YOLO' ? 'text-bg-primary' : 'text-bg-dark'">
                        {{ exp.format }}
                      </span>
                      <div v-if="exp.yolo_task" class="small text-muted">{{ $t('yolo.' + exp.yolo_task) }}</div>
                      <div v-if="exp.merged" class="small text-info-emphasis lh-sm" :title="exp.merged.join(' + ')">
                        <i class="fa fa-object-group" /> {{ $t('exportMerge.listed', { n: exp.merged.length }) }}
                      </div>
                      <div v-if="exp.folder" class="small text-muted">
                        <i class="fa fa-folder-o" /> {{ exp.folder }}/
                      </div>
                      <div
                        v-for="part in splitParts(exp)"
                        :key="part"
                        class="small text-muted lh-sm"
                        :title="$t('exportList.seed', { seed: exp.seed })"
                      >{{ part }}</div>
                      <div v-if="exp.augment" class="small text-muted lh-sm" :title="augmentTitle(exp.augment)">
                        <i class="fa fa-magic" /> {{ $t('exportList.augmented', { n: exp.augment.images, copies: exp.augment.copies }) }}
                        <div class="aug-ops">
                          <span v-for="op in augmentOps(exp.augment)" :key="op" class="aug-op">{{ op }}</span>
                        </div>
                        <div class="aug-scope">{{ $t(exp.augment.scope === 'all' ? 'exportList.augScopeAll' : 'exportList.augScopeTrain') }}</div>
                      </div>
                    </td>
                    <td class="text-center">
                      <span
                        v-for="name in shownCategories(exp)"
                        :key="name"
                        class="badge text-bg-light border me-1"
                      >{{ name }}</span>
                      <a
                        v-if="(exp.categories || []).length > EXPORT_TAGS_SHOWN"
                        href="#"
                        class="small"
                        @click.prevent="toggleExportTags(exp.id)"
                      >{{ expandedExports.includes(exp.id)
                        ? $t('exportList.less')
                        : $t('exportList.more', { n: exp.categories.length - EXPORT_TAGS_SHOWN }) }}</a>
                    </td>
                    <td class="text-nowrap text-center">
                      {{ exportTime(exp) }}
                      <div class="small text-muted">{{ $t('dataset.exportedAgo', { time: $ago(exp.ago) }) }}</div>
                    </td>
                    <td class="text-center text-nowrap">
                      <!-- downloading: progress, size, speed, cancel -->
                      <div v-if="downloads[exp.id]" class="dl-progress">
                        <div class="d-flex align-items-center gap-1">
                          <div class="progress flex-grow-1" style="height: 14px">
                            <div
                              class="progress-bar progress-bar-striped progress-bar-animated bg-success"
                              :style="{ width: downloadPct(exp) + '%' }"
                            >{{ downloadPct(exp) }}%</div>
                          </div>
                          <button
                            type="button"
                            class="btn btn-sm btn-link text-danger p-0 ms-1"
                            :title="$t('exportList.cancelDownload')"
                            @click="cancelDownload(exp)"
                          ><i class="fa fa-times" /></button>
                        </div>
                        <div class="small text-muted">{{ downloadText(exp) }}</div>
                      </div>
                      <template v-else>
                        <button
                          class="btn btn-sm btn-success"
                          :disabled="exp.exists === false"
                          :title="exp.exists === false ? $t('exportList.missing') : ''"
                          @click="downloadExport(exp)"
                        >
                          <i class="fa fa-download" />
                          {{ $t('exportList.download') }}
                        </button>
                        <div class="small text-muted">
                          {{ exp.exists === false ? $t('exportList.missing') : fileSize(exp.size) }}
                        </div>
                        <RouterLink
                          v-if="exp.format === 'YOLO' && exp.exists !== false && $store.getters['user/can']('train')"
                          class="small"
                          :to="{ path: '/train', query: { export: exp.id } }"
                        ><i class="fa fa-graduation-cap" /> {{ $t('train.trainThis') }}</RouterLink>
                      </template>
                    </td>
                    <td class="text-center">
                      <button
                        class="btn btn-sm btn-outline-danger"
                        :title="$t('exportList.delete')"
                        @click="deleteExport(exp)"
                      >
                        <i class="fa fa-trash" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="page-container" v-if="tab == 'members'">
          <DatasetMembers :dataset-id="dataset.id" @changed="getUsers()" />
        </div>

        <div class="page-container" v-show="tab == 'settings'">
          <div class="card my-3 p-3 shadow-sm me-2">
            <h6 class="border-bottom border-gray pb-2"><b>{{ $t('datasetTask.label') }}</b></h6>
            <TaskPicker v-model="taskDraft" name="settingsTask" />
            <div class="d-flex align-items-center gap-2 mt-2">
              <button
                type="button"
                class="btn btn-sm btn-primary"
                :disabled="taskDraft === (dataset.task || '')"
                @click="saveTask"
              >
                {{ $t('datasetTask.save') }}
              </button>
              <span class="small text-muted">{{ $t('datasetTask.settingsHint') }}</span>
            </div>
          </div>
          <div class="card my-3 p-3 shadow-sm me-2">
            <h6 class="border-bottom border-gray pb-2"><b>{{ $t('dataset.metadata') }}</b></h6>
            
            <button 
              class="btn btn-sm w-100 btn-danger"
              @click="resetMetadata"
            >
              {{ $t('dataset.restAllMetadata') }}
            </button>
          </div>
        </div>

      </div>
    </div>

    <div v-if="narrow && sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false" />
    <div
      id="filter"
      ref="sidebar"
      class="sidebar"
      :class="{ 'sidebar-mobile': narrow, open: sidebarOpen }"
      :style="{ width: narrow ? 'min(85vw, 320px)' : sidebar.width + 'px' }"
    >
      <div style="padding-top: 10px" />
      <h3>{{ dataset.name }}</h3>
      <p class="text-center" style="color: lightgray">
        <i18n-t keypath="dataset.totalImages" tag="span">
          <template #images><strong style="color: white">{{ imageCount }}</strong></template>
          <template #pages><strong style="color: white">{{ pages }}</strong></template>
        </i18n-t>
      </p>
      <div class="row justify-content-md-center sidebar-section-buttons">
        <button
          type="button"
          class="btn btn-secondary w-100"
          @click="createScanTask"
        >
          <div v-if="scan.id != null" class="progress">
            <div
              class="progress-bar bg-secondary"
              :style="{ 'width': `${scan.progress}%` }"
            >
              {{ $t('dataset.scanning') }}
            </div>
          </div>
          <div v-else>{{ $t('dataset.scan') }}</div>
        </button>

        <button
          type="button"
          class="btn btn-primary w-100"
          @click="importModal"
        >
          <div v-if="importing.id != null" class="progress">
            <div
              class="progress-bar bg-primary"
              :style="{ 'width': `${importing.progress}%` }"
            >
              {{ $t('dataset.importing') }}
            </div>
          </div>
          <div v-else>{{ $t('dataset.importCoco') }}</div>
        </button>

        <button
          type="button"
          class="btn btn-dark w-100"
          @click="exportModal"
        >
          <div v-if="exporting.id != null" class="progress">
            <div
              class="progress-bar bg-dark"
              :style="{ 'width': `${exporting.progress}%` }"
            >
              {{ $t('dataset.exporting') }}
            </div>
          </div>
          <div v-else>{{ $t('dataset.exportCoco') }}</div>
        </button>

        <button
          type="button"
          class="btn btn-info w-100"
          @click="modelModal"
        >
          <div v-if="preannotating.id != null" class="progress">
            <div
              class="progress-bar bg-info"
              :style="{ 'width': `${preannotating.progress}%` }"
            >
              {{ $t('modelRun.running') }}
            </div>
          </div>
          <div v-else><i class="fa fa-rocket" /> {{ $t('modelRun.datasetButton') }}</div>
        </button>

        <button type="button" class="btn btn-outline-light w-100" @click="$refs.aiCleanup.open()">
          <i class="fa fa-eraser" /> {{ $t('aiCleanup.button') }}
        </button>
      </div>
      <hr>
      <h6 class="sidebar-title text-center">{{ $t('dataset.subdirectories') }}</h6>
      <div class="sidebar-section" style="max-height: 30%; color: lightgray">
        <div v-if="subdirectories.length > 0">
          <button
            v-for="(subdirectory, subId) in subdirectories"
            :key="subId"
            class="btn badge rounded-pill text-bg-primary category-badge"
            style="margin: 2px"
            @click="folders.push(subdirectory)"
          >
            {{ subdirectory }}
          </button>
        </div>
        <p v-else style="margin: 0; font-size: 13px; color: gray">
          {{ $t('dataset.noSubdirectoryFound') }}
        </p>
      </div>
      <hr>
      <h6 class="sidebar-title text-center">{{ $t('dataset.filteringOptions') }}</h6>
      <div
        class="sidebar-section"
        style="max-height: 30%; color: lightgray"
      >
        <PanelString :name="$t('dataset.contains')" v-model:value="query.file_name__icontains" @submit="updatePage" />
        <PanelToggle :name="$t('dataset.showAnnotated')" v-model:value="panel.showAnnotated" />
        <PanelToggle :name="$t('dataset.showNotAnnotated')" v-model:value="panel.showNotAnnotated" />
        <PanelDropdown :name="$t('dataset.order')" v-model:value="order" :values="orderTypes" />
        <PanelDropdown :name="$t('review.filterStatus')" v-model:value="reviewFilter.status" :values="statusOptions" />
        <PanelDropdown :name="$t('review.filterAssignee')" v-model:value="reviewFilter.assignee" :values="assigneeOptions" />
        <PanelDropdown :name="$t('imageClass.filter')" v-model:value="reviewFilter.image_class" :values="imageClassOptions" />
      </div>
        <div
          class="sidebar-section"
          style="max-height: 30%; color: lightgray"
        >
          <div class="mb-3">
            <label>{{ $t('dataset.showAnnotatedCategories') }} </label>
            <TagsInput
              v-model:value="selected.categories"
              element-id="selectedCategories"
              :title="$t('dataset.onlyShowsImagesAnnotatedWith')"
              :existing-tags="categoryTags"
              :typeahead="true"
              :typeahead-activation-threshold="0"
            ></TagsInput>
          </div>
      </div>
    </div>


    <div class="modal fade" tabindex="-1" role="dialog" id="cocoUpload">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('dataset.uploadCocoAnnotaitons') }}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form>
              <div class="mb-3">
                <label for="coco" class="form-label">{{ $t('dataset.cocoAnnotationFileJson') }}</label>
                <input
                  type="file"
                  class="form-control"
                  id="coco"
                  accept=".json,application/json,.zip,application/zip"
                  @change="importFile = $event.target.files[0] || null"
                />
                <div class="form-text">{{ importIsYolo ? $t('yolo.importHint') : $t('dataset.importHint') }}</div>
              </div>
              <div v-if="importIsYolo" class="mb-3">
                <label for="importYoloTask" class="form-label">{{ $t('yolo.task') }}</label>
                <select id="importYoloTask" v-model="importYoloTask" class="form-select">
                  <option value="auto">{{ $t('yolo.auto') }}</option>
                  <option v-for="t in yoloTasks" :key="t" :value="t">{{ $t('yolo.' + t) }}</option>
                </select>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              @click="importCOCO"
              :disabled="!importFile"
              data-bs-dismiss="modal"
            >
              {{ $t('dataset.upload') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('dataset.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <ExportWizard ref="exportWizard" @started="onExportStarted" />

    <ModelRunModal
      ref="modelRun"
      modal-id="modelRunDataset"
      :dataset="true"
      :dataset-name="dataset.name"
      :categories="categories"
      @run="runModel"
    />
    <AiCleanupModal
      v-if="dataset.id"
      ref="aiCleanup"
      modal-id="aiCleanupDataset"
      :dataset-id="dataset.id"
      :dataset-name="dataset.name"
      @deleted="updatePage()"
    />
    <ChatWidget v-if="dataset.id" :dataset-id="dataset.id" :dataset-name="dataset.name" />
  </div>
</template>

<script>
import { hideModal, showModal } from "@/libs/modal";
import toastrs from "@/mixins/toastrs";
import Dataset, { isYoloFile } from "@/models/datasets";
import Export from "@/models/exports";
import ImageCard from "@/components/cards/ImageCard.vue";
import Pagination from "@/components/Pagination.vue";
import PanelString from "@/components/PanelInputString.vue";
import PanelToggle from "@/components/PanelToggle.vue";
import PanelDropdown from "@/components/PanelInputDropdown.vue"
import TagsInput from "@/components/TagsInput.vue";
import ModelRunModal from "@/components/ModelRunModal.vue";
import AiCleanupModal from "@/components/AiCleanupModal.vue";
import ExportWizard from "@/components/ExportWizard.vue";
import ReviewPanel from "@/components/ReviewPanel.vue";
import TaskPicker from "@/components/TaskPicker.vue";
import ChatWidget from "@/components/ChatWidget.vue";
import DatasetMembers from "@/components/DatasetMembers.vue";
import DatasetHealth from "@/components/DatasetHealth.vue";
import { OPS as AUGMENT_OPS } from "@/components/ExportAugment.vue";
import axios from "axios";

import { mapMutations } from "vuex";


const TABS = ["images", "progress", "exports", "members", "health", "settings"];

// bigger exports are downloaded by the browser itself (bytes)
const DIRECT_DOWNLOAD_BYTES = 1.5 * 1024 * 1024 * 1024;

function rememberedTab(datasetId) {
  try {
    let tab = sessionStorage.getItem(`dataset/${datasetId}/tab`);
    // the former statistics tab is part of "health" (now called statistics)
    if (tab === "statistics") tab = "health";
    return TABS.includes(tab) ? tab : "images";
  } catch {
    return "images";
  }
}

function rememberTab(datasetId, tab) {
  try {
    sessionStorage.setItem(`dataset/${datasetId}/tab`, tab);
  } catch {
    // not remembered
  }
}

export default {
  name: "Dataset",
  components: {
    ChatWidget,
    ImageCard,
    DatasetMembers,
    ReviewPanel,
    TaskPicker,
    DatasetHealth,
    ExportWizard,
    Pagination,
    PanelString,
    PanelToggle,
    PanelDropdown,
    TagsInput,
    ModelRunModal,
    AiCleanupModal
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
      page: 1,
      pages: 1,
      limit: 48,
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
      mouseDown: false,
      // a phone: the sidebar slides in over the page
      narrow: window.innerWidth < 768,
      sidebarOpen: false,
      sidebar: {
        drag: false,
        width: window.innerWidth * 0.2,
        canResize: false
      },
      scan: {
        progress: 0,
        id: null
      },
      importing: {
        progress: 0,
        warnings: 0,
        errors: 0,
        id: null
      },
      importPoll: null,
      preannotating: {
        progress: 0,
        id: null
      },
      // the export task running from this page (progress on the button)
      exporting: {
        progress: 0,
        id: null
      },
      yoloTasks: ["detect", "segment", "obb", "pose"],
      importFile: null,
      importYoloTask: "auto",
      selected: {
        categories: []
      },
      datasetExports: [],
      expandedExports: [],
      // export id -> { loaded, total, started, controller } while downloading
      downloads: {},
      EXPORT_TAGS_SHOWN: 6,
      tab: "images",
      order: "file_name",
      orderTypes: {
        file_name: "File Name",
        id: "Id",
        path: "File Path"
      },
      query: {
        file_name__icontains: "",
        // query string filters (but not the import task id, see created)
        ...Object.fromEntries(Object.entries(this.$route.query).filter(([k]) => k !== "importTask"))
      },
      reviewFilter: { status: "", assignee: "", image_class: "" },
      taskDraft: "",
      memberNames: [],
      panel: {
        showAnnotated: true,
        showNotAnnotated: true
      }
    };
  },
  methods: {
    /** hear who starts / stops annotating this dataset's images */
    watchDataset() {
      if (this.dataset.id) this.$socket.emit("watch_dataset", { dataset_id: this.dataset.id });
    },
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage(page) {
      // both pagers (above and below the images) show this page
      this.page = page || 1;
      let process = "Loading images from dataset";
      this.addProcess(process);

      Dataset.getData(this.dataset.id, {
        page: page,
        limit: this.limit,
        folder: this.folders.join("/"),
        ...this.query,
        annotated: this.queryAnnotated,
        status: this.reviewFilter.status,
        assignee: this.reviewFilter.assignee,
        image_class: this.reviewFilter.image_class,
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
          this.taskDraft = data.dataset.task || "";
          if (!this.memberNames.length) this.getUsers();
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
    saveTask() {
      axios
        .post(`/api/dataset/${this.dataset.id}`, { task: this.taskDraft })
        .then(() => {
          this.dataset.task = this.taskDraft;
          this.exportDefaultsApplied = false;
          this.$toastr.success(this.$t("datasetTask.saved"));
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(data.message || String(error));
        });
    },
    getUsers() {
      Dataset.getUsers(this.dataset.id).then(response => {
        this.users = response.data;
        this.memberNames = (response.data || []).map(u => u.username).sort();
      });
    },
    downloadExport(exp) {
      if (this.downloads[exp.id]) return;
      // very large files: the browser downloads them itself (its own
      // progress, straight to disk instead of through the page's memory)
      if (exp.size && exp.size > DIRECT_DOWNLOAD_BYTES) {
        const link = document.createElement("a");
        link.href = Export.downloadUrl(exp.id);
        document.body.appendChild(link);
        link.click();
        link.remove();
        this.$toastr.info(this.$t("exportList.browserDownload"));
        return;
      }
      const controller = new AbortController();
      const state = { loaded: 0, total: exp.size || 0, started: Date.now(), controller };
      this.downloads = { ...this.downloads, [exp.id]: state };
      Export.download(exp.id, this.dataset.name, {
        signal: controller.signal,
        onProgress: ({ loaded, total }) => {
          const d = this.downloads[exp.id];
          if (!d) return;
          d.loaded = loaded;
          if (total) d.total = total;
        }
      })
        .catch(error => {
          if (axios.isCancel(error) || (error && error.name === "CanceledError")) return;
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(data.message || this.$t("exportList.downloadFailed"));
        })
        .finally(() => {
          const rest = { ...this.downloads };
          delete rest[exp.id];
          this.downloads = rest;
        });
    },
    cancelDownload(exp) {
      const d = this.downloads[exp.id];
      if (d) d.controller.abort();
    },
    downloadPct(exp) {
      const d = this.downloads[exp.id];
      return d && d.total ? Math.min(100, Math.floor((100 * d.loaded) / d.total)) : 0;
    },
    /** "120 / 260 MB · 8.5 MB/s" */
    downloadText(exp) {
      const d = this.downloads[exp.id];
      if (!d) return "";
      const secs = Math.max(0.5, (Date.now() - d.started) / 1000);
      const speed = this.fileSize(d.loaded / secs) + "/s";
      return d.total ? `${this.fileSize(d.loaded)} / ${this.fileSize(d.total)} · ${speed}` : `${this.fileSize(d.loaded)} · ${speed}`;
    },
    deleteExport(exp) {
      if (!confirm(this.$t("exportList.confirmDelete", { id: exp.id }))) return;
      axios
        .delete(`/api/export/${exp.id}`)
        .then(() => {
          this.datasetExports = this.datasetExports.filter(e => e.id !== exp.id);
          this.$toastr.success(this.$t("exportList.deleted", { id: exp.id }));
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(data.message || String(error));
        });
    },
    splitParts(exp) {
      if (!exp.split) return [];
      return ["train", "val", "test"].filter(k => exp.split[k] > 0).map(k => {
        const n = exp.split_counts ? exp.split_counts[k] : null;
        // originals, plus the augmented images of that part
        const extra = exp.augment && exp.augment.parts ? exp.augment.parts[k] || 0 : 0;
        if (extra) {
          return this.$t("exportList.splitPartAug", { name: this.$t("exportSplit." + k), pct: exp.split[k], n, extra });
        }
        return this.$t("exportList.splitPart", { name: this.$t("exportSplit." + k), pct: exp.split[k], n });
      });
    },
    shownCategories(exp) {
      const names = exp.categories || [];
      return this.expandedExports.includes(exp.id) ? names : names.slice(0, this.EXPORT_TAGS_SHOWN);
    },
    toggleExportTags(id) {
      this.expandedExports = this.expandedExports.includes(id)
        ? this.expandedExports.filter(x => x !== id)
        : [...this.expandedExports, id];
    },
    /** Local date and time of an export (stored in UTC) */
    exportTime(exp) {
      const date = exp.created_at ? new Date(exp.created_at) : null;
      if (!date || isNaN(date)) return "";
      const pad = n => String(n).padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
        `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    },
    fileSize(bytes) {
      if (bytes == null) return "";
      if (bytes < 1024) return `${Math.round(bytes)} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      if (bytes < 1024 ** 3) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
      return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
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
    createScanTask() {
      if (this.scan.id != null) {
        this.openTask(this.scan.id);
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
        });
    },
    exportModal() {
      if (this.exporting.id != null) {
        this.openTask(this.exporting.id);
        return;
      }
      this.$refs.exportWizard.open([this.dataset.id]);
    },
    onExportStarted({ datasetId, taskId }) {
      // the export is kept with the main dataset (the first one ticked)
      if (datasetId === this.dataset.id) {
        this.exporting.id = taskId;
      } else {
        this.$toastr.info(this.$t("exportPick.startedElsewhere"));
      }
    },
    augmentTitle(aug) {
      return this.augmentOps(aug).join("、");
    },
    /** the augmentations of an export, with their amounts (±15°) */
    augmentOps(aug) {
      const ops = (aug && aug.ops) || {};
      return AUGMENT_OPS.filter(o => ops[o.key]).map(o => {
        let label = this.$t("exportAugment.op." + o.key);
        if (o.key === "rotate" && typeof ops.rotate === "number") label += ` ±${ops.rotate}°`;
        if (o.key === "scale" && typeof ops.scale === "number") label += ` ≥${Math.round(ops.scale * 100)}%`;
        return label;
      });
    },
    /** A running task: open it on the Tasks page, or just say it is still running */
    openTask(id) {
      if (this.$store.getters["user/canPage"]("tasks")) {
        this.$router.push({ path: "/tasks", query: { id } });
      } else {
        this.$toastr.info(this.$t("dataset.taskStillRunning"));
      }
    },
    modelModal() {
      if (this.preannotating.id != null) {
        this.openTask(this.preannotating.id);
        return;
      }
      this.$refs.modelRun.open();
    },
    runModel(options) {
      axios
        .post(`/api/model/yolo/dataset/${this.dataset.id}`, options)
        .then(response => {
          hideModal("#modelRunDataset");
          this.preannotating.id = response.data.id;
          this.$toastr.info(this.$t("modelRun.datasetStarted"));
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.axiosReqestError(this.$t("modelRun.datasetButton"), data.message);
        });
    },
    removeFolder(folder) {
      let index = this.folders.indexOf(folder);
      this.folders.splice(index + 1, this.folders.length);
    },
    importModal() {
      if (this.importing.id != null) {
        this.openTask(this.importing.id);
        return;
      }

      this.importFile = null;
      const input = document.getElementById("coco");
      if (input) input.value = "";
      showModal("#cocoUpload");
    },
    /** Fallback for a progress update sent before this page was listening */
    /** "last seen" text; accounts that never logged in have no date */
    pollImportTask() {
      clearTimeout(this.importPoll);
      const id = this.importing.id;
      if (id == null || this.importing.progress >= 100) return;
      axios.get("/api/tasks/").then(response => {
        const task = (response.data || []).find(t => t.id === id);
        if (this.importing.id !== id) return;
        if (task && task.completed) {
          this.importing.warnings = task.warnings || 0;
          this.importing.errors = task.errors || 0;
          this.importing.progress = 100;
        } else {
          this.importPoll = setTimeout(this.pollImportTask, 2000);
        }
      });
    },
    importCOCO() {
      if (!this.importFile) return;
      Dataset.uploadAnnotations(this.dataset.id, this.importFile, this.importYoloTask)
        .then(response => {
          if (response.data.stats) this.showYoloStats(response.data);
          this.importing.id = response.data.id;
          this.pollImportTask();
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.axiosReqestError(this.$t("dataset.importCoco"), data.message || String(error));
        });
    },
    /** What the server matched in a YOLO zip (the import itself runs as a task) */
    showYoloStats(data) {
      const s = data.stats;
      this.$toastr.info(this.$t("yolo.importStarted", {
        task: this.$t("yolo." + s.task), matched: s.matched, annotations: s.annotations
      }));
      if (s.unmatched) {
        this.$toastr.warning(this.$t("yolo.unmatched", { n: s.unmatched, names: s.unmatched_examples.join(", ") }));
      }
      if (!data.names_found) this.$toastr.warning(this.$t("yolo.noNames"));
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
    statusOptions() {
      const options = { "": this.$t("review.all"), annotated: this.$t("review.filterAnnotated"), ai: this.$t("review.filterAi") };
      ["unlabeled", "labeled", "approved", "rejected"].forEach(s => (options[s] = this.$t("review.status." + s)));
      return options;
    },
    imageClassOptions() {
      const options = { "": this.$t("review.all"), none: this.$t("imageClass.none") };
      this.categories.forEach(c => (options[String(c.id)] = c.name));
      return options;
    },
    categoryMap() {
      return Object.fromEntries(this.categories.map(c => [c.id, { name: c.name, color: c.color }]));
    },
    assigneeOptions() {
      const options = { "": this.$t("review.all"), me: this.$t("review.assignedToMe"), none: this.$t("review.unassigned") };
      this.memberNames.forEach(name => (options[name] = name));
      return options;
    },
    importIsYolo() {
      return isYoloFile(this.importFile);
    },
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
    connect() {
      // a new connection starts without rooms
      this.watchDataset();
    },
    taskProgress(data) {
      if (data.id === this.scan.id) {
        this.scan.progress = data.progress;
      }

      if (data.id === this.importing.id) {
        // socket updates can arrive after the poll already saw the task finish
        this.importing.progress = Math.max(this.importing.progress, data.progress);
        this.importing.warnings = data.warnings || 0;
        this.importing.errors = data.errors || 0;
      }

      if (data.id === this.exporting.id) {
        if (data.failed) {
          // tell why, and do not refresh the list as if it had worked
          this.$toastr.error(data.message || "", this.$t("dataset.exportFailed"), { timeOut: 0, closeButton: true });
          this.exporting.progress = 0;
          this.exporting.id = null;
          return;
        }
        this.exporting.progress = data.progress;
      }

      if (data.id === this.preannotating.id) {
        this.preannotating.progress = data.progress;
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
      rememberTab(this.dataset.id, tab);
      if (tab == "members") this.getUsers();
      if (tab == "exports") this.getExports();
    },
    reviewFilter: {
      deep: true,
      handler() {
        this.updatePage();
      }
    },
    order(order) {
      localStorage.setItem("dataset/order", order);
      this.updatePage();
    },
    queryAnnotated() {
      this.updatePage();
    },
    "selected.categories": {
      deep: true,
      handler(val) {
        this.updatePage();
      }
    },
    folders: {
      deep: true,
      handler() {
        this.updatePage();
      }
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
    "importing.progress"(progress, previous) {
      // progress can step from e.g. 100.0000001 to 100: report once
      if (progress >= 100 && !(previous >= 100)) {
        const problems = (this.importing.warnings || 0) + (this.importing.errors || 0);
        if (problems) {
          this.$toastr.warning(this.$t("dataset.importDoneWithProblems", { n: problems }));
        } else {
          this.$toastr.success(this.$t("dataset.importDone"));
        }
        this.updatePage();
        setTimeout(() => {
          this.importing.progress = 0;
          this.importing.id = null;
        }, 1000);
      }
    },
    "preannotating.progress"(progress) {
      if (progress >= 100) {
        setTimeout(() => {
          this.preannotating.progress = 0;
          this.preannotating.id = null;
          this.updatePage();
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
  beforeRouteUpdate(to) {
    this.dataset.id = parseInt(to.params.identifier);
    this.watchDataset();
    this.tab = rememberedTab(this.dataset.id);
    this.updatePage();
  },
  created() {
    let order = localStorage.getItem("dataset/order");
    let sideWidth = localStorage.getItem("dataset/sideWidth");
    
    if (sideWidth !== null) this.sidebar.width = parseInt(sideWidth);
    if (order !== null) this.order = order;

    this.dataset.id = parseInt(this.identifier);
    // each dataset opens on Images, except when coming back to it in this
    // browser tab (e.g. from the annotator): then on the tab it was left on
    this.tab = rememberedTab(this.dataset.id);
    // coming from the import dialog on the datasets page: follow its task
    if (this.$route.query.importTask) {
      this.importing.id = parseInt(this.$route.query.importTask);
      this.pollImportTask();
    }
    this.updatePage();
  },
  mounted() {
    this.onResize = () => {
      this.narrow = window.innerWidth < 768;
      if (!this.narrow) this.sidebarOpen = false;
    };
    window.addEventListener("resize", this.onResize);
    window.addEventListener("mouseup", this.stopDrag);
    window.addEventListener("mousedown", this.startDrag);
    this.watchDataset();
  },
  unmounted() {
    // stop hearing who annotates this dataset's images
    this.$socket.emit("watch_dataset", { dataset_id: null });
    clearTimeout(this.importPoll);
    window.removeEventListener("mouseup", this.stopDrag);
    window.removeEventListener("mousedown", this.startDrag);
    window.removeEventListener("resize", this.onResize);
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
  height: var(--vh);
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

.sidebar-mobile {
  z-index: 1020;
  overflow-y: auto;
  padding-bottom: 24px;
  transform: translateX(-100%);
  transition: transform 0.2s ease;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.3);
}
.sidebar-mobile.open {
  transform: none;
}
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1019;
  background: rgba(0, 0, 0, 0.35);
}
.nav-scroll {
  flex-wrap: nowrap;
  overflow-x: auto;
  white-space: nowrap;
  scrollbar-width: none;
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

.exports-tab {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px;
}
.dl-progress {
  min-width: 170px;
}
.export-table td,
.export-table th {
  padding: 0.6rem 0.75rem;
}

.aug-ops {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2px;
  max-width: 220px;
  margin: 2px auto 0;
  white-space: normal;
}
.aug-op {
  background: #e7f1ff;
  color: #084298;
  border-radius: 999px;
  padding: 0 6px;
  font-size: 0.7rem;
  white-space: nowrap;
}
.aug-scope {
  font-size: 0.7rem;
  white-space: normal;
}
</style>
