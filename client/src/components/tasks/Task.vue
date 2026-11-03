<template>
  <div class="task" :class="[state, { open: showLogs, highlight }]" :id="'task-' + task.id">
    <div class="task-row d-flex align-items-center gap-3" role="button" :aria-expanded="showLogs" @click="showLogs = !showLogs">
      <div class="state-icon" :title="$t('tasks.state.' + state)">
        <i class="fa" :class="stateIcon" />
      </div>

      <div class="flex-grow-1 min-w-0">
        <div class="name text-truncate">{{ $taskName(task.name) }}</div>
        <div class="meta small text-muted">
          <span class="type-badge">{{ $tr('taskGroup', task.group) }}</span>
          <span>#{{ task.id }}</span>
          <span v-if="task.dataset_name"><i class="fa fa-database" /> {{ task.dataset_name }}</span>
          <span v-if="task.creator"><i class="fa fa-user-o" /> {{ task.creator }}</span>
          <span v-if="started"><i class="fa fa-clock-o" /> {{ started }}</span>
          <span v-if="duration">{{ completed ? $t('tasks.took', { t: duration }) : $t('tasks.runningFor', { t: duration }) }}</span>
        </div>
      </div>

      <div class="d-flex align-items-center gap-1 flex-shrink-0">
        <span v-if="errors > 0" class="badge text-bg-danger">{{ $t('task.errors', { n: errors }, errors) }}</span>
        <span v-if="warnings > 0" class="badge text-bg-warning">{{ $t('task.warnings', { n: warnings }, warnings) }}</span>
      </div>

      <div class="progress-col flex-shrink-0">
        <div class="d-flex justify-content-between small">
          <span class="text-muted">{{ completed ? $t('tasks.state.done') : $t('tasks.state.running') }}</span>
          <span class="fw-semibold">{{ Math.round(task.progress || 0) }}%</span>
        </div>
        <div class="progress">
          <div
            class="progress-bar"
            :class="{ 'bg-success': completed && !errors, 'bg-danger': errors > 0 && completed, 'progress-bar-striped progress-bar-animated': !completed }"
            :style="{ width: (task.progress || 0) + '%' }"
          />
        </div>
      </div>

      <i class="fa chevron text-muted" :class="showLogs ? 'fa-chevron-up' : 'fa-chevron-down'" />
    </div>

    <div v-if="showLogs" class="logs-panel">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn" :class="level === '' ? 'btn-dark' : 'btn-outline-secondary'" @click="level = ''">
            {{ $t('tasks.allLines', { n: logs.length }) }}
          </button>
          <button type="button" class="btn" :class="level === 'ERROR' ? 'btn-danger' : 'btn-outline-secondary'" :disabled="!errors" @click="level = 'ERROR'">
            {{ $t('task.errors', { n: errors }, errors) }}
          </button>
          <button type="button" class="btn" :class="level === 'WARNING' ? 'btn-warning' : 'btn-outline-secondary'" :disabled="!warnings" @click="level = 'WARNING'">
            {{ $t('task.warnings', { n: warnings }, warnings) }}
          </button>
        </div>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="copyLogs">
          <i class="fa fa-clipboard" /> {{ $t('tasks.copyLogs') }}
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="getLogs">
          <i class="fa fa-refresh" />
        </button>
        <button v-if="completed" type="button" class="btn btn-sm btn-outline-danger ms-auto" @click="deleteTask">
          <i class="fa fa-trash" /> {{ $t('task.delete') }}
        </button>
      </div>
      <div class="logs">
        <div v-if="!displayLogs.length" class="log text-muted">{{ $t('tasks.noLogs') }}</div>
        <div v-for="(line, index) in displayLogs" :key="index" class="log" :class="lineLevel(line)">
          <span class="ts">{{ parts(line).time }}</span>
          <span class="lvl">{{ parts(line).level }}</span>
          <span class="msg">{{ parts(line).text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Tasks from "@/models/tasks";

const pad = n => String(n).padStart(2, "0");
function toDate(value) {
  const raw = value && (value.$date ?? value);
  const d = raw != null ? new Date(raw) : null;
  return d && !isNaN(d) ? d : null;
}
function span(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${pad(s % 60)}s`;
  return `${Math.floor(m / 60)}h ${pad(m % 60)}m`;
}

export default {
  name: "Task",
  props: {
    task: { type: Object, required: true }
  },
  emits: ["deleted"],
  data() {
    return { logs: [], showLogs: false, highlight: false, level: "", now: Date.now(), timer: null };
  },
  computed: {
    warnings() {
      return this.task.warnings || 0;
    },
    errors() {
      return this.task.errors || 0;
    },
    completed() {
      return !!(this.task.completed || this.task.progress >= 100);
    },
    state() {
      if (!this.completed) return "running";
      if (this.task.failed || this.errors > 0) return "failed";
      if (this.warnings > 0) return "warning";
      return "done";
    },
    stateIcon() {
      return { running: "fa-spinner fa-spin", failed: "fa-times", warning: "fa-exclamation", done: "fa-check" }[this.state];
    },
    started() {
      const d = toDate(this.task.start_date);
      if (!d) return "";
      const today = new Date();
      const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
      return d.toDateString() === today.toDateString() ? time : `${d.getMonth() + 1}/${d.getDate()} ${time}`;
    },
    duration() {
      const start = toDate(this.task.start_date);
      if (!start) return "";
      const end = toDate(this.task.end_date) || (this.completed ? null : new Date(this.now));
      return end ? span(end - start) : "";
    },
    /** newest first */
    displayLogs() {
      const lines = this.level ? this.logs.filter(l => l.includes(`[${this.level}]`)) : this.logs;
      return lines.slice().reverse();
    }
  },
  watch: {
    showLogs(open) {
      if (open) this.getLogs();
    },
    completed() {
      if (this.showLogs) this.getLogs();
    }
  },
  methods: {
    getLogs() {
      Tasks.getLogs(this.task.id).then(response => {
        this.logs = response.data.logs || [];
      });
    },
    lineLevel(line) {
      if (line.includes("[ERROR]")) return "error";
      if (line.includes("[WARNING]")) return "warning";
      return "info";
    },
    /** "[dd-mm-YYYY HH:MM:SS] [LEVEL] text" */
    parts(line) {
      const m = /^\[([^\]]+)\]\s*\[([A-Z]+)\]\s*(.*)$/s.exec(line);
      if (!m) return { time: "", level: "", text: line };
      return { time: m[1].split(" ").pop(), level: m[2], text: m[3] };
    },
    copyLogs() {
      navigator.clipboard.writeText(this.logs.join("\n")).then(
        () => this.$toastr.success(this.$t("tasks.copied")),
        () => this.$toastr.error(this.$t("bulkUsers.copyFailed"))
      );
    },
    deleteTask() {
      Tasks.delete(this.task.id).finally(() => this.$emit("deleted", this.task.id));
    }
  },
  mounted() {
    this.timer = setInterval(() => {
      if (!this.completed) this.now = Date.now();
    }, 1000);
    if (this.task.show) {
      this.showLogs = true;
      setTimeout(() => {
        this.highlight = true;
        this.$el.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => (this.highlight = false), 1500);
      }, 200);
    }
  },
  beforeUnmount() {
    clearInterval(this.timer);
  }
};
</script>

<style scoped>
.task {
  border-bottom: 1px solid #eef0f3;
  transition: background-color 400ms;
}
.task:last-child {
  border-bottom: 0;
}
.task.highlight {
  background: #fff7d6;
}
.task-row {
  padding: 12px 16px;
  cursor: pointer;
}
.task-row:hover {
  background: #f8f9fb;
}
.task.open .task-row {
  background: #f4f7fb;
}
.min-w-0 {
  min-width: 0;
}
.state-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 0.9rem;
}
.running .state-icon {
  background: #e8f0fb;
  color: #2a78d6;
}
.done .state-icon {
  background: #e6f6ef;
  color: #1a9e6e;
}
.warning .state-icon {
  background: #fff4dc;
  color: #c47f00;
}
.failed .state-icon {
  background: #fdecec;
  color: #d63a3a;
}
.name {
  font-weight: 600;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 2px;
}
.type-badge {
  background: #eef1f5;
  color: #495057;
  border-radius: 4px;
  padding: 0 6px;
}
.progress-col {
  width: 160px;
}
.progress {
  height: 6px;
  border-radius: 999px;
}
.chevron {
  width: 14px;
}
.logs-panel {
  padding: 4px 16px 14px 66px;
  background: #f4f7fb;
}
.logs {
  background: #1f2430;
  border-radius: 8px;
  max-height: 320px;
  overflow-y: auto;
  padding: 8px 0;
  font-family: SFMono-Regular, Menlo, Consolas, "Courier New", monospace;
  font-size: 12.5px;
}
.log {
  display: flex;
  gap: 10px;
  padding: 1px 12px;
  color: #d8dee9;
  white-space: pre-wrap;
  word-break: break-word;
}
.log .ts {
  color: #7a8396;
  flex-shrink: 0;
}
.log .lvl {
  flex-shrink: 0;
  width: 58px;
  color: #8fbcbb;
}
.log.warning .lvl,
.log.warning .msg {
  color: #ebcb8b;
}
.log.error .lvl,
.log.error .msg {
  color: #ff8a8a;
}
@media (max-width: 767.98px) {
  .progress-col {
    width: 90px;
  }
  .logs-panel {
    padding-left: 16px;
  }
}
</style>
