<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light activity-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <!-- header -->
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1"><i class="fa fa-history" /> {{ $t('activity.title') }}</h3>
            <div class="text-muted small">
              {{ data && data.days ? $t('activity.keepDays', { days: data.days }) : $t('activity.keepForever') }}
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="loading" @click="load()">
            <i class="fa fa-refresh" :class="{ 'fa-spin': loading }" /> {{ $t('trash.refresh') }}
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline-danger"
            :disabled="!data || !data.counts.trash || busy"
            @click="emptyTrash"
          >
            <i class="fa fa-trash" /> {{ $t('trash.empty') }}
          </button>
        </div>

        <!-- groups -->
        <ul class="nav nav-pills mb-3 flex-wrap gap-1">
          <li v-for="g in GROUPS" :key="g" class="nav-item">
            <a href="#" class="nav-link py-1 px-3" :class="{ active: group === g }" @click.prevent="setGroup(g)">
              <i class="fa fa-fw" :class="GROUP_ICONS[g]" />
              {{ $t('activity.group.' + g) }}
              <span class="badge rounded-pill ms-1" :class="group === g ? 'text-bg-light' : 'text-bg-secondary'">
                {{ data ? data.counts[g] || 0 : 0 }}
              </span>
            </a>
          </li>
        </ul>

        <!-- filters -->
        <div class="row g-2 mb-3">
          <div class="col-md-4">
            <select v-model="filters.dataset_id" class="form-select form-select-sm">
              <option value="">{{ $t('trash.allDatasets') }}</option>
              <option v-for="d in (data ? data.datasets : [])" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div class="col-md-3">
            <select v-model="filters.user" class="form-select form-select-sm">
              <option value="">{{ $t('activity.anyone') }}</option>
              <option v-for="u in (data ? data.users : [])" :key="u" :value="u">
                {{ u === '-' ? $t('activity.system') : u }}
              </option>
            </select>
          </div>
          <div class="col-md-5">
            <input v-model="search" class="form-control form-control-sm" :placeholder="$t('trash.search')" />
          </div>
        </div>

        <!-- bulk bar (trash) -->
        <div v-if="group === 'trash' && restorable.length" class="d-flex align-items-center flex-wrap gap-2 mb-2 bulk-bar">
          <div class="form-check mb-0">
            <input id="trashAll" class="form-check-input" type="checkbox" :checked="allChecked" @change="toggleAll" />
            <label class="form-check-label small" for="trashAll">{{ $t('trash.selectPage') }}</label>
          </div>
          <span class="small text-muted">{{ $t('trash.selectedN', { n: selectedEntries.length }) }}</span>
          <button
            type="button"
            class="btn btn-sm btn-success ms-auto"
            :disabled="!selectedEntries.length || busy"
            @click="restoreEntries(selectedEntries)"
          >
            <i class="fa fa-undo" /> {{ $t('trash.restoreSelected') }}
          </button>
          <button
            type="button"
            class="btn btn-sm btn-danger"
            :disabled="!selectedEntries.length || busy"
            @click="purgeEntries(selectedEntries)"
          >
            <i class="fa fa-times" /> {{ $t('trash.purgeSelected') }}
          </button>
        </div>

        <div v-if="!data" class="text-muted"><i class="fa fa-spinner fa-spin" /></div>
        <div v-else-if="!data.entries.length" class="text-center text-muted py-5">
          <i class="fa fa-3x mb-2 d-block" :class="group === 'trash' ? 'fa-trash-o' : 'fa-history'" />
          {{ hasFilters ? $t('trash.noMatch') : (group === 'trash' ? $t('trash.isEmpty') : $t('activity.isEmpty')) }}
        </div>

        <!-- entries by day -->
        <template v-for="day in days" :key="day.key">
          <div class="day-label small fw-semibold text-muted mt-3 mb-1">{{ day.label }}</div>
          <div
            v-for="e in day.entries"
            :key="e.id"
            class="card mb-2 shadow-sm entry"
            :class="{ checked: selected[e.id], faded: e.action === 'delete' && !e.trash.in_trash }"
          >
            <div class="card-body p-2 d-flex gap-3 align-items-start">
              <input
                v-if="group === 'trash'"
                v-model="selected[e.id]"
                class="form-check-input mt-1 flex-shrink-0"
                type="checkbox"
              />
              <span class="action-icon flex-shrink-0" :class="'g-' + groupOf(e)">
                <i class="fa fa-fw" :class="iconOf(e)" />
              </span>

              <div v-if="hasVisual(e)" class="preview flex-shrink-0">
                <img
                  v-if="previewUrl(e)"
                  :src="previewUrl(e)"
                  loading="lazy"
                  alt=""
                  @error="$event.target.style.visibility = 'hidden'"
                />
                <span v-else-if="e.detail.color" class="swatch" :style="{ backgroundColor: e.detail.color }" />
              </div>

              <div class="flex-grow-1 min-w-0">
                <div class="sentence">
                  <strong>{{ e.user || $t('activity.system') }}</strong>
                  {{ sentence(e) }}
                </div>

                <div v-if="chips(e).length" class="d-flex flex-wrap gap-1 mt-1">
                  <span v-for="c in chips(e)" :key="c.name" class="cat-chip">
                    <span v-if="c.color !== undefined" class="dot" :style="{ backgroundColor: c.color || '#adb5bd' }" />
                    {{ c.name }}<template v-if="c.n"> × {{ c.n }}</template>
                  </span>
                </div>

                <div v-if="e.detail.note" class="small fst-italic mt-1">“{{ e.detail.note }}”</div>

                <div class="meta small text-muted mt-1">
                  <span v-if="e.dataset">
                    <i class="fa fa-database me-1" />
                    <RouterLink v-if="!e.dataset.deleted" :to="`/dataset/${e.dataset.id}`" class="text-muted">{{ e.dataset.name }}</RouterLink>
                    <template v-else>{{ e.dataset.name }}</template>
                  </span>
                  <span :title="e.updated_at"><i class="fa fa-clock-o" /> {{ when(e) }}</span>
                  <span v-if="e.action === 'delete'" :class="stateClass(e)">{{ trashState(e) }}</span>
                  <span v-if="e.undone" class="text-danger">
                    {{ $t('activity.undoneBy', { user: e.undone.by || '?' }) }}
                  </span>
                </div>

                <div v-if="e.action === 'delete' && e.trash.in_trash && parentNote(e)" class="small text-warning-emphasis mt-1">
                  <i class="fa fa-info-circle" /> {{ parentNote(e) }}
                </div>

                <!-- the annotations of a multi-annotation delete -->
                <template v-if="e.action === 'delete' && e.type === 'annotation' && e.ids.length > 1">
                  <a href="#" class="small" @click.prevent="toggleOpen(e.id)">
                    {{ open[e.id] ? $t('trash.hideItems') : $t('trash.showItems', { n: e.ids.length }) }}
                  </a>
                  <div v-if="open[e.id]" class="d-flex flex-wrap gap-2 mt-2">
                    <div v-for="item in itemsInTrash(e)" :key="item.id" class="mini">
                      <img
                        v-if="e.image"
                        :src="previewSrc(e.image.id, [item.id], 96, true)"
                        loading="lazy"
                        alt=""
                        @error="$event.target.style.visibility = 'hidden'"
                      />
                      <div class="small text-truncate">
                        <span class="dot" :style="{ backgroundColor: item.color || '#adb5bd' }" />{{ item.category }}
                      </div>
                      <div class="d-flex gap-1">
                        <button
                          type="button"
                          class="btn btn-sm btn-outline-success py-0 px-1"
                          :title="$t('trash.restore')"
                          :disabled="busy"
                          @click="restoreItems([{ type: 'annotation', ids: [item.id] }], e.id)"
                        ><i class="fa fa-undo" /></button>
                        <button
                          type="button"
                          class="btn btn-sm btn-outline-danger py-0 px-1"
                          :title="$t('trash.purge')"
                          :disabled="busy"
                          @click="purgeItems([{ type: 'annotation', ids: [item.id] }], 1, false, e.id)"
                        ><i class="fa fa-times" /></button>
                      </div>
                    </div>
                  </div>
                </template>
              </div>

              <!-- actions -->
              <div class="d-flex flex-column gap-1 flex-shrink-0 actions">
                <template v-if="e.action === 'delete' && e.trash.in_trash">
                  <button type="button" class="btn btn-sm btn-outline-success" :disabled="busy" @click="restoreEntries([e])">
                    <i class="fa fa-undo" /> {{ $t('trash.restore') }}
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-danger" :disabled="busy" @click="purgeEntries([e])">
                    <i class="fa fa-times" /> {{ $t('trash.purge') }}
                  </button>
                </template>
                <button
                  v-if="e.can_undo"
                  type="button"
                  class="btn btn-sm btn-outline-warning"
                  :disabled="busy"
                  @click="undoImport(e)"
                >
                  <i class="fa fa-reply" /> {{ $t('activity.undoImport') }}
                </button>
                <RouterLink
                  v-if="e.image && !e.image.deleted && e.action !== 'delete'"
                  :to="`/annotate/${e.image.id}`"
                  class="btn btn-sm btn-outline-secondary"
                >
                  <i class="fa fa-pencil" /> {{ $t('activity.open') }}
                </RouterLink>
              </div>
            </div>
          </div>
        </template>

        <div v-if="data && data.pages > 1" class="d-flex justify-content-center mt-3">
          <Pagination :pages="data.pages" :current="page" @pagechange="p => load(p)" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import Pagination from "@/components/Pagination.vue";

