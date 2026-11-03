<template>
  <div class="modal fade" tabindex="-1" role="dialog" :id="modalId">
    <div class="modal-dialog" role="document">
      <div class="modal-content text-start">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ dataset ? $t('modelRun.titleDataset', { name: datasetName }) : $t('modelRun.titleImage') }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>

        <div class="modal-body">
          <div v-if="loading" class="text-muted">
            <i class="fa fa-spinner fa-spin" /> {{ $t('modelRun.loadingModels') }}
          </div>

          <div v-else-if="!installed" class="alert alert-warning mb-0">
            {{ $t('modelRun.notInstalled') }}
          </div>

          <div v-else-if="models.length === 0" class="alert alert-info">
            <span v-if="isAdmin">{{ $t('modelRun.noModelsAdmin') }}</span>
            <i18n-t v-else keypath="modelRun.noModels" tag="span">
              <template #folder><code>models/</code></template>
            </i18n-t>
          </div>

          <form v-if="!loading && installed && models.length" @submit.prevent="run">
            <div class="mb-3">
              <label class="form-label" :for="modalId + 'Model'">{{ $t('modelRun.model') }}</label>
              <div class="input-group">
                <select :id="modalId + 'Model'" v-model="options.model" class="form-select">
                  <option v-for="m in models" :key="m.name" :value="m.name" :disabled="!!m.error">
                    {{ m.display_name ? `${m.display_name} — ${m.name}` : m.name }}{{ m.task ? ` (${taskLabel(m.task)})` : '' }}{{ m.error ? ` — ${$t('modelRun.cannotLoad')}` : '' }}
                  </option>
                </select>
              </div>
              <div v-if="selected && selected.note" class="small note mt-1">{{ selected.note }}</div>
              <div v-if="selected && selected.classes && selected.classes.length" class="form-text">
                <div class="d-flex align-items-center flex-wrap gap-1">
                  <span>{{ $t('modelRun.classes', { n: selected.classes.length }) }}</span>
                  <a href="#" class="ms-auto" @click.prevent="showMap = !showMap">
                    <i class="fa" :class="showMap ? 'fa-caret-down' : 'fa-caret-right'" />
                    {{ $t('modelRun.map.title') }}<template v-if="mappedCount"> ({{ $t('modelRun.map.count', { n: mappedCount }) }})</template>
                  </a>
                </div>
                <template v-if="!showMap">
                  <span
                    v-for="c in selected.classes.slice(0, 30)"
                    :key="c"
                    class="badge me-1"
                    :class="badgeClass(c)"
                  >{{ c }}<template v-if="targetOf(c)"> → {{ targetOf(c).name }}</template></span>
                  <span v-if="selected.classes.length > 30">…</span>
                  <div class="mt-1">{{ $t('modelRun.classesHint') }}</div>
                </template>
                <div v-else class="class-map mt-1">
                  <div v-for="c in selected.classes" :key="c" class="d-flex align-items-center gap-2 mb-1">
                    <span class="badge text-bg-light border class-name text-truncate" :title="c">{{ c }}</span>
                    <i class="fa fa-long-arrow-right text-muted" />
                    <select v-model="classMap[c]" class="form-select form-select-sm">
                      <option value="">{{ autoLabel(c) }}</option>
                      <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
                      <option value="skip">{{ $t('modelRun.map.skip') }}</option>
                    </select>
                    <i v-if="keypointWarning(c)" class="fa fa-exclamation-triangle text-warning" :title="keypointWarning(c)" />
                  </div>
                  <div class="mt-1">{{ $t('modelRun.map.hint') }}</div>
                </div>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label" :for="modalId + 'Conf'">
                {{ $t('modelRun.confidence') }}: <strong>{{ Number(options.conf).toFixed(2) }}</strong>
              </label>
              <input
                :id="modalId + 'Conf'"
                v-model.number="options.conf"
                type="range"
                class="form-range"
                min="0.05"
                max="0.95"
                step="0.05"
              />
              <div class="form-text">{{ $t('modelRun.confidenceHint') }}</div>
            </div>

            <div v-if="$store.getters['user/can']('create_categories')" class="form-check">
              <input :id="modalId + 'Create'" v-model="options.createCategories" type="checkbox" class="form-check-input" />
              <label class="form-check-label" :for="modalId + 'Create'">{{ $t('modelRun.createCategories') }}</label>
            </div>

            <div v-if="dataset" class="form-check">
              <input :id="modalId + 'Skip'" v-model="options.skipAnnotated" type="checkbox" class="form-check-input" />
              <label class="form-check-label" :for="modalId + 'Skip'">{{ $t('modelRun.skipAnnotated') }}</label>
            </div>

            <div v-if="!dataset" class="form-text mt-2">{{ $t('modelRun.imageHint') }}</div>
            <div v-else class="form-text mt-2">{{ $t('modelRun.datasetHint') }}</div>
          </form>

          <div v-if="!loading && installed && $store.getters['user/canPage']('models')" class="upload-section small">
            <RouterLink to="/models" data-bs-dismiss="modal">
              <i class="fa fa-cubes" /> {{ isAdmin ? $t('modelRun.manageModels') : $t('modelRun.seeModels') }}
            </RouterLink>
          </div>
        </div>

        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!canRun || running"
            @click="run"
          >
            <i v-if="running" class="fa fa-spinner fa-spin" />
            {{ $t('modelRun.run') }}
          </button>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
            {{ $t('modelRun.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { showModal } from "@/libs/modal";

const STORAGE_KEY = "modelRunOptions";
// per model: class -> category name (or SKIP), so a choice carries over to
// other datasets that have a category of that name
const MAP_KEY = "modelRunClassMap";
const SKIP = "__skip__";

function loadSaved(key = STORAGE_KEY) {
  try {
    return JSON.parse(localStorage.getItem(key)) || {};
  } catch {
    return {};
  }
}

export default {
  name: "ModelRunModal",
  props: {
    modalId: { type: String, required: true },
    // true: run over the whole dataset (background task); false: one image
    dataset: { type: Boolean, default: false },
    datasetName: { type: String, default: "" },
    // the dataset's categories ({ id, name, keypoint_labels })
    categories: { type: Array, default: () => [] },
    running: { type: Boolean, default: false }
  },
  emits: ["run"],
  data() {
    const saved = loadSaved();
    return {
      loading: false,
      installed: true,
      models: [],
      // class -> "" (same name / new), a category id, or "skip"
      classMap: {},
      showMap: false,
      options: {
        model: saved.model || "",
        conf: saved.conf || 0.25,
        createCategories: saved.createCategories !== false,
        skipAnnotated: saved.skipAnnotated !== false
      }
    };
  },
  watch: {
    "options.model"() {
      this.applyDefaultConf();
      this.loadClassMap();
    },
    categories() {
      this.loadClassMap();
    }
  },
  computed: {
    isAdmin() {
      return this.$store.getters["user/can"]("manage_models");
    },
    selected() {
      return this.models.find(m => m.name === this.options.model);
    },
    canRun() {
      return this.installed && this.selected && !this.selected.error;
    },
    lowerCategoryNames() {
      return this.categories.map(c => String(c.name).toLowerCase());
    },
    mappedCount() {
      return Object.values(this.classMap).filter(v => v !== "").length;
    }
  },
  methods: {
    open() {
      showModal("#" + this.modalId);
      this.loadModels();
    },
    loadModels() {
      this.loading = true;
      axios
        .get("/api/model/yolo")
        .then(response => {
          this.installed = response.data.installed;
          this.models = response.data.models || [];
          if (!this.selected) {
            const usable = this.models.find(m => !m.error);
            this.options.model = usable ? usable.name : "";
          }
          this.applyDefaultConf();
          this.loadClassMap();
        })
        .finally(() => (this.loading = false));
    },
    /** the model's default confidence (set on the Models page), if it has one */
    applyDefaultConf() {
      if (this.selected && this.selected.default_conf != null) this.options.conf = this.selected.default_conf;
    },
    hasCategory(name) {
      return this.lowerCategoryNames.includes(name.toLowerCase());
    },
    sameName(name) {
      return this.categories.find(c => String(c.name).toLowerCase() === name.toLowerCase());
    },
    /** the category a class goes to (chosen, else the same name), or null */
    targetOf(name) {
      const value = this.classMap[name];
      if (value === "skip") return null;
      if (value !== "" && value != null) return this.categories.find(c => c.id === value) || null;
      return null;
    },
    badgeClass(name) {
      if (this.classMap[name] === "skip") return "text-bg-light border text-decoration-line-through";
      return this.targetOf(name) || this.hasCategory(name) ? "text-bg-success" : "text-bg-secondary";
    },
    autoLabel(name) {
      const same = this.sameName(name);
      if (same) return this.$t("modelRun.map.sameName", { name: same.name });
      return this.options.createCategories && this.$store.getters["user/can"]("create_categories")
        ? this.$t("modelRun.map.create", { name })
        : this.$t("modelRun.map.none");
    },
    /** a pose model's points into a category with another number of points */
    keypointWarning(name) {
      const shape = this.selected && this.selected.kpt_shape;
      if (!shape || !shape[0]) return "";
      const target = this.targetOf(name) || (this.classMap[name] === "" ? this.sameName(name) : null);
      const labels = (target && target.keypoint_labels) || [];
      if (!labels.length || labels.length === shape[0]) return "";
      return this.$t("modelRun.map.keypoints", { model: shape[0], category: labels.length, name: target.name });
    },
    loadClassMap() {
      const classes = (this.selected && this.selected.classes) || [];
      const saved = loadSaved(MAP_KEY)[this.options.model] || {};
      const map = {};
      for (const c of classes) {
        const choice = saved[c];
        if (choice === SKIP) map[c] = "skip";
        else {
          const cat = choice && this.categories.find(x => x.name === choice);
          map[c] = cat ? cat.id : "";
        }
      }
      this.classMap = map;
      if (classes.length && classes.length <= 12 && Object.values(map).some(v => v !== "")) this.showMap = true;
    },
    saveClassMap() {
      const all = loadSaved(MAP_KEY);
      const mine = {};
      for (const [c, v] of Object.entries(this.classMap)) {
        if (v === "skip") mine[c] = SKIP;
        else if (v !== "") {
          const cat = this.categories.find(x => x.id === v);
          if (cat) mine[c] = cat.name;
        }
      }
      if (Object.keys(mine).length) all[this.options.model] = mine;
      else delete all[this.options.model];
      try {
        localStorage.setItem(MAP_KEY, JSON.stringify(all));
      } catch {
        // storage unavailable: the choice is just not remembered
      }
    },
    taskLabel(task) {
      const key = "modelRun.task." + task;
      return this.$te(key) ? this.$t(key) : task;
    },
    run() {
      if (!this.canRun || this.running) return;
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.options));
      } catch {
        // storage unavailable: the choice is just not remembered
      }
      this.saveClassMap();
      const classMap = {};
      for (const [c, v] of Object.entries(this.classMap)) {
        if (v === "skip") classMap[c] = null;
        else if (v !== "") classMap[c] = v;
      }
      this.$emit("run", {
        model: this.options.model,
        conf: this.options.conf,
        create_categories: this.options.createCategories,
        skip_annotated: this.options.skipAnnotated,
        ...(Object.keys(classMap).length ? { class_map: classMap } : {})
      });
    }
  }
};
</script>

<style scoped>
.note {
  white-space: pre-wrap;
  color: #495057;
  border-left: 3px solid #2a78d6;
  padding-left: 6px;
}
.class-map {
  max-height: 260px;
  overflow-y: auto;
}
.class-name {
  min-width: 90px;
  max-width: 140px;
}
.upload-section {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid #dee2e6;
}
</style>
