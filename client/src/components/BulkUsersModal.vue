<template>
  <div class="modal fade" tabindex="-1" role="dialog" id="bulkUsers">
    <div class="modal-dialog modal-xl modal-dialog-scrollable" role="document">
      <div class="modal-content text-start">
        <div class="modal-header">
          <div>
            <h5 class="modal-title"><i class="fa fa-users" /> {{ $t('bulkUsers.title') }}</h5>
            <div v-if="!result" class="small text-muted">{{ $t('bulkUsers.tableHint') }}</div>
          </div>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>

        <div class="modal-body">
          <!-- ============ entering ============ -->
          <template v-if="!result">
            <div class="default-pw d-flex flex-wrap align-items-center gap-2 mb-3">
              <label class="fw-semibold small mb-0" for="bulkUsersDefaultPw">
                <i class="fa fa-key" /> {{ $t('bulkUsers.defaultPassword') }}
              </label>
              <input
                id="bulkUsersDefaultPw"
                v-model="defaultPassword"
                class="form-control form-control-sm mono pw-input"
                :placeholder="$t('bulkUsers.defaultPasswordPlaceholder')"
                autocomplete="off"
                spellcheck="false"
              />
              <span class="small text-muted">
                {{ defaultPassword.trim() ? $t('bulkUsers.defaultPasswordOn') : $t('bulkUsers.defaultPasswordOff') }}
              </span>
            </div>
            <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
              <span class="chip ok"><i class="fa fa-check" /> {{ $t('bulkUsers.countOk', { n: counts.ok }) }}</span>
              <span v-if="counts.exists" class="chip exists"><i class="fa fa-user" /> {{ $t('bulkUsers.countExists', { n: counts.exists }) }}</span>
              <span v-if="counts.bad" class="chip bad"><i class="fa fa-exclamation-triangle" /> {{ $t('bulkUsers.countBad', { n: counts.bad }) }}</span>
              <div class="ms-auto d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-sm" @click="$refs.csv.click()">
                  <i class="fa fa-file-text-o" /> {{ $t('bulkUsers.loadCsv') }}
                </button>
                <input ref="csv" type="file" accept=".csv,.txt,text/csv,text/plain" class="d-none" @change="loadCsv" />
                <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="filledRows === 0" @click="clearRows">
                  <i class="fa fa-eraser" /> {{ $t('bulkUsers.clear') }}
                </button>
              </div>
            </div>

            <div class="sheet">
              <table class="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th class="num">#</th>
                    <th>{{ $t('bulkUsers.colId') }} <span class="text-danger">*</span></th>
                    <th>{{ $t('bulkUsers.colName') }}</th>
                    <th>{{ $t('bulkUsers.colPassword') }}</th>
                    <th class="status-col">{{ $t('bulkUsers.colStatus') }}</th>
                    <th class="del"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in rows" :key="row.key" :class="'row-' + statusOf(i).kind">
                    <td class="num">{{ i + 1 }}</td>
                    <td v-for="field in FIELDS" :key="field">
                      <input
                        :ref="el => setCell(i, field, el)"
                        v-model="row[field]"
                        class="cell"
                        :class="{ mono: field !== 'name' }"
                        :placeholder="cellPlaceholder(i, field)"
                        :maxlength="field === 'username' ? 9 : 40"
                        autocomplete="off"
                        spellcheck="false"
                        @input="ensureTrailingRow"
                        @paste="onPaste($event, i, field)"
                        @keydown="onKey($event, i, field)"
                      />
                    </td>
                    <td class="status-col">
                      <span v-if="statusOf(i).kind !== 'empty'" class="status" :class="statusOf(i).kind">
                        <i class="fa" :class="statusOf(i).icon" /> {{ statusOf(i).text }}
                      </span>
                    </td>
                    <td class="del">
                      <button
                        v-if="!isEmpty(row)"
                        type="button"
                        class="btn btn-sm btn-link text-muted p-0"
                        :title="$t('bulkUsers.removeRow')"
                        @click="removeRow(i)"
                      >
                        <i class="fa fa-times" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="form-text">{{ $t('bulkUsers.listHint') }}</div>

            <div class="row g-3 mt-1">
              <div class="col-md-6">
                <label class="form-label small fw-semibold mb-1" for="bulkUsersRole">{{ $t('roles.role') }}</label>
                <select id="bulkUsersRole" v-model="role" class="form-select form-select-sm">
                  <option v-for="r in roles" :key="r.key" :value="r.key">{{ roleName(r) }}</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold mb-1" for="bulkUsersDataset">{{ $t('bulkUsers.dataset') }}</label>
                <select id="bulkUsersDataset" v-model="datasetId" class="form-select form-select-sm">
                  <option :value="null">{{ $t('bulkUsers.noDataset') }}</option>
                  <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
              </div>
            </div>
          </template>

          <!-- ============ done ============ -->
          <template v-else>
            <div class="d-flex flex-wrap gap-2 mb-2">
              <span class="chip ok"><i class="fa fa-check" /> {{ $t('bulkUsers.countCreated', { n: result.created.length }) }}</span>
              <span v-if="result.existing.length" class="chip exists"><i class="fa fa-user" /> {{ $t('bulkUsers.countExists', { n: result.existing.length }) }}</span>
            </div>
            <div v-if="result.created.length" class="alert alert-warning py-2 small d-flex align-items-center gap-2">
              <i class="fa fa-exclamation-circle" /> {{ $t('bulkUsers.saveNow') }}
            </div>
            <div class="sheet">
              <table class="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th class="num">#</th>
                    <th>{{ $t('bulkUsers.colId') }}</th>
                    <th>{{ $t('bulkUsers.colName') }}</th>
                    <th>{{ $t('adminPanel.password') }}</th>
                    <th class="status-col">{{ $t('bulkUsers.colStatus') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(u, i) in result.created" :key="u.username">
                    <td class="num">{{ i + 1 }}</td>
                    <td class="mono">{{ u.username }}</td>
                    <td>{{ u.name }}</td>
                    <td class="mono fw-semibold">{{ u.password }}</td>
                    <td class="status-col"><span class="status ok"><i class="fa fa-check" /> {{ $t('bulkUsers.created') }}</span></td>
                  </tr>
                  <tr v-for="(name, i) in result.existing" :key="'e' + name" class="text-muted">
                    <td class="num">{{ result.created.length + i + 1 }}</td>
                    <td class="mono">{{ name }}</td>
                    <td colspan="2"></td>
                    <td class="status-col"><span class="status exists"><i class="fa fa-user" /> {{ $t('bulkUsers.alreadyExists') }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>

        <div class="modal-footer">
          <template v-if="!result">
            <button type="button" class="btn btn-primary" :disabled="!counts.ok || running" @click="submit">
              <i class="fa" :class="running ? 'fa-spinner fa-spin' : 'fa-user-plus'" />
              {{ $t('bulkUsers.create', { n: counts.ok }) }}
            </button>
          </template>
          <template v-else>
            <button v-if="result.created.length" type="button" class="btn btn-outline-secondary" @click="copyResult">
              <i class="fa fa-clipboard" /> {{ $t('bulkUsers.copy') }}
            </button>
            <button v-if="result.created.length" type="button" class="btn btn-success" @click="download">
              <i class="fa fa-download" /> {{ $t('bulkUsers.download') }}
            </button>
          </template>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t('adminPanel.close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { showModal } from "@/libs/modal";

const STUDENT_ID = /^[A-Za-z][0-9]{8}$/;
const FIELDS = ["username", "name", "password"];
const START_ROWS = 8;
let nextKey = 1;
const blank = () => ({ key: nextKey++, username: "", name: "", password: "" });

/** One line of pasted / CSV text: id, name, password (tab, comma, semicolon or spaces) */
function splitLine(line) {
  const raw = line.trim();
  if (!raw) return null;
  return raw.includes("\t") ? raw.split("\t").map(s => s.trim()) : raw.split(/\s*[,;，]\s*|\s+/);
}

export default {
  name: "BulkUsersModal",
  emits: ["created"],
  data() {
    return {
      FIELDS,
      rows: Array.from({ length: START_ROWS }, blank),
      cells: {},
      existing: new Set(),
      roles: [],
      role: "user",
      defaultPassword: "",
      datasetId: null,
      datasets: [],
      result: null,
      running: false
    };
  },
  computed: {
    statuses() {
      const seen = new Set();
      return this.rows.map(row => {
        if (this.isEmpty(row)) return { kind: "empty" };
        const id = row.username.trim().toUpperCase();
        if (!id) return { kind: "bad", icon: "fa-exclamation-triangle", text: this.$t("bulkUsers.needId") };
        if (!STUDENT_ID.test(id)) return { kind: "bad", icon: "fa-exclamation-triangle", text: this.$t("bulkUsers.badId") };
        if (seen.has(id)) return { kind: "bad", icon: "fa-clone", text: this.$t("bulkUsers.duplicate") };
        seen.add(id);
        if (this.existing.has(id)) return { kind: "exists", icon: "fa-user", text: this.$t("bulkUsers.alreadyExists") };
        const text = row.password.trim() ? this.$t("bulkUsers.ready")
          : this.defaultPassword.trim() ? this.$t("bulkUsers.readyDefault") : this.$t("bulkUsers.readyAuto");
        return { kind: "ok", icon: "fa-check", text };
      });
    },
    counts() {
      const c = { ok: 0, exists: 0, bad: 0 };
      this.statuses.forEach(s => { if (s.kind in c) c[s.kind]++; });
      return c;
    },
    filledRows() {
      return this.rows.filter(r => !this.isEmpty(r)).length;
    }
  },
  methods: {
    open() {
      this.rows = Array.from({ length: START_ROWS }, blank);
      this.result = null;
      this.datasetId = null;
      this.role = "user";
      this.defaultPassword = "";
      showModal("#bulkUsers");
      axios.get("/api/dataset/").then(r => {
        this.datasets = (r.data || []).sort((a, b) => a.name.localeCompare(b.name));
      });
      axios.get("/api/admin/roles").then(r => {
        this.roles = (r.data.roles || []).filter(x => x.key !== "admin" || this.$store.getters["user/isAdmin"]);
      }).catch(() => (this.roles = [{ key: "user", builtin: true }]));
      // accounts that already exist are shown as such (and skipped)
      axios.get("/api/admin/users", { params: { limit: 5000 } }).then(r => {
        this.existing = new Set((r.data.users || []).map(u => String(u.username).toUpperCase()));
      }).catch(() => {});
      this.$nextTick(() => this.focus(0, "username"));
    },
    roleName(r) {
      if (r.key === "admin" || r.key === "user") return this.$t("roles.builtin." + r.key);
      return r.name || r.key;
    },
    /** first row shows examples; empty password cells show what they will get */
    cellPlaceholder(i, field) {
      if (field === "password") {
        if (this.defaultPassword.trim()) return this.isEmpty(this.rows[i]) && i > 0 ? "" : this.defaultPassword.trim();
        return i === 0 ? this.$t("bulkUsers.placeholder.password") : "";
      }
      return i === 0 ? this.$t("bulkUsers.placeholder." + field) : "";
    },
    statusOf(i) {
      return this.statuses[i] || { kind: "empty" };
    },
    isEmpty(row) {
      return !row.username.trim() && !row.name.trim() && !row.password.trim();
    },
    setCell(i, field, el) {
      if (el) this.cells[`${i}:${field}`] = el;
    },
    focus(i, field) {
      const el = this.cells[`${i}:${field}`];
      if (el) {
        el.focus();
        el.select();
      }
    },
    /** keep a few empty rows at the bottom to type into */
    ensureTrailingRow() {
      let empty = 0;
      for (let i = this.rows.length - 1; i >= 0 && this.isEmpty(this.rows[i]); i--) empty++;
      for (; empty < 2; empty++) this.rows.push(blank());
    },
    removeRow(i) {
      this.rows.splice(i, 1);
      if (this.rows.length < START_ROWS) this.rows.push(blank());
      this.ensureTrailingRow();
    },
    clearRows() {
      this.rows = Array.from({ length: START_ROWS }, blank);
    },
    /** Rows of text (Excel copy, CSV) into the table from row ``start`` on */
    fill(text, start = 0, field = "username") {
      const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).map(splitLine).filter(Boolean);
      // a header line such as "學號,姓名" is skipped
      if (lines.length && !STUDENT_ID.test(lines[0][0] || "") && /學號|帳號|id|user/i.test(lines[0].join(" "))) lines.shift();
      const offset = FIELDS.indexOf(field);
      lines.forEach((parts, n) => {
        const i = start + n;
        while (this.rows.length <= i) this.rows.push(blank());
        parts.slice(0, FIELDS.length - offset).forEach((value, k) => {
          this.rows[i][FIELDS[offset + k]] = value;
        });
      });
      this.ensureTrailingRow();
      return lines.length;
    },
    onPaste(event, i, field) {
      const text = (event.clipboardData || window.clipboardData).getData("text");
      // a single value pastes normally; rows / columns fill the table
      if (!/[\t\r\n]/.test(text.trim()) && !(field === "username" && /[,;，]/.test(text))) return;
      event.preventDefault();
      const n = this.fill(text, i, field);
      this.$nextTick(() => this.focus(Math.min(i + n, this.rows.length - 1), "username"));
    },
    onKey(event, i, field) {
      const col = FIELDS.indexOf(field);
      if (event.key === "Enter" || (event.key === "ArrowDown" && !event.shiftKey)) {
        event.preventDefault();
        if (i + 1 >= this.rows.length) this.rows.push(blank());
        this.$nextTick(() => this.focus(i + 1, event.key === "Enter" ? "username" : field));
      } else if (event.key === "ArrowUp" && i > 0) {
        event.preventDefault();
        this.focus(i - 1, field);
      } else if (event.key === "Tab" && !event.shiftKey && col === FIELDS.length - 1) {
        event.preventDefault();
        if (i + 1 >= this.rows.length) this.rows.push(blank());
        this.$nextTick(() => this.focus(i + 1, "username"));
      }
    },
    loadCsv(event) {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        this.rows = [];
        this.fill(String(reader.result), 0);
        while (this.rows.length < START_ROWS) this.rows.push(blank());
      };
      reader.readAsText(file, "utf-8");
    },
    submit() {
      const users = this.rows
        .filter((row, i) => this.statusOf(i).kind === "ok")
        .map(row => ({ username: row.username.trim().toUpperCase(), name: row.name.trim(), password: row.password.trim() || this.defaultPassword.trim() }));
      this.running = true;
      axios
        .post("/api/admin/users/bulk", { users, datasetId: this.datasetId, role: this.role })
        .then(r => {
          this.result = r.data;
          this.$emit("created");
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(data.message || String(error), this.$t("bulkUsers.title"));
        })
        .finally(() => (this.running = false));
    },
    resultRows() {
      return [["username", "name", "password"], ...this.result.created.map(u => [u.username, u.name, u.password])];
    },
    copyResult() {
      const text = this.resultRows().map(r => r.join("\t")).join("\n");
      navigator.clipboard.writeText(text).then(
        () => this.$toastr.success(this.$t("bulkUsers.copied")),
        () => this.$toastr.error(this.$t("bulkUsers.copyFailed"))
      );
    },
    download() {
      const csv = this.resultRows().map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
      // BOM so Excel opens Chinese names correctly
      const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `accounts-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    }
  }
};
</script>

<style scoped>
.sheet {
  border: 1px solid #dee2e6;
  border-radius: 6px;
  max-height: 52vh;
  overflow: auto;
}
.sheet thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f1f3f5;
  font-size: 0.8rem;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
  white-space: nowrap;
}
.sheet td,
.sheet th {
  padding: 0;
  border-right: 1px solid #f1f3f5;
}
.sheet th {
  padding: 6px 8px;
}
.sheet td.num,
.sheet th.num {
  width: 40px;
  text-align: center;
  color: #adb5bd;
  font-size: 0.75rem;
  background: #fafbfc;
}
.sheet td.del,
.sheet th.del {
  width: 32px;
  text-align: center;
}
.status-col {
  width: 170px;
}
td.status-col {
  padding: 0 8px !important;
}
.cell {
  width: 100%;
  border: 0;
  padding: 6px 8px;
  background: transparent;
  outline: none;
  font-size: 0.9rem;
}
.cell:focus {
  background: #fff;
  box-shadow: inset 0 0 0 2px #2a78d6;
}
.mono {
  font-family: SFMono-Regular, Menlo, Consolas, monospace;
  letter-spacing: 0.02em;
}
td.mono {
  padding: 6px 8px;
}
.sheet tbody td:not(.num):not(.del):not(.status-col):not(:has(input)) {
  padding: 6px 8px;
}
.row-bad {
  background: #fff5f5;
}
.row-exists {
  background: #f8f9fa;
}
.row-exists .cell {
  color: #868e96;
}
.status {
  font-size: 0.78rem;
  white-space: nowrap;
}
.status.ok {
  color: #1a9e6e;
}
.status.bad {
  color: #d63a3a;
}
.status.exists {
  color: #868e96;
}
.default-pw {
  background: #f8f9fb;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 8px 12px;
}
.pw-input {
  max-width: 220px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
}
.chip.ok {
  background: #e6f6ef;
  color: #137a55;
}
.chip.exists {
  background: #f1f3f5;
  color: #495057;
}
.chip.bad {
  background: #fdecec;
  color: #b42323;
}
</style>
