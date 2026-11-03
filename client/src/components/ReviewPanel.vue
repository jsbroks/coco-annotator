<template>
  <div class="review-panel">
    <!-- overall progress -->
    <div class="card my-3 p-3 shadow-sm">
      <div class="d-flex align-items-center flex-wrap gap-2 border-bottom pb-2 mb-3">
        <h6 class="mb-0 me-auto">
          <b>{{ $t('review.progressTitle') }}</b>
          <small v-if="refreshedAt" class="text-muted fw-normal ms-2 updated">{{ updatedText }}</small>
        </h6>
        <button
          v-if="progress && progress.can_review"
          type="button"
          class="btn btn-sm btn-warning"
          :disabled="!progress.total.labeled"
          @click="openNext('review')"
        >
          <i class="fa fa-search" /> {{ $t('review.startReview', { n: progress.total.labeled }) }}
        </button>
        <RouterLink
          v-if="progress && progress.can_review"
          :to="`/review/${datasetId}`"
          class="btn btn-sm btn-outline-warning"
          :title="$t('quickReview.hint')"
        >
          <i class="fa fa-th" /> {{ $t('quickReview.title') }}
        </RouterLink>
        <button type="button" class="btn btn-sm btn-primary" :disabled="!myOpen" @click="openNext('work')">
          <i class="fa fa-pencil" /> {{ $t('review.startWork', { n: myOpen }) }}
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" :title="updatedText" @click="load()">
          <i class="fa fa-refresh" />
        </button>
      </div>

      <div v-if="!progress" class="text-muted small"><i class="fa fa-spinner fa-spin" /></div>
      <template v-else>
        <div class="progress-stacked" style="height: 22px">
          <div
            v-for="s in BAR_ORDER"
            :key="s"
            class="progress"
            role="progressbar"
            :style="{ width: share(progress.total[s], progress.images) + '%' }"
            :title="$t('review.status.' + s) + ': ' + progress.total[s]"
          >
            <div class="progress-bar" :class="barClass(s)">
              <template v-if="pct(progress.total[s]) >= 8">{{ progress.total[s] }}</template>
            </div>
          </div>
        </div>
        <div class="d-flex flex-wrap gap-3 small mt-2">
          <span v-for="s in BAR_ORDER" :key="s">
            <span class="badge" :class="statusClass(s)">{{ $t('review.status.' + s) }}</span>
            {{ progress.total[s] }}（{{ pct(progress.total[s]) }}%）
          </span>
          <span class="ms-auto text-muted">{{ $t('review.totalImages', { n: progress.images }) }}</span>
        </div>
      </template>
    </div>

    <!-- per member -->
    <div v-if="progress" class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2"><b>{{ $t('review.byMember') }}</b></h6>
      <div class="table-responsive">
        <table class="table table-sm align-middle mb-0 text-center">
          <thead>
            <tr>
              <th class="text-start">{{ $t('review.member') }}</th>
              <th>{{ $t('review.assigned') }}</th>
              <th v-for="s in STATUSES" :key="s">{{ $t('review.status.' + s) }}</th>
              <th style="width: 30%">{{ $t('review.approvedPct') }}</th>
              <th v-if="canAssign" />
            </tr>
          </thead>
          <tbody>
            <template v-for="row in memberRows" :key="row.username || '-'">
            <tr>
              <td class="text-start">
                <template v-if="row.username">
                  {{ row.username }}
                  <span v-if="progress.reviewers.includes(row.username)" class="badge text-bg-info ms-1">
                    {{ $t('review.reviewer') }}
                  </span>
                  <span v-if="row.username === progress.owner" class="badge text-bg-dark ms-1">{{ $t('review.owner') }}</span>
                </template>
                <span v-else class="text-muted">{{ $t('review.unassigned') }}</span>
              </td>
              <td>{{ row.assigned }}</td>
              <td v-for="s in STATUSES" :key="s">{{ row[s] || 0 }}</td>
              <td>
                <div class="progress" style="height: 8px" :title="rowPct(row) + '%'">
                  <div class="progress-bar bg-success" :style="{ width: rowPct(row) + '%' }" />
                </div>
              </td>
              <td v-if="canAssign" class="text-end">
                <button
                  v-if="row.username && row.assigned"
                  type="button"
                  class="btn btn-sm py-0"
                  :class="clearing === row.username ? 'btn-secondary' : 'btn-outline-secondary'"
                  :title="$t('review.clearFor', { name: row.username })"
                  @click="clearing = clearing === row.username ? null : row.username"
                >
                  <i class="fa fa-eraser" /> {{ $t('review.clearAssign') }}
                </button>
              </td>
            </tr>
            <!-- clearing one person's assignment -->
            <tr v-if="canAssign && clearing && clearing === row.username" class="clear-row">
              <td :colspan="STATUSES.length + 4" class="text-start">
                <div class="d-flex flex-wrap align-items-center gap-2 py-1">
                  <span class="small me-auto">{{ $t('review.clearHint', { name: row.username }) }}</span>
                  <button
                    type="button"
                    class="btn btn-sm btn-warning"
                    :disabled="busy || !notDone(row)"
                    @click="clearAssign(row, 'unlabeled')"
                  >
                    {{ $t('review.clearNotDone', { n: notDone(row) }) }}
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-danger" :disabled="busy" @click="clearAssign(row, 'all')">
                    {{ $t('review.clearAll', { n: row.assigned }) }}
                  </button>
                  <button type="button" class="btn btn-sm btn-link" @click="clearing = null">{{ $t('review.cancel') }}</button>
                </div>
              </td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- per folder (e.g. one per video) -->
    <div v-if="progress && folders && folders.length > 1" class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2"><b>{{ $t('review.byFolder') }}</b></h6>
      <div class="table-responsive">
        <table class="table table-sm align-middle mb-0 text-center">
          <thead>
            <tr>
              <th class="text-start">{{ $t('review.folder') }}</th>
              <th>{{ $t('review.folderImages') }}</th>
              <th class="text-start">{{ $t('review.folderNow') }}</th>
              <th v-for="s in STATUSES" :key="s">{{ $t('review.status.' + s) }}</th>
              <th style="width: 26%">{{ $t('review.folderProgress') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in folders" :key="f.folder">
              <td class="text-start text-truncate" style="max-width: 280px" :title="f.folder">
                <i class="fa fa-folder-o me-1" />{{ f.folder || $t('review.rootFolder') }}
              </td>
              <td>{{ f.images }}</td>
              <td class="text-start small">
                <span v-for="p in assigneeParts(f)" :key="p.who" class="me-2" :class="{ 'text-muted': !p.who }">{{ p.text }}</span>
              </td>
              <td v-for="s in STATUSES" :key="s">{{ f.status[s] || '' }}</td>
              <td>
                <div class="d-flex align-items-center gap-2">
                  <div class="progress-stacked flex-grow-1" style="height: 10px">
                    <div
                      v-for="s in BAR_ORDER"
                      :key="s"
                      class="progress"
                      :style="{ width: share(f.status[s], f.images) + '%' }"
                      :title="$t('review.status.' + s) + ': ' + (f.status[s] || 0)"
                    >
                      <div class="progress-bar" :class="barClass(s)" />
                    </div>
                  </div>
                  <small class="text-muted folder-pct" :title="$t('review.folderDoneHint')">
                    {{ folderPct(f, (f.status.labeled || 0) + (f.status.approved || 0)) }}%
                  </small>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- assign -->
    <div v-if="progress && (progress.can_assign ?? progress.can_review)" class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2 d-flex align-items-center flex-wrap gap-2">
        <b class="me-auto">{{ $t('review.assignTitle') }}</b>
        <span class="btn-group btn-group-sm" role="group">
          <button type="button" class="btn" :class="assignMode === 'even' ? 'btn-secondary' : 'btn-outline-secondary'" @click="setAssignMode('even')">
            <i class="fa fa-random" /> {{ $t('review.modeEven') }}
          </button>
          <button type="button" class="btn" :class="assignMode === 'folder' ? 'btn-secondary' : 'btn-outline-secondary'" @click="setAssignMode('folder')">
            <i class="fa fa-folder-o" /> {{ $t('review.modeFolder') }}
          </button>
        </span>
      </h6>
      <div class="small text-muted mb-2">{{ assignMode === 'folder' ? $t('review.folderHint') : $t('review.assignHint') }}</div>
      <div class="d-flex flex-wrap gap-3 mb-2">
        <div v-for="name in progress.members" :key="name" class="form-check">
          <input :id="'assign-' + name" v-model="assignTo" class="form-check-input" type="checkbox" :value="name" />
          <label class="form-check-label" :for="'assign-' + name">{{ name }}</label>
        </div>
      </div>
      <div class="d-flex flex-wrap align-items-center gap-2">
        <select v-model="scope" class="form-select form-select-sm" style="max-width: 280px">
          <option value="unassigned">{{ $t('review.scope.unassigned', { n: progress.unassigned ? sumRow(progress.unassigned) : 0 }) }}</option>
          <option value="unlabeled">{{ $t('review.scope.unlabeled', { n: progress.total.unlabeled + progress.total.rejected }) }}</option>
          <option value="all">{{ $t('review.scope.all', { n: progress.images }) }}</option>
        </select>
        <button v-if="assignMode === 'even'" type="button" class="btn btn-sm btn-primary" :disabled="!assignTo.length || busy" @click="assign">
          <i class="fa fa-random" /> {{ $t('review.assignEven', { n: assignTo.length }) }}
        </button>
        <template v-else>
          <button type="button" class="btn btn-sm btn-outline-primary" :disabled="!assignTo.length || !folders || busy" @click="autoFolders">
            <i class="fa fa-magic" /> {{ $t('review.folderAuto', { n: assignTo.length }) }}
          </button>
          <button type="button" class="btn btn-sm btn-primary" :disabled="!folderChanges || busy" @click="assignFolders">
            <i class="fa fa-check" /> {{ $t('review.folderApply', { n: folderChanges }) }}
          </button>
        </template>
        <button type="button" class="btn btn-sm btn-outline-danger ms-auto" :disabled="busy" @click="unassignAll">
          {{ $t('review.unassignAll') }}
        </button>
      </div>

      <!-- whole folders (one per video) to one person each -->
      <div v-if="assignMode === 'folder'" class="mt-3">
        <div v-if="!folders" class="text-muted small"><i class="fa fa-spinner fa-spin" /></div>
        <div v-else-if="folders.length < 2" class="text-muted small">{{ $t('review.noFolders') }}</div>
        <template v-else>
          <table class="table table-sm align-middle mb-2 folder-table">
            <thead>
              <tr>
                <th>{{ $t('review.folder') }}</th>
                <th class="text-end">{{ $t('review.folderImages') }}</th>
                <th>{{ $t('review.folderNow') }}</th>
                <th style="width: 200px">{{ $t('review.folderTo') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in folders" :key="f.folder" :class="{ 'text-muted': !inScope(f) }">
                <td class="text-truncate" style="max-width: 320px" :title="f.folder">
                  <i class="fa fa-folder-o me-1" />{{ f.folder || $t('review.rootFolder') }}
                </td>
                <td class="text-end">
                  {{ inScope(f) }}
                  <small v-if="inScope(f) !== f.images" class="text-muted">/ {{ f.images }}</small>
                </td>
                <td class="small">
                  <span v-for="p in assigneeParts(f)" :key="p.who" class="me-2" :class="{ 'text-muted': !p.who }">{{ p.text }}</span>
                </td>
                <td>
                  <select v-model="folderPlan[f.folder]" class="form-select form-select-sm" :disabled="!inScope(f)">
                    <option :value="undefined">{{ $t('review.folderKeep') }}</option>
                    <option v-for="name in progress.members" :key="name" :value="name">{{ name }}</option>
                    <option value="">{{ $t('review.folderClear') }}</option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="folderTotals.length" class="small">
            {{ $t('review.folderTotals') }}
            <span v-for="t in folderTotals" :key="t.name" class="badge text-bg-light border me-1">{{ t.name }} {{ t.n }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- reviewers -->
    <div v-if="progress && (progress.is_creator ?? progress.is_owner)" class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2"><b>{{ $t('review.reviewersTitle') }}</b></h6>
      <div class="small text-muted mb-2">{{ $t('review.reviewersHint') }}</div>
      <div class="d-flex flex-wrap gap-3 mb-2">
        <div v-for="name in progress.members.filter(n => n !== progress.owner)" :key="name" class="form-check">
          <input :id="'reviewer-' + name" v-model="reviewers" class="form-check-input" type="checkbox" :value="name" />
          <label class="form-check-label" :for="'reviewer-' + name">{{ name }}</label>
        </div>
        <span v-if="progress.members.length <= 1" class="small text-muted">{{ $t('review.noMembers') }}</span>
      </div>
      <div>
        <button type="button" class="btn btn-sm btn-outline-primary" :disabled="busy" @click="saveReviewers">
          {{ $t('review.saveReviewers') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import autoRefresh from "@/mixins/autoRefresh";
import { statusClass } from "@/components/annotator/ReviewBar.vue";

const STATUSES = ["unlabeled", "labeled", "approved", "rejected"];
// bars fill from the left: done first, not started last
const BAR_ORDER = ["approved", "labeled", "rejected", "unlabeled"];

export default {
  name: "ReviewPanel",
  props: {
    datasetId: { type: Number, required: true }
  },
  emits: ["changed"],
  // others annotate and review meanwhile: keep the numbers current
  mixins: [autoRefresh("load", 15000)],
  data() {
    return {
      STATUSES, BAR_ORDER, progress: null, clearing: null, assignTo: [], scope: "unassigned", reviewers: [], busy: false,
      assignMode: "even",
      folders: null,
      // folder -> username ("" unassigns, missing: leave as it is)
      folderPlan: {}
    };
  },
  computed: {
    updatedText() {
      return this.refreshedAt ? this.$t("review.updatedAt", { time: this.refreshedAt.toLocaleTimeString() }) : "";
    },
    canAssign() {
      return !!(this.progress && (this.progress.can_assign ?? this.progress.can_review));
    },
    memberRows() {
      if (!this.progress) return [];
      const byName = Object.fromEntries(this.progress.people.map(p => [p.username, p]));
      const rows = this.progress.members.map(name => {
        const counts = byName[name] || {};
        return { username: name, ...counts, assigned: this.sumRow(counts) };
      });
      // assignees who are no longer members
      this.progress.people.filter(p => !this.progress.members.includes(p.username))
        .forEach(p => rows.push({ ...p, assigned: this.sumRow(p) }));
      rows.push({ username: "", ...this.progress.unassigned, assigned: this.sumRow(this.progress.unassigned) });
      return rows;
    },
    /** folders with a person chosen (and images in scope) */
    folderChanges() {
      if (!this.folders) return 0;
      return this.folders.filter(f => this.folderPlan[f.folder] !== undefined && this.inScope(f)).length;
    },
    /** what each person gets with the current plan */
    folderTotals() {
      const totals = {};
      (this.folders || []).forEach(f => {
        const who = this.folderPlan[f.folder];
        if (who) totals[who] = (totals[who] || 0) + this.inScope(f);
      });
      return Object.entries(totals).map(([name, n]) => ({ name, n })).sort((a, b) => b.n - a.n);
    },
    /** my images that still need work */
    myOpen() {
      if (!this.progress) return 0;
      const mine = this.progress.people.find(p => p.username === this.progress.me) || {};
      return (mine.unlabeled || 0) + (mine.rejected || 0);
    }
  },
  watch: {
    datasetId: {
      immediate: true,
      handler(id) {
        if (id) this.load();
      }
    }
  },
  methods: {
    statusClass,
    barClass(s) {
      return { unlabeled: "bg-secondary", labeled: "bg-warning", approved: "bg-success", rejected: "bg-danger" }[s];
    },
    sumRow(row) {
      return STATUSES.reduce((n, s) => n + ((row && row[s]) || 0), 0);
    },
    /** exact share for bar widths: rounded ones may not add up to 100 */
    share(n, total) {
      return total ? (100 * (n || 0)) / total : 0;
    },
    pct(n) {
      return this.progress && this.progress.images ? Math.round((100 * n) / this.progress.images) : 0;
    },
    rowPct(row) {
      const total = this.sumRow(row);
      return total ? Math.round((100 * (row.approved || 0)) / total) : 0;
    },
    /** "test03(all)" for a whole folder, else "test01(21) test02(43) 未指派(5)" */
    assigneeParts(f) {
      const people = Object.entries(f.assignees || {}).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      if (people.length === 1 && !f.unassigned) return [{ who: people[0][0], text: `${people[0][0]}(all)` }];
      const parts = people.map(([who, n]) => ({ who, text: `${who}(${n})` }));
      if (f.unassigned) {
        parts.push({ who: "", text: f.unassigned === f.images ? this.$t("review.unassigned") : `${this.$t("review.unassigned")}(${f.unassigned})` });
      }
      return parts;
    },
    sameNames(a, b) {
      return [...(a || [])].sort().join("\n") === [...(b || [])].sort().join("\n");
    },
    folderPct(f, n) {
      return f.images ? Math.round((100 * (n || 0)) / f.images) : 0;
    },
    load() {
      // folders: progress per folder, and the "by folder" assignment
      axios.get(`/api/review/dataset/${this.datasetId}/folders`).then(r => (this.folders = r.data.folders)).catch(() => {});
      return axios.get(`/api/review/dataset/${this.datasetId}/progress`).then(r => {
        // reviewer ticks being changed (not saved yet) are kept
        const untouched = !this.progress || this.sameNames(this.reviewers, this.progress.reviewers);
        this.progress = r.data;
        this.refreshedAt = new Date();
        if (untouched) this.reviewers = [...r.data.reviewers];
        if (!this.assignTo.length) {
          // default: everybody except the owner
          this.assignTo = r.data.members.filter(n => n !== r.data.owner);
        }
      });
    },
    async assign() {
      if (!confirm(this.$t("review.assignConfirm", { n: this.assignTo.length }))) return;
      await this.post("assign", { usernames: this.assignTo, scope: this.scope }, r => {
        const parts = Object.entries(r.data.assigned).map(([k, v]) => `${k} ${v}`);
        this.$toastr.success(this.$t("review.assigned_done", { list: parts.join("、") }));
      });
    },
    setAssignMode(mode) {
      this.assignMode = mode;
      if (mode === "folder") this.folderPlan = {};
    },
    /** images of a folder that the chosen scope covers */
    inScope(f) {
      if (this.scope === "unassigned") return f.unassigned;
      if (this.scope === "unlabeled") return f.unlabeled;
      return f.images;
    },
    /** biggest folders first, each to whoever has the least so far: even without splitting */
    autoFolders() {
      const people = [...this.assignTo];
      if (!people.length || !this.folders) return;
      const load = Object.fromEntries(people.map(p => [p, 0]));
      const plan = {};
      [...this.folders]
        .filter(f => this.inScope(f) > 0)
        .sort((a, b) => this.inScope(b) - this.inScope(a) || a.folder.localeCompare(b.folder))
        .forEach(f => {
          const who = people.reduce((best, p) => (load[p] < load[best] ? p : best), people[0]);
          plan[f.folder] = who;
          load[who] += this.inScope(f);
        });
      this.folderPlan = plan;
    },
    async assignFolders() {
      const plan = {};
      this.folders.forEach(f => {
        if (this.folderPlan[f.folder] !== undefined && this.inScope(f)) plan[f.folder] = this.folderPlan[f.folder];
      });
      if (!Object.keys(plan).length) return;
      if (!confirm(this.$t("review.folderConfirm", { n: Object.keys(plan).length }))) return;
      await this.post("assign", { folders: plan, scope: this.scope }, r => {
        const parts = Object.entries(r.data.assigned).map(([k, v]) => `${k} ${v}`);
        if (r.data.unassigned) parts.push(`${this.$t("review.unassigned")} ${r.data.unassigned}`);
        this.$toastr.success(this.$t("review.assigned_done", { list: parts.join("、") }));
      });
      this.folderPlan = {};
    },
    /** images this person still has to do */
    notDone(row) {
      return (row.unlabeled || 0) + (row.rejected || 0);
    },
    async clearAssign(row, scope) {
      const n = scope === "all" ? row.assigned : this.notDone(row);
      if (!n) return;
      await this.post("assign", { usernames: [], from_user: row.username, scope }, r => {
        this.clearing = null;
        this.$toastr.success(this.$t("review.clearDone", { name: row.username, n: r.data.unassigned }));
      });
    },
    async unassignAll() {
      if (!confirm(this.$t("review.unassignConfirm"))) return;
      await this.post("assign", { usernames: [], scope: "all" }, () => this.$toastr.success(this.$t("review.unassigned_done")));
    },
    async saveReviewers() {
      await this.post("reviewers", { reviewers: this.reviewers }, () => this.$toastr.success(this.$t("review.reviewersSaved")));
    },
    async post(path, body, onDone) {
      this.busy = true;
      try {
        const r = await axios.post(`/api/review/dataset/${this.datasetId}/${path}`, body);
        onDone(r);
        await this.load();
        this.$emit("changed");
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    },
    async openNext(mode) {
      const r = await axios.get(`/api/review/dataset/${this.datasetId}/next`, { params: { mode } });
      if (r.data.id) {
        this.$router.push({ name: "annotate", params: { identifier: r.data.id } });
      } else {
        this.$toastr.info(this.$t(mode === "review" ? "review.nothingToReview" : "review.nothingToDo"));
      }
    }
  }
};
</script>

<style scoped>
/* each coloured part fills the whole bar (Bootstrap gives it 1rem) */
.progress-stacked > .progress {
  height: 100%;
}
</style>
