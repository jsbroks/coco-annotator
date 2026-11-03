<template>
  <div class="modal fade" tabindex="-1" role="dialog" id="importDataset">
    <div class="modal-dialog" :class="{ 'modal-lg': videoState.count }" role="document">
      <div class="modal-content text-start">
        <div class="modal-header">
          <h5 class="modal-title">{{ $t('importDataset.title') }}</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
            :disabled="running"
          ></button>
        </div>

        <div class="modal-body">
          <form @submit.prevent="run">
            <div class="mb-3">
              <label class="form-label" for="importTarget">{{ $t('importDataset.dataset') }}</label>
              <select id="importTarget" v-model="target" class="form-select" :disabled="running">
                <option value="new">{{ $t('importDataset.newDataset') }}</option>
                <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
              <template v-if="target === 'new'">
                <input
                  v-model="newName"
                  class="form-control mt-2"
                  :placeholder="$t('importDataset.newName')"
                  :disabled="running"
                />
                <label class="form-label small mt-2 mb-1">{{ $t('datasetTask.label') }}</label>
                <TaskPicker v-model="newTask" compact :disabled="running" />
              </template>
            </div>

            <div class="mb-3">
              <label class="form-label">{{ $t('importDataset.images') }}</label>
              <div class="d-flex gap-2 flex-wrap">
                <button type="button" class="btn btn-outline-primary btn-sm" :disabled="running" @click="$refs.files.click()">
                  <i class="fa fa-file-image-o" /> {{ $t('importDataset.chooseImages') }}
                </button>
                <button type="button" class="btn btn-outline-primary btn-sm" :disabled="running" @click="$refs.folder.click()">
                  <i class="fa fa-folder-open-o" /> {{ $t('importDataset.chooseFolder') }}
                </button>
                <button
                  v-if="images.length || yoloLabels.length"
                  type="button"
                  class="btn btn-link btn-sm"
                  :disabled="running"
                  @click="images = []; yoloLabels = []; yoloNames = null"
                >
                  {{ $t('importDataset.clear') }}
                </button>
              </div>
              <input ref="files" type="file" multiple :accept="imageAccept" class="d-none" @change="addImages" />
              <input ref="folder" type="file" webkitdirectory directory multiple class="d-none" @change="addImages" />
              <div class="form-text">
                <span v-if="images.length">{{ $t('importDataset.selected', { n: images.length, size: totalSize }) }}</span>
                <span v-else>{{ $t('importDataset.imagesHint') }}</span>
              </div>
              <div v-if="yoloLabels.length" class="form-text text-success">
                <i class="fa fa-check" />
                {{ $t('yolo.folderFound', { n: yoloLabels.length }) }}
                <span v-if="!yoloNames" class="text-warning">{{ $t('yolo.noNames') }}</span>
              </div>
            </div>

            <div class="mb-3">
              <VideoList ref="videoList" :disabled="running" @change="videoState = $event" />
            </div>

            <div class="mb-3">
              <label class="form-label" for="importCoco">{{ $t('importDataset.coco') }}</label>
              <input
                id="importCoco"
                ref="coco"
                type="file"
                accept=".json,application/json,.zip,application/zip"
                class="form-control"
                :disabled="running"
                @change="coco = $event.target.files[0] || null"
              />
              <div class="form-text">{{ yoloLabels.length && !coco ? $t('yolo.folderUsed') : $t('importDataset.cocoHint') }}</div>
              <div v-if="isYolo || (yoloLabels.length && !coco)" class="mt-2">
                <label class="form-label" for="importDatasetYoloTask">{{ $t('yolo.task') }}</label>
                <select id="importDatasetYoloTask" v-model="yoloTask" class="form-select" :disabled="running">
                  <option value="auto">{{ $t('yolo.auto') }}</option>
                  <option v-for="t in yoloTasks" :key="t" :value="t">{{ $t('yolo.' + t) }}</option>
                </select>
                <div class="form-text">{{ $t('yolo.importHint') }}</div>
              </div>
            </div>

            <div v-if="running || progress.total" class="mb-2">
              <div class="progress" style="height: 20px">
                <div class="progress-bar" :style="{ width: percent + '%' }">
                  {{ progress.done }} / {{ progress.total }}
                </div>
              </div>
              <div class="form-text">
                {{ $t('importDataset.progress', { skipped: progress.skipped, failed: progress.failed.length }) }}
              </div>
            </div>
          </form>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-primary" :disabled="!canRun || running" @click="run">
            <i v-if="running" class="fa fa-spinner fa-spin" />
            {{ $t('importDataset.import') }}
          </button>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" :disabled="running">
            {{ $t('importDataset.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { showModal, hideModal } from "@/libs/modal";
import Dataset, { isYoloFile } from "@/models/datasets";
import TaskPicker from "@/components/TaskPicker.vue";
import VideoList from "@/components/VideoList.vue";

const IMAGE_EXT = [".gif", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"];
const PARALLEL_UPLOADS = 4;

/** YOLO label / class-name files that come along when a dataset folder is picked */
function isYoloText(file) {
  const name = file.name.toLowerCase();
  if (name.startsWith(".")) return null;
  if (/\.(ya?ml|names)$/.test(name) || name === "classes.txt") return "names";
  if (name.endsWith(".txt") && !/^readme/.test(name)) return "label";
  return null;
}

/** data.yaml beats other .yaml files, which beat classes.txt / obj.names */
function namesRank(file) {
  if (!file) return 0;
  const name = file.name.toLowerCase();
  return name === "data.yaml" || name === "data.yml" ? 3 : /\.ya?ml$/.test(name) ? 2 : 1;
}

function isImage(file) {
  const name = file.name.toLowerCase();
  return !name.startsWith(".") && IMAGE_EXT.some(ext => name.endsWith(ext));
}

export default {
  name: "ImportDatasetModal",
  components: { TaskPicker, VideoList },
  emits: ["done"],
  data() {
    return {
      datasets: [],
      target: "new",
      newName: "",
      images: [],
      coco: null,
      newTask: "",
      videoState: { count: 0, ready: 0, busy: false, valid: true },
      yoloLabels: [],
      yoloNames: null,
      yoloTask: "auto",
      yoloTasks: ["detect", "segment", "obb", "pose"],
      running: false,
      progress: { done: 0, total: 0, skipped: 0, failed: [] },
      imageAccept: IMAGE_EXT.join(",")
    };
  },
  computed: {
    isYolo() {
      return isYoloFile(this.coco);
    },
    canRun() {
      const hasTarget = this.target !== "new" || this.newName.trim().length > 0;
      // videos must have finished uploading (their length is known) before the import
      const v = this.videoState;
      const videosOk = !v.count || (!v.busy && v.valid);
      return hasTarget && videosOk &&
        (this.images.length > 0 || v.ready > 0 || this.coco || this.yoloLabels.length > 0 || this.target === "new");
    },
    percent() {
      return this.progress.total ? Math.round((100 * this.progress.done) / this.progress.total) : 0;
    },
    totalSize() {
      const mb = this.images.reduce((n, f) => n + f.size, 0) / 1024 / 1024;
      return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
    }
  },
  methods: {
    open(datasetId) {
      this.target = datasetId || "new";
      this.newName = "";
      this.newTask = "";
      this.images = [];
      this.coco = null;
      if (this.$refs.videoList) this.$refs.videoList.clear();
      this.yoloLabels = [];
      this.yoloNames = null;
      this.yoloTask = "auto";
      this.progress = { done: 0, total: 0, skipped: 0, failed: [] };
      if (this.$refs.coco) this.$refs.coco.value = "";
      showModal("#importDataset");
      axios.get("/api/dataset/").then(r => {
        this.datasets = (r.data || []).sort((a, b) => a.name.localeCompare(b.name));
      });
    },
    addImages(event) {
      const seen = new Set(this.images.map(f => f.name));
      const labels = new Set(this.yoloLabels.map(f => f.webkitRelativePath || f.name));
      for (const file of event.target.files) {
        // a folder pick includes everything: keep the images, once per name
        if (isImage(file) && !seen.has(file.name)) {
          seen.add(file.name);
          this.images.push(file);
          continue;
        }
        // ... and the YOLO labels + data.yaml / classes.txt of a YOLO dataset folder
        const kind = isYoloText(file);
        const path = file.webkitRelativePath || file.name;
        if (kind === "label" && !labels.has(path)) {
          labels.add(path);
          this.yoloLabels.push(file);
        } else if (kind === "names" && namesRank(file) > namesRank(this.yoloNames)) {
          this.yoloNames = file;
        }
      }
      event.target.value = "";
    },
    async createDataset() {
      const response = await axios.post("/api/dataset/", { name: this.newName.trim(), task: this.newTask });
      return response.data.id;
    },
    async uploadAll(datasetId) {
      const queue = [...this.images];
      this.progress = { done: 0, total: queue.length, skipped: 0, failed: [] };
      const worker = async () => {
        while (queue.length) {
          const file = queue.shift();
          const form = new FormData();
          form.append("image", file);
          form.append("dataset_id", datasetId);
          try {
            const r = await axios.post("/api/image/", form, {
              headers: { "Content-Type": "multipart/form-data" }
            });
            if (r.data.existed) this.progress.skipped += 1;
          } catch {
            this.progress.failed.push(file.name);
          }
          this.progress.done += 1;
        }
      };
      await Promise.all(Array.from({ length: PARALLEL_UPLOADS }, worker));
    },
    /** The label files of a picked YOLO folder, zipped like a YOLO export */
    async yoloZip() {
      // only needed here: loaded the first time
      const { zipSync, strToU8 } = await import("fflate");
      const entries = {};
      const files = this.yoloNames ? [...this.yoloLabels, this.yoloNames] : this.yoloLabels;
      for (const file of files) {
        const path = (file.webkitRelativePath || file.name).replace(/^\/+/, "");
        entries[path] = strToU8(await file.text());
      }
      return new File([zipSync(entries, { level: 6 })], "labels.zip", { type: "application/zip" });
    },
    async importVideos(datasetId) {
      const frames = await this.$refs.videoList.importInto(datasetId, this.waitForTask);
      this.$toastr.success(this.$t("video.done", { n: frames, videos: this.videoState.ready }));
      this.$refs.videoList.reset();
    },
    async waitForTask(id, onProgress) {
      for (;;) {
        const tasks = (await axios.get("/api/tasks/")).data || [];
        const task = tasks.find(t => t.id === id);
        if (!task || task.completed) return task;
        onProgress(task.progress || 0);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    },
    async run() {
      if (!this.canRun || this.running) return;
      this.running = true;
      let datasetId = this.target;
      try {
        if (this.target === "new") datasetId = await this.createDataset();
        if (this.images.length) await this.uploadAll(datasetId);
        if (this.videoState.ready) await this.importVideos(datasetId);

        let importTask = null;
        const annotations = this.coco || (this.yoloLabels.length ? await this.yoloZip() : null);
        if (annotations) {
          const r = await Dataset.uploadAnnotations(datasetId, annotations, this.yoloTask);
          importTask = r.data.id;
          const s = r.data.stats;
          if (s && s.unmatched) {
            this.$toastr.warning(this.$t("yolo.unmatched", { n: s.unmatched, names: s.unmatched_examples.join(", ") }));
          }
          if (s && !r.data.names_found) this.$toastr.warning(this.$t("yolo.noNames"));
        }

        const p = this.progress;
        const uploaded = p.total - p.skipped - p.failed.length;
        this.$toastr.success(this.$t("importDataset.done", { uploaded, skipped: p.skipped }));
        if (p.failed.length) {
          this.$toastr.warning(
            this.$t("importDataset.failed", { n: p.failed.length, names: p.failed.slice(0, 5).join(", ") })
          );
        }
        hideModal("#importDataset");
        this.$emit("done", { datasetId, importTask });
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error), this.$t("importDataset.title"));
      } finally {
        this.running = false;
      }
    }
  }
};
</script>

<style scoped>
</style>
