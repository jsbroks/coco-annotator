<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light tasks-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1"><i class="fa fa-tasks" /> {{ $t('tasks.tasks') }}</h3>
            <div class="text-muted small">{{ $t('tasks.subtitle') }}</div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-danger" :disabled="!counts.done || clearing" @click="clearCompleted">
            <i class="fa" :class="clearing ? 'fa-spinner fa-spin' : 'fa-trash'" /> {{ $t('tasks.clearDone', { n: counts.done }) }}
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="loading" @click="updatePage">
            <i class="fa fa-refresh" :class="{ 'fa-spin': loading }" /> {{ $t('trash.refresh') }}
          </button>
        </div>

        <!-- summary: also the filters -->
        <div class="row g-2 mb-3">
          <div v-for="s in summary" :key="s.key" class="col-6 col-md-3">
            <button type="button" class="stat card w-100 text-start shadow-sm" :class="[s.key, { active: filter === s.key }]" @click="filter = filter === s.key ? 'all' : s.key">
              <div class="d-flex align-items-center gap-3">
                <div class="stat-icon"><i class="fa" :class="s.icon" /></div>
                <div>
                  <div class="small text-muted">{{ s.label }}</div>
                  <div class="stat-value">{{ s.n }}</div>
                </div>
              </div>
            </button>
          </div>
        </div>

        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <div class="input-group input-group-sm search-box">
            <span class="input-group-text"><i class="fa fa-search" /></span>
            <input v-model="search" class="form-control" :placeholder="$t('tasks.search')" />
          </div>
          <select v-model="group" class="form-select form-select-sm group-select" :aria-label="$t('tasks.type')">
            <option value="">{{ $t('tasks.allTypes') }}</option>
            <option v-for="g in groups" :key="g" :value="g">{{ $tr('taskGroup', g) }}</option>
          </select>
          <span class="small text-muted ms-auto">{{ $t('tasks.shown', { n: filtered.length, total: tasks.length }) }}</span>
        </div>

        <div class="card shadow-sm task-list">
          <div v-if="!filtered.length" class="text-center text-muted py-5">
            <i class="fa fa-check-circle-o fa-3x d-block mb-2" />
            {{ tasks.length ? $t('exportCategories.noMatch') : $t('tasks.none') }}
          </div>
          <Task
            v-for="task in shownTasks"
            :key="task.id"
            :task="task"
            @deleted="removeTask"
          />
          <div v-if="filtered.length > shownTasks.length" class="text-center py-2 border-top">
            <button type="button" class="btn btn-sm btn-link" @click="limit += 30">
              {{ $t('tasks.more', { n: filtered.length - shownTasks.length }) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import toastrs from "@/mixins/toastrs";
import Task from "@/components/tasks/Task.vue";
import Tasks from "@/models/tasks";
import { taskName } from "@/i18n";

import { mapMutations } from "vuex";

export default {
  name: "Tasks",
  components: { Task },
  mixins: [toastrs],
  data() {
    return {
      tasks: [],
      loading: false,
      clearing: false,
      filter: "all",
      group: "",
      search: "",
      limit: 30
    };
  },
  computed: {
    taskToShow() {
      const id = this.$route.query.id;
      return id == null ? null : parseInt(id);
    },
    groups() {
      return [...new Set(this.tasks.map(t => t.group).filter(Boolean))].sort();
    },
    counts() {
      const c = { all: this.tasks.length, running: 0, done: 0, problems: 0 };
      this.tasks.forEach(t => {
        if (this.isDone(t)) c.done++;
        else c.running++;
        if ((t.errors || 0) > 0 || t.failed) c.problems++;
      });
      return c;
    },
    summary() {
      return [
        { key: "all", icon: "fa-list", label: this.$t("tasks.all"), n: this.counts.all },
        { key: "running", icon: "fa-spinner", label: this.$t("tasks.runningLabel"), n: this.counts.running },
        { key: "done", icon: "fa-check", label: this.$t("tasks.done"), n: this.counts.done },
        { key: "problems", icon: "fa-exclamation-triangle", label: this.$t("tasks.problems"), n: this.counts.problems }
      ];
    },
    filtered() {
      const q = this.search.trim().toLowerCase();
      return this.tasks
        .filter(t => {
          if (this.filter === "running" && this.isDone(t)) return false;
          if (this.filter === "done" && !this.isDone(t)) return false;
          if (this.filter === "problems" && !((t.errors || 0) > 0 || t.failed)) return false;
          if (this.group && t.group !== this.group) return false;
          if (!q) return true;
          return [t.name, taskName(t.name), t.dataset_name, t.creator, String(t.id)]
            .some(v => v && String(v).toLowerCase().includes(q));
        })
        // running first, then newest
        .sort((a, b) => (this.isDone(a) - this.isDone(b)) || b.id - a.id);
    },
    shownTasks() {
      return this.filtered.slice(0, this.limit);
    }
  },
  watch: {
    filter() { this.limit = 30; },
    group() { this.limit = 30; },
    search() { this.limit = 30; },
    taskToShow: "showTask"
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    isDone(t) {
      return !!(t.completed || t.progress >= 100);
    },
    updatePage() {
      const process = "Loading tasks";
      this.addProcess(process);
      this.loading = true;
      Tasks.all()
        .then(response => {
          this.tasks = response.data || [];
          if (this.taskToShow != null) this.showTask(this.taskToShow);
        })
        .finally(() => {
          this.loading = false;
          this.removeProcess(process);
        });
    },
    showTask(taskId) {
      if (taskId == null) return;
      const task = this.tasks.find(t => t.id == taskId);
      if (task == null) return;
      task.show = true;
      // make sure it is in the list
      this.filter = "all";
      this.group = "";
      this.search = "";
      const index = this.filtered.findIndex(t => t.id === task.id);
      if (index >= this.limit) this.limit = index + 1;
    },
    removeTask(id) {
      this.tasks = this.tasks.filter(t => t.id !== id);
    },
    clearCompleted() {
      if (!confirm(this.$t("tasks.clearConfirm", { n: this.counts.done }))) return;
      this.clearing = true;
      Tasks.clearCompleted()
        .then(r => {
          this.$toastr.success(this.$t("tasks.cleared", { n: r.data.deleted }));
          this.updatePage();
        })
        .catch(error => this.axiosReqestError(this.$t("tasks.tasks"), (error.response && error.response.data.message) || String(error)))
        .finally(() => (this.clearing = false));
    }
  },
  sockets: {
    taskProgress(data) {
      const task = this.tasks.find(t => t.id === data.id);
      if (!task) {
        // a new task started somewhere: pick it up
        this.updatePage();
        return;
      }
      task.progress = data.progress;
      task.warnings = data.warnings;
      task.errors = data.errors;
      if (data.progress >= 100) task.completed = true;
    }
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.tasks-page {
  text-align: left;
}
.search-box {
  max-width: 300px;
}
.group-select {
  max-width: 200px;
}
.stat {
  border: 1px solid #e3e7ec;
  padding: 12px 14px;
  background: #fff;
  border-radius: 10px;
  transition: border-color 120ms, box-shadow 120ms;
}
.stat:hover {
  border-color: #adb5bd;
}
.stat.active {
  border-color: #2a78d6;
  box-shadow: 0 0 0 2px rgba(42, 120, 214, 0.2) !important;
}
.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  background: #eef1f5;
  color: #495057;
}
.stat.running .stat-icon {
  background: #e8f0fb;
  color: #2a78d6;
}
.stat.done .stat-icon {
  background: #e6f6ef;
  color: #1a9e6e;
}
.stat.problems .stat-icon {
  background: #fdecec;
  color: #d63a3a;
}
.stat-value {
  font-size: 1.35rem;
  font-weight: 600;
  line-height: 1.1;
}
.task-list {
  border-radius: 10px;
  overflow: hidden;
}
</style>