const GROUPS = ["all", "annotate", "import", "delete", "trash", "dataset", "review", "admin"];
const GROUP_ICONS = {
  all: "fa-th-list",
  annotate: "fa-pencil",
  import: "fa-exchange",
  delete: "fa-trash-o",
  trash: "fa-trash",
  dataset: "fa-database",
  review: "fa-check-square-o",
  admin: "fa-shield"
};
const ADMIN_ACTIONS = ["user_create", "user_bulk", "user_update", "user_delete", "password_change", "role_create",
  "role_update", "role_delete", "model_upload", "model_update", "model_delete", "task_delete", "task_clear"];
const ACTION_GROUP = {
  ...Object.fromEntries(ADMIN_ACTIONS.map(a => [a, "admin"])),
  annotate: "annotate", copy: "annotate", auto_annotate: "annotate",
  import: "import", video: "import", upload: "import", scan: "import", export: "import",
  delete: "delete", restore: "delete", purge: "delete", undo_import: "delete",
  dataset_create: "dataset", dataset_update: "dataset", dataset_share: "dataset",
  category_create: "dataset", category_update: "dataset", reviewers: "review",
  review: "review", assign: "review", help_request: "review", help_reply: "review"
};
const ICONS = {
  annotate: "fa-pencil", copy: "fa-clone", auto_annotate: "fa-magic",
  import: "fa-upload", video: "fa-film", upload: "fa-picture-o", scan: "fa-folder-open-o",
  export: "fa-download", delete: "fa-trash-o", restore: "fa-undo", purge: "fa-times",
  undo_import: "fa-reply", dataset_create: "fa-plus", dataset_update: "fa-cog",
  dataset_share: "fa-users", category_create: "fa-tag", category_update: "fa-tag",
  reviewers: "fa-user-secret", review: "fa-check-square-o", assign: "fa-share",
  user_create: "fa-user-plus", user_bulk: "fa-users", user_update: "fa-user", user_delete: "fa-user-times",
  password_change: "fa-key", role_create: "fa-id-badge", role_update: "fa-id-badge", role_delete: "fa-id-badge",
  model_upload: "fa-cubes", model_update: "fa-cubes", model_delete: "fa-cubes", task_delete: "fa-tasks",
  task_clear: "fa-tasks", help_request: "fa-life-ring", help_reply: "fa-reply"
};

