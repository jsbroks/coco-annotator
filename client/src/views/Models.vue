<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light models-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1"><i class="fa fa-cubes" /> {{ $t('models.title') }}</h3>
            <div class="text-muted small">{{ $t('models.subtitle') }}</div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="loading" @click="load">
            <i class="fa fa-refresh" :class="{ 'fa-spin': loading }" /> {{ $t('trash.refresh') }}
          </button>
        </div>

        <div v-if="data && !data.installed" class="alert alert-warning">{{ $t('modelRun.notInstalled') }}</div>

        <template v-if="data && data.installed">
          <!-- server -->
          <div class="row g-2 mb-3">
            <div class="col-md-4">
              <div class="card h-100 p-3 shadow-sm">
                <div class="small text-muted">{{ $t('models.device') }}</div>
                <div class="fw-semibold"><i class="fa" :class="(data.device || '').startsWith('cuda') ? 'fa-bolt text-success' : 'fa-microchip'" /> {{ data.device }}</div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card h-100 p-3 shadow-sm">
                <div class="small text-muted">{{ $t('models.sam') }}</div>
                <div class="fw-semibold">
                  <template v-if="data.sam && data.sam.available"><i class="fa fa-check text-success" /> {{ data.sam.checkpoint }}</template>
                  <span v-else class="text-muted">{{ $t('models.samOff') }}</span>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card h-100 p-3 shadow-sm">
                <div class="small text-muted">{{ $t('models.count') }}</div>
                <div class="fw-semibold">{{ $t('models.countValue', { n: data.models.length, on: enabledCount }) }}</div>
              </div>
            </div>
          </div>

          <!-- upload -->
          <div v-if="data.can_manage" class="card p-3 mb-3 shadow-sm">
            <label class="form-label fw-semibold mb-1" for="modelUpload">{{ $t('modelRun.uploadModel') }}</label>
            <div class="input-group input-group-sm">
              <input id="modelUpload" ref="file" type="file" accept=".pt,.task,.tflite" class="form-control" :disabled="uploading" @change="e => (file = e.target.files[0] || null)" />
              <button type="button" class="btn btn-primary" :disabled="!file || uploading" @click="upload">
                <i v-if="uploading" class="fa fa-spinner fa-spin" />
                {{ uploading ? `${uploadProgress}%` : $t('modelRun.upload') }}
              </button>
            </div>
            <div class="form-text">{{ $t('modelRun.uploadHint') }}</div>
          </div>
          <div v-else class="alert alert-light border small">{{ $t('models.readOnly') }}</div>

          <!-- MediaPipe's official models -->
          <div v-if="data.can_manage && catalog" class="card p-3 mb-3 shadow-sm">
            <div class="d-flex align-items-center flex-wrap gap-2 mb-1">
              <span class="fw-semibold">{{ $t('models.mediapipe.title') }}</span>
              <span class="badge text-bg-info">MediaPipe</span>
              <a href="#" class="small ms-auto" @click.prevent="showCatalog = !showCatalog">
                {{ showCatalog ? $t('trash.hideItems') : $t('models.mediapipe.show', { n: catalog.models.length }) }}
              </a>
            </div>
            <div class="form-text mt-0">{{ $t('models.mediapipe.hint') }}</div>
            <div v-if="!catalog.installed" class="alert alert-warning small mt-2 mb-0">{{ $t('models.mediapipe.notInstalled') }}</div>
            <div v-else-if="showCatalog" class="mt-2">
              <div v-for="group in catalogGroups" :key="group.task" class="mb-2">
                <div class="small text-muted fw-semibold mb-1">{{ $t('models.mediapipe.task.' + group.task) }}</div>
                <div v-for="c in group.models" :key="c.key" class="d-flex align-items-center gap-2 catalog-row">
                  <div class="flex-grow-1 min-w-0">
                    <span class="fw-semibold">{{ c.key }}</span>
                    <span class="small text-muted ms-1">{{ c.size_mb }} MB</span>
                    <div class="small text-muted">{{ $t('models.mediapipe.about.' + c.key) }}</div>
                  </div>
                  <span v-if="c.added" class="small text-success text-nowrap"><i class="fa fa-check" /> {{ $t('models.mediapipe.added') }}</span>
                  <button v-else type="button" class="btn btn-sm btn-outline-primary text-nowrap" :disabled="!!installing" @click="install(c)">
                    <i class="fa" :class="installing === c.key ? 'fa-spinner fa-spin' : 'fa-download'" />
                    {{ installing === c.key ? $t('models.mediapipe.adding') : $t('models.mediapipe.add') }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!data.models.length" class="text-center text-muted py-5">
            <i class="fa fa-cubes fa-3x d-block mb-2" />{{ $t('models.none') }}
          </div>

          <!-- models -->
          <div v-for="m in data.models" :key="m.name" class="card model-card mb-3 shadow-sm" :class="{ off: !m.enabled }">
            <div class="card-body">
              <div class="d-flex align-items-start gap-3 flex-wrap">
                <div class="flex-grow-1 min-w-0">
                  <div class="d-flex align-items-center flex-wrap gap-2">
                    <h5 class="mb-0 text-break">{{ m.display_name || m.name }}</h5>
                    <span v-if="m.task" class="badge text-bg-dark">{{ taskLabel(m.task) }}</span>
                    <span v-if="m.framework === 'mediapipe'" class="badge text-bg-info">MediaPipe</span>
                    <span v-if="!m.enabled" class="badge text-bg-secondary">{{ $t('models.off') }}</span>
                    <span v-if="m.error" class="badge text-bg-danger">{{ $t('modelRun.cannotLoad') }}</span>
                  </div>
                  <div class="small text-muted meta mt-1">
                    <span v-if="m.display_name"><i class="fa fa-file-o" /> {{ m.name }}</span>
                    <span v-if="m.size">{{ size(m.size) }}</span>
                    <span v-if="m.uploaded_by">{{ $t('models.uploadedBy', { user: m.uploaded_by, time: when(m.uploaded_at) }) }}</span>
                    <span v-else-if="m.modified">{{ $t('models.fileDate', { time: when(new Date(m.modified * 1000).toISOString()) }) }}</span>
                  </div>
                  <div v-if="m.note && !editing[m.name]" class="note mt-2">{{ m.note }}</div>
                  <div v-if="m.error" class="small text-danger mt-1">{{ m.error }}</div>
                </div>

                <div v-if="data.can_manage" class="d-flex flex-column align-items-end gap-2 flex-shrink-0">
                  <div class="form-check form-switch mb-0">
                    <input :id="'on-' + m.name" class="form-check-input" type="checkbox" :checked="m.enabled" :disabled="busy[m.name]" @change="save(m, { enabled: $event.target.checked })" />
                    <label class="form-check-label small" :for="'on-' + m.name">{{ m.enabled ? $t('models.on') : $t('models.off') }}</label>
                  </div>
                  <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-secondary" @click="toggleEdit(m)">
                      <i class="fa fa-pencil" /> {{ $t('models.edit') }}
                    </button>
                    <a class="btn btn-outline-secondary" :href="`${modelUrl(m.name)}/download`">
                      <i class="fa fa-download" /> {{ $t('models.download') }}
                    </a>
                    <button type="button" class="btn btn-outline-danger" @click="remove(m)">
                      <i class="fa fa-trash-o" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- edit -->
              <div v-if="editing[m.name]" class="edit-box mt-3">
                <div class="row g-2">
                  <div class="col-md-6">
                    <label class="form-label small mb-0">{{ $t('models.displayName') }}</label>
                    <input v-model="editing[m.name].display_name" class="form-control form-control-sm" :placeholder="m.name" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label small mb-0">
                      {{ $t('models.defaultConf') }}:
                      <strong>{{ editing[m.name].default_conf == null ? $t('models.notSet') : Number(editing[m.name].default_conf).toFixed(2) }}</strong>
                      <a v-if="editing[m.name].default_conf != null" href="#" class="ms-1" @click.prevent="editing[m.name].default_conf = null">{{ $t('models.clear') }}</a>
                    </label>
                    <input
                      type="range" class="form-range" min="0.05" max="0.95" step="0.05"
                      :value="editing[m.name].default_conf == null ? 0.25 : editing[m.name].default_conf"
                      @input="editing[m.name].default_conf = Number($event.target.value)"
                    />
                  </div>
                  <div class="col-12">
                    <label class="form-label small mb-0">{{ $t('models.note') }}</label>
                    <textarea v-model="editing[m.name].note" class="form-control form-control-sm" rows="2" :placeholder="$t('models.notePlaceholder')" />
                  </div>
                </div>
                <div class="d-flex gap-2 mt-2">
                  <button type="button" class="btn btn-sm btn-primary" :disabled="busy[m.name]" @click="save(m, editing[m.name], true)">{{ $t('models.save') }}</button>
                  <button type="button" class="btn btn-sm btn-link" @click="toggleEdit(m)">{{ $t('review.cancel') }}</button>
                </div>
              </div>

              <!-- classes -->
              <div v-if="m.classes && m.classes.length" class="mt-3">
                <div class="small fw-semibold mb-1">{{ $t('modelRun.classes', { n: m.classes.length }) }}</div>
                <div class="d-flex flex-wrap gap-1">
                  <span v-for="c in (showAll[m.name] ? m.classes : m.classes.slice(0, 24))" :key="c" class="badge text-bg-light border">{{ c }}</span>
                  <a v-if="m.classes.length > 24" href="#" class="small ms-1" @click.prevent="showAll = { ...showAll, [m.name]: !showAll[m.name] }">
                    {{ showAll[m.name] ? $t('trash.hideItems') : $t('models.moreClasses', { n: m.classes.length - 24 }) }}
                  </a>
                </div>
              </div>

              <!-- usage -->
              <div v-if="m.usage" class="usage small mt-3">
                <span><i class="fa fa-play" /> {{ $t('models.runs', { n: m.usage.runs }) }}</span>
                <span><i class="fa fa-object-group" /> {{ $t('models.made', { n: m.usage.annotations.toLocaleString() }) }}</span>
                <span v-if="m.usage.last_used">{{ $t('models.lastUsed', { time: when(m.usage.last_used), user: m.usage.last_user || '?' }) }}</span>
                <span v-else class="text-muted">{{ $t('models.neverUsed') }}</span>
                <span v-if="m.default_conf != null">{{ $t('models.defaultConf') }} {{ m.default_conf.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </template>

        <div v-if="!data" class="text-muted"><i class="fa fa-spinner fa-spin" /></div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

/** Uploaded YOLO / MediaPipe models: on / off, name, note, default confidence, usage, upload, download, delete. */
export default {
  name: "Models",
  data() {
    return {
      data: null, loading: false, file: null, uploading: false, uploadProgress: 0, editing: {}, busy: {}, showAll: {},
      // MediaPipe's official models (admins can add them from here)
      catalog: null, showCatalog: false, installing: null
    };
  },
  computed: {
    enabledCount() {
      return this.data ? this.data.models.filter(m => m.enabled).length : 0;
    },
    catalogGroups() {
      const groups = [];
      for (const c of (this.catalog && this.catalog.models) || []) {
        let group = groups.find(g => g.task === c.task);
        if (!group) groups.push((group = { task: c.task, models: [] }));
        group.models.push(c);
      }
      return groups;
    }
  },
  created() {
    this.load();
  },
  methods: {
    /** a model's API path: "trained/x.pt" keeps its "/" (an encoded %2F
     *  is refused by many reverse proxies: 404) */
    modelUrl(name) {
      return "/api/model/yolo/model/" + name.split("/").map(encodeURIComponent).join("/");
    },
    load() {
      this.loading = true;
      return axios
        .get("/api/model/yolo", { params: { all: 1 } })
        .then(r => {
          this.data = r.data;
          if (r.data.can_manage) return this.loadCatalog();
        })
        .finally(() => (this.loading = false));
    },
    loadCatalog() {
      return axios
        .get("/api/model/mediapipe/catalog")
        .then(r => (this.catalog = r.data))
        .catch(() => (this.catalog = null));
    },
    async install(c) {
      if (this.installing) return;
      this.installing = c.key;
      try {
        const r = await axios.post(`/api/model/mediapipe/install/${encodeURIComponent(c.key)}`);
        this.$toastr.success(this.$t("modelRun.uploaded", { name: r.data.model.name }));
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error), c.key);
      } finally {
        this.installing = null;
      }
    },
    taskLabel(task) {
      const key = "modelRun.task." + task;
      return this.$te(key) ? this.$t(key) : task;
    },
    size(bytes) {
      const mb = bytes / 1024 / 1024;
      return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
    },
    when(iso) {
      if (!iso) return "-";
      const d = new Date(iso);
      const pad = n => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },
    toggleEdit(m) {
      const next = { ...this.editing };
      if (next[m.name]) delete next[m.name];
      else next[m.name] = { display_name: m.display_name, note: m.note, default_conf: m.default_conf };
      this.editing = next;
    },
    async save(m, changes, closeEditor = false) {
      this.busy = { ...this.busy, [m.name]: true };
      try {
        const r = await axios.put(this.modelUrl(m.name), changes);
        Object.assign(m, r.data.model);
        if (closeEditor) this.toggleEdit(m);
        this.$toastr.success(this.$t("models.saved", { name: m.display_name || m.name }));
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
        await this.load();
      } finally {
        this.busy = { ...this.busy, [m.name]: false };
      }
    },
    async remove(m) {
      if (!confirm(this.$t("modelRun.confirmDelete", { name: m.name }))) return;
      try {
        await axios.delete(this.modelUrl(m.name));
        this.$toastr.success(this.$t("modelRun.deleted", { name: m.name }));
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      }
    },
    send(overwrite) {
      const form = new FormData();
      form.append("file", this.file);
      form.append("overwrite", overwrite ? "true" : "false");
      this.uploadProgress = 0;
      return axios.post("/api/model/yolo/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: e => {
          if (e.total) this.uploadProgress = Math.round((100 * e.loaded) / e.total);
        }
      });
    },
    async upload() {
      if (!this.file || this.uploading) return;
      this.uploading = true;
      try {
        const r = await this.send(false).catch(error => {
          if (!(error.response && error.response.status === 409)) throw error;
          if (!confirm(this.$t("modelRun.confirmOverwrite", { name: this.file.name }))) return null;
          return this.send(true);
        });
        if (!r) return;
        this.$toastr.success(this.$t("modelRun.uploaded", { name: r.data.model.name }));
        this.file = null;
        if (this.$refs.file) this.$refs.file.value = "";
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error), this.$t("modelRun.uploadModel"));
      } finally {
        this.uploading = false;
      }
    }
  }
};
</script>

<style scoped>
.models-page {
  text-align: left;
}
.model-card.off {
  opacity: 0.7;
}
.min-w-0 {
  min-width: 0;
}
.meta span + span::before,
.usage span + span::before {
  content: "·";
  margin: 0 6px;
  color: #adb5bd;
}
.note {
  white-space: pre-wrap;
  background: #f8f9fa;
  border-left: 3px solid #2a78d6;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 0.875rem;
}
.edit-box {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 10px;
}
.catalog-row {
  padding: 4px 0;
  border-top: 1px solid #f1f3f5;
}
.usage {
  color: #495057;
  border-top: 1px solid #e9ecef;
  padding-top: 8px;
}
</style>