export default {
  name: "Activity",
  components: { Pagination },
  data() {
    return {
      GROUPS,
      GROUP_ICONS,
      data: null,
      group: this.$route.query.group && GROUPS.includes(this.$route.query.group) ? this.$route.query.group : "all",
      page: 1,
      filters: { dataset_id: "", user: "" },
      search: "",
      searchTimer: null,
      selected: {},
      open: {},
      loading: false,
      busy: false
    };
  },
  computed: {
    entries() {
      return this.data ? this.data.entries : [];
    },
    restorable() {
      return this.entries.filter(e => e.action === "delete" && e.trash.in_trash);
    },
    selectedEntries() {
      return this.restorable.filter(e => this.selected[e.id]);
    },
    allChecked() {
      return this.restorable.length > 0 && this.restorable.every(e => this.selected[e.id]);
    },
    hasFilters() {
      return this.filters.dataset_id !== "" || this.filters.user !== "" || !!this.search.trim();
    },
    /** entries split by local day: 今天 / 昨天 / date */
    days() {
      const out = [];
      const today = new Date();
      const key = d => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
      const yesterday = new Date(today.getTime() - 86400000);
      this.entries.forEach(e => {
        const date = new Date(e.updated_at);
        const k = key(date);
        let day = out[out.length - 1];
        if (!day || day.key !== k) {
          let label = date.toLocaleDateString(this.$i18n.locale, { year: "numeric", month: "long", day: "numeric", weekday: "short" });
          if (k === key(today)) label = this.$t("activity.today");
          else if (k === key(yesterday)) label = this.$t("activity.yesterday");
          day = { key: k, label, entries: [] };
          out.push(day);
        }
        day.entries.push(e);
      });
      return out;
    }
  },
  watch: {
    filters: {
      deep: true,
      handler() {
        this.load(1);
      }
    },
    search() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => this.load(1), 300);
    }
  },
  created() {
    this.load(1);
  },
  methods: {
    load(page = this.page) {
      this.page = page;
      this.loading = true;
      const params = { group: this.group, page, per_page: 30, q: this.search.trim() };
      if (this.filters.dataset_id !== "") params.dataset_id = this.filters.dataset_id;
      if (this.filters.user) params.user = this.filters.user;
      return axios
        .get("/api/activity/", { params })
        .then(r => {
          this.data = r.data;
          this.selected = {};
        })
        .finally(() => (this.loading = false));
    },
    setGroup(g) {
      this.group = g;
      this.$router.replace({ query: g === "all" ? {} : { group: g } }).catch(() => {});
      this.load(1);
    },
    toggleAll(event) {
      const next = {};
      if (event.target.checked) this.restorable.forEach(e => (next[e.id] = true));
      this.selected = next;
    },
    toggleOpen(id) {
      this.open = { ...this.open, [id]: !this.open[id] };
    },
    groupOf(e) {
      return ACTION_GROUP[e.action] || "all";
    },
    iconOf(e) {
      if (e.action === "delete") {
        return { annotation: "fa-object-group", image: "fa-picture-o", category: "fa-tag", dataset: "fa-database" }[e.type] || "fa-trash-o";
      }
      return ICONS[e.action] || "fa-circle-o";
    },

    // ---------------------------------------------------------------- text
    names(list) {
      return (list || []).join("、");
    },
    sentence(e) {
      const d = e.detail || {};
      const c = e.counts || {};
      const t = (key, params) => this.$t("activity.act." + key, params);
      const file = d.file_name || (e.image && e.image.file_name) || "?";
      switch (e.action) {
        case "annotate": {
          const parts = [];
          if (c.added) parts.push(t("added", { n: c.added }));
          if (c.edited) parts.push(t("edited", { n: c.edited }));
          if (d.image_class_set) parts.push(d.image_class ? t("imageClass", { name: d.image_class }) : t("imageClassCleared"));
          return t("annotate", { file, what: parts.join("、") });
        }
        case "copy":
          return t("copy", { n: c.annotations || 0, file, from: d.from_file || "?" });
        case "auto_annotate":
          return d.whole_dataset
            ? t("autoDataset", { model: d.model, n: c.annotations || 0, images: c.images || 0 })
            : t("autoImage", { model: d.model, n: c.annotations || 0, file });
        case "import":
          return t("import", { format: d.format || "COCO", n: c.annotations || 0, images: c.images || 0 }) +
            (d.new_categories && d.new_categories.length ? t("newCategories", { names: this.names(d.new_categories) }) : "");
        case "video":
          return t("video", { file, n: c.images || 0 });
        case "upload":
          return c.images > 1 ? t("uploadMany", { n: c.images }) : t("uploadOne", { file });
        case "scan":
          return t("scan", { n: c.images || 0 });
        case "export":
          return t("export", { format: d.format || "COCO", images: c.images || 0, n: c.annotations || 0 }) +
            (d.split ? t("withSplit") : "") + (d.only_approved ? t("onlyApproved") : "");
        case "train":
          return t("train", { name: d.run ? `#${d.run}` : "", task: d.task || "", epochs: d.epochs || "" });
        case "terminal":
          return t("terminal", { user: d.ssh_user || "", host: d.host || "" });
        case "delete":
          if (e.type === "annotation") return t("deleteAnnotations", { n: c.annotations || e.ids.length, file });
          if (e.type === "image") return d.file_name ? t("deleteImage", { file: d.file_name }) : t("deleteImages", { n: c.images || 0 });
          if (e.type === "category") return t("deleteCategory", { name: d.name });
          if (e.type === "dataset") return t("deleteDataset", { name: d.name, n: c.images || 0 });
          return t("deleteOther", { n: c.items || 0 });
        case "restore":
        case "purge": {
          if (d.empty) return t("empty", { n: c.items || 0 });
          let what = "";
          if (d.kind === "annotation" && d.file_name) what = t("whatAnnotations", { file: d.file_name });
          else if (d.kind === "image" && d.file_name) what = t("whatImage", { file: d.file_name });
          else if ((d.kind === "category" || d.kind === "dataset") && d.name) what = t("whatNamed", { name: d.name });
          return t(e.action, { n: c.items || 0, what });
        }
        case "undo_import":
          return t(d.kind === "image" ? "undoVideo" : "undoImport", { n: c.items || 0, file: d.file_name || d.format || "" });
        case "dataset_create":
          return t("datasetCreate", { name: d.name || (e.dataset && e.dataset.name) });
        case "dataset_update": {
          const parts = [];
          if (d.task !== undefined) parts.push(t("taskChanged", { task: this.$t("datasetTask." + (d.task || "none") + ".name") }));
          if (d.categories_added) parts.push(t("categoriesAdded", { names: this.names(d.categories_added) }));
          if (d.categories_removed) parts.push(t("categoriesRemoved", { names: this.names(d.categories_removed) }));
          if (d.metadata) parts.push(t("metadataChanged"));
          return t("datasetUpdate", { what: parts.join("；") });
        }
        case "dataset_share": {
          const parts = [];
          if (d.added && d.added.length) parts.push(t("membersAdded", { names: this.names(d.added) }));
          if (d.removed && d.removed.length) parts.push(t("membersRemoved", { names: this.names(d.removed) }));
          return t("datasetShare", { what: parts.join("；") });
        }
        case "category_create":
          return t("categoryCreate", { name: d.name });
        case "category_update": {
          let text = d.old_name ? t("categoryRename", { old: d.old_name, name: d.name }) : t("categoryUpdate", { name: d.name });
          if (d.parents) text += "：" + (d.parents.length ? t("parentsChanged", { names: this.names(d.parents) }) : t("parentsCleared"));
          return text;
        }
        case "reviewers":
          return d.reviewers && d.reviewers.length ? t("reviewers", { names: this.names(d.reviewers) }) : t("reviewersCleared");
        case "review": {
          const verb = t("review_" + d.review_action);
          return d.file_name ? t("reviewOne", { verb, file: d.file_name }) : t("reviewMany", { verb, n: c.images || 0 });
        }
        case "assign":
          if (d.unassigned) return t("unassign", { n: c.images || 0 });
          return t("assign", {
            n: c.images || 0,
            people: Object.entries(d.people || {}).map(([u, n]) => `${u} ${n}`).join("、")
          });
        case "help_request":
          return t("helpRequest", { file, msg: d.message || "" });
        case "help_reply":
          return t("helpReply", { file, msg: d.message || "" });
        case "user_create":
          return t("userCreate", { name: this.who(d), role: this.roleLabel(d.role, d.role_name) });
        case "user_bulk":
          return t("userBulk", { n: c.users || 0, names: this.names(d.names || []), role: this.roleLabel(d.role, d.role_name) }) +
            (d.dataset_name ? t("userBulkShared", { name: d.dataset_name }) : "") +
            (c.existing ? t("userBulkExisting", { n: c.existing }) : "");
        case "user_update": {
          const parts = (d.changes || []).map(k => k === "role"
            ? t("roleChanged", { from: this.roleLabel(d.role_from, d.role_from_name), to: this.roleLabel(d.role_to, d.role_to_name) })
            : t("changed_" + k));
          return t("userUpdate", { name: this.who(d), what: parts.join("、") });
        }
        case "user_delete":
          return t("userDelete", { name: this.who(d) });
        case "password_change":
          return d.first_login ? t("passwordFirst") : t("passwordChange");
        case "role_create":
          return t("roleCreate", { name: d.name });
        case "role_update": {
          const parts = [];
          if (d.old_name) parts.push(t("roleRenamed", { old: d.old_name }));
          if (d.added && d.added.length) parts.push(t("permsAdded", { names: d.added.map(p => this.$t("roles.perm." + p)).join("、") }));
          if (d.removed && d.removed.length) parts.push(t("permsRemoved", { names: d.removed.map(p => this.$t("roles.perm." + p)).join("、") }));
          return t("roleUpdate", { name: this.roleLabel(d.key, d.name), what: parts.join("；") });
        }
        case "role_delete":
          return t("roleDelete", { name: d.name, n: c.users || 0 });
        case "model_upload":
          return t(d.replaced ? "modelReplace" : "modelUpload", { name: d.name });
        case "model_update": {
          const parts = (d.changed || []).map(k => k === "enabled" ? t(d.enabled ? "modelOn" : "modelOff")
            : k === "default_conf" ? t("modelConf", { v: d.default_conf ?? "–" }) : t("modelChanged_" + k));
          return t("modelUpdate", { name: d.display_name || d.name, what: parts.join("、") });
        }
        case "model_delete":
          return t("modelDelete", { name: d.display_name ? `${d.display_name}（${d.name}）` : d.name });
        case "task_delete":
          return t("taskDelete", { name: this.$taskName(d.name || "") });
        case "task_clear":
          return t("taskClear", { n: c.items || 0 });
        default:
          return e.action;
      }
    },
    /** "B12345678（王小明）" */
    who(d) {
      return d.display && d.display !== d.name ? `${d.name}（${d.display}）` : d.name;
    },
    roleLabel(key, name) {
      if (!key) return this.$t("roles.builtin.user");
      if (key === "admin" || key === "user") return this.$t("roles.builtin." + key);
      return name || key;
    },
    chips(e) {
      const d = e.detail || {};
      if (e.action === "delete" && e.type === "annotation") return d.categories || [];
      if (e.action === "export" && d.categories) return d.categories.map(name => ({ name }));
      if (e.action === "category_update" && d.old_color) return [{ name: d.name, color: d.color }];
      return [];
    },
    when(e) {
      const date = new Date(e.updated_at);
      const pad = n => String(n).padStart(2, "0");
      let text = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
      if (e.created_at && e.created_at !== e.updated_at) {
        const start = new Date(e.created_at);
        text = `${pad(start.getHours())}:${pad(start.getMinutes())} – ${text}`;
      }
      const minutes = Math.max(0, Math.round((Date.now() - date) / 60000));
      let ago;
      if (minutes < 1) ago = this.$t("trash.justNow");
      else if (minutes < 60) ago = this.$t("trash.minutesAgo", { n: minutes });
      else if (minutes < 60 * 24) ago = this.$t("trash.hoursAgo", { n: Math.round(minutes / 60) });
      else return text;
      return `${text}（${ago}）`;
    },
    trashState(e) {
      const s = e.trash;
      const parts = [];
      if (s.in_trash) {
        parts.push(e.expires_at
          ? this.$t("activity.inTrashDays", { n: Math.max(0, Math.ceil((new Date(e.expires_at) - Date.now()) / 86400000)) })
          : this.$t("activity.inTrash"));
      }
      if (s.restored) parts.push(this.$t("activity.restoredN", { n: s.restored }));
      if (s.purged) parts.push(this.$t("activity.purgedN", { n: s.purged }));
      return parts.join("，");
    },
    stateClass(e) {
      if (!e.trash.in_trash) return e.trash.restored ? "text-success" : "";
      if (e.expires_at && new Date(e.expires_at) - Date.now() < 7 * 86400000) return "text-danger";
      return "text-warning-emphasis";
    },
    parentNote(e) {
      if (e.type === "annotation" && e.image && e.image.deleted) return this.$t("trash.parentImage");
      if ((e.type === "annotation" || e.type === "image") && e.dataset && e.dataset.deleted) return this.$t("trash.parentDataset");
      return "";
    },
    itemsInTrash(e) {
      const ids = new Set(e.ids);
      return (e.detail.items || []).filter(i => ids.has(i.id));
    },

    // ---------------------------------------------------------------- previews
    hasVisual(e) {
      if (e.action === "delete") return ["annotation", "image", "category"].includes(e.type);
      return !!e.image;
    },
    previewSrc(imageId, annotationIds, size, crop) {
      const params = new URLSearchParams({ image_id: imageId, size });
      if (annotationIds && annotationIds.length) params.set("annotations", annotationIds.slice(0, 200).join(","));
      if (crop) params.set("crop", "1");
      return `/api/trash/preview?${params}`;
    },
    previewUrl(e) {
      if (!e.image) return null;
      if (e.action === "delete") {
        if (e.type === "annotation") {
          const ids = e.ids.length ? e.ids : (e.detail.items || []).map(i => i.id);
          return this.previewSrc(e.image.id, ids, 192, ids.length === 1);
        }
        if (e.type === "image") return this.previewSrc(e.image.id, [], 192, false);
        return null;
      }
      return this.previewSrc(e.image.id, e.annotation_ids || [], 192, false);
    },

    // ---------------------------------------------------------------- trash actions
    itemsOf(entries) {
      const byType = {};
      entries.forEach(e => (byType[e.type] = [...(byType[e.type] || []), ...e.ids]));
      return Object.entries(byType).map(([type, ids]) => ({ type, ids }));
    },
    restoreEntries(entries) {
      return this.restoreItems(this.itemsOf(entries), entries.length === 1 ? entries[0].id : null);
    },
    async restoreItems(items, activityId = null, includeParents = false) {
      this.busy = true;
      try {
        const r = await axios.post("/api/trash/restore", { items, include_parents: includeParents, activity_id: activityId });
        this.$toastr.success(this.$t("trash.restored", { n: r.data.restored }));
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        if (error.response && error.response.status === 409 && !includeParents) {
          const parents = data.parents || {};
          const what = [
            parents.image ? this.$t("trash.nImages", { n: parents.image.length }) : null,
            parents.dataset ? this.$t("trash.nDatasets", { n: parents.dataset.length }) : null
          ].filter(Boolean).join("、");
          if (confirm(this.$t("trash.confirmParents", { what }))) {
            this.busy = false;
            return this.restoreItems(items, activityId, true);
          }
        } else {
          this.$toastr.error(data.message || String(error));
        }
      } finally {
        this.busy = false;
      }
    },
    purgeEntries(entries) {
      const files = entries.some(e => e.type === "image" || e.type === "dataset");
      const n = entries.reduce((sum, e) => sum + e.trash.in_trash, 0);
      return this.purgeItems(this.itemsOf(entries), n, files, entries.length === 1 ? entries[0].id : null);
    },
    async purgeItems(items, n, files, activityId = null) {
      const message = this.$t("trash.confirmPurge", { n }) + (files ? "\n\n" + this.$t("trash.filesToo") : "");
      if (!confirm(message)) return;
      this.busy = true;
      try {
        const r = await axios.post("/api/trash/purge", { items, activity_id: activityId });
        this.$toastr.success(this.$t("trash.purged", { n: r.data.deleted }));
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    },
    async emptyTrash() {
      if (!confirm(this.$t("trash.confirmEmpty", { n: this.data.counts.trash }) + "\n\n" + this.$t("trash.filesToo"))) return;
      this.busy = true;
      try {
        const r = await axios.post("/api/trash/empty");
        this.$toastr.success(this.$t("trash.purged", { n: r.data.deleted }));
        await this.load(1);
      } finally {
        this.busy = false;
      }
    },
    async undoImport(e) {
      const kind = e.action === "video" ? "images" : "annotations";
      const n = (e.counts || {})[kind] || 0;
      if (!confirm(this.$t(e.action === "video" ? "activity.confirmUndoVideo" : "activity.confirmUndoImport", { n }))) return;
      this.busy = true;
      try {
        const r = await axios.post(`/api/activity/${e.id}/undo`);
        this.$toastr.success(this.$t("activity.undone", { n: r.data.deleted }));
        await this.load();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    }
  }
};
</script>

<style scoped>
.activity-page {
  text-align: left;
}
.entry.checked {
  outline: 2px solid #0d6efd;
}
.entry.faded {
  opacity: 0.75;
}
.action-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #6c757d;
  margin-top: 2px;
}
.action-icon.g-annotate {
  background: #2a78d6;
}
.action-icon.g-import {
  background: #6f42c1;
}
.action-icon.g-delete {
  background: #c0392b;
}
.action-icon.g-dataset {
  background: #198754;
}
.action-icon.g-review {
  background: #d97706;
}
.action-icon.g-admin {
  background: #343a40;
}
.preview {
  width: 96px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f3f5;
  border-radius: 6px;
  overflow: hidden;
}
.preview img {
  max-width: 100%;
  max-height: 100%;
}
.preview .swatch {
  width: 36px;
  height: 36px;
  border-radius: 50%;
}
.min-w-0 {
  min-width: 0;
}
.sentence {
  word-break: break-word;
}
.meta span + span::before {
  content: "·";
  margin: 0 6px;
}
.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #dee2e6;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 0.75rem;
  background: #fff;
}
.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 3px;
}
.mini {
  width: 104px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 4px;
  background: #fff;
}
.mini img {
  width: 96px;
  height: 64px;
  object-fit: contain;
  background: #f1f3f5;
  border-radius: 4px;
}
.actions .btn {
  white-space: nowrap;
}
.bulk-bar {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f8f9fa;
  padding: 4px 0;
}
.day-label {
  border-bottom: 1px solid #dee2e6;
  padding-bottom: 2px;
}
</style>
