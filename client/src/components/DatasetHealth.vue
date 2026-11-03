<template>
  <div class="health viz-root">
    <div class="d-flex align-items-center my-3">
      <h5 class="mb-0 me-auto">
        {{ $t('health.title') }}
        <small v-if="refreshedAt" class="text-muted fw-normal fs-6 ms-2">{{ $t('review.updatedAt', { time: refreshedAt.toLocaleTimeString() }) }}</small>
      </h5>
      <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="loading" @click="load()">
        <i class="fa fa-refresh" :class="{ 'fa-spin': loading }" /> {{ $t('health.refresh') }}
      </button>
    </div>

    <div v-if="!data" class="text-muted"><i class="fa fa-spinner fa-spin" /></div>
    <template v-else>
      <!-- headline numbers -->
      <div class="row g-2 mb-3">
        <div v-for="tile in tiles" :key="tile.label" class="col-6 col-md">
          <div class="stat-tile">
            <div class="stat-value">{{ tile.value }}</div>
            <div class="stat-label">{{ tile.label }}</div>
            <div v-if="tile.sub" class="stat-sub">{{ tile.sub }}</div>
          </div>
        </div>
      </div>

      <!-- problems -->
      <div class="card p-3 mb-3 shadow-sm">
        <h6 class="mb-2"><b>{{ $t('health.issuesTitle') }}</b></h6>
        <div v-if="!data.issues.length" class="text-success">
          <i class="fa fa-check-circle" /> {{ $t('health.noIssues') }}
        </div>
        <ul v-else class="list-unstyled mb-0">
          <li v-for="issue in data.issues" :key="issue.code" class="issue" :class="issue.level">
            <i class="fa" :class="issue.level === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'" />
            <span class="ms-1">{{ issueText(issue) }}</span>
            <span v-if="issue.examples && issue.examples.length" class="examples">
              {{ $t('health.examples') }}
              <router-link
                v-for="ex in issue.examples"
                :key="issue.code + ex.image_id"
                :to="{ name: 'annotate', params: { identifier: ex.image_id } }"
                class="me-2"
              >{{ ex.file_name }}</router-link>
            </span>
          </li>
        </ul>
      </div>

      <div class="row g-3">
        <!-- class balance -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.classBalance') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.classBalanceHint') }}</div>
            <div v-if="!data.classes.length" class="text-muted small">{{ $t('health.noData') }}</div>
            <div v-if="data.classes.length" class="hbar-list">
            <div v-for="row in data.classes" :key="row.id" class="hbar-row" :title="classTitle(row)">
              <span class="hbar-label">
                <span class="swatch" :style="{ backgroundColor: row.color || '#adb5bd' }" />
                {{ row.name }}
              </span>
              <span class="hbar-track">
                <span v-if="row.annotations" class="hbar" :style="{ width: pctOf(row.annotations, maxClass) + '%' }" />
              </span>
              <span class="hbar-value">{{ row.annotations }}</span>
              <small class="hbar-extra text-secondary">
                {{ $t('health.imagesN', { n: row.images }) }}<template v-if="row.classified"> · {{ $t('health.classifiedN', { n: row.classified }) }}</template>
              </small>
            </div>
            </div>
          </div>
        </div>

        <!-- who annotated how much (and what came from models / imports) -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.byMember') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('dataset.perUserHint') }}</div>
            <div v-if="!people.length" class="text-muted small">{{ $t('health.noData') }}</div>
            <div v-else class="member-head">
              <span />
              <span class="text-end">{{ $t('dataset.annotations') }}</span>
              <span class="text-end">{{ $t('dataset.images') }}</span>
            </div>
            <div v-for="row in people" :key="row.key" class="member-row" :class="{ source: row.source }">
              <span class="member-name text-truncate" :title="row.title || row.name">
                <i v-if="row.icon" class="fa" :class="row.icon" />
                {{ row.name }}
                <span v-if="row.by" class="small text-secondary fw-normal">{{ row.by }}</span>
              </span>
              <span class="member-bar">
                <span class="hbar-track">
                  <span v-if="row.annotations" class="hbar" :style="{ width: pctOf(row.annotations, maxPerson) + '%' }" />
                </span>
                <span class="num">{{ row.annotations }}</span>
              </span>
              <span class="num">{{ row.images }}</span>
            </div>
          </div>
        </div>

        <!-- how long each person worked on the dataset's images -->
        <div class="col-12">
          <div class="card p-3 shadow-sm">
            <h6><b>{{ $t('health.memberTime') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.memberTimeHint') }}</div>
            <div v-if="!timeRows.length" class="text-muted small">{{ $t('health.noData') }}</div>
            <div v-else class="table-responsive">
              <table class="table table-sm align-middle mb-0 time-table">
                <thead>
                  <tr>
                    <th>{{ $t('review.member') }}</th>
                    <th class="text-end">{{ $t('health.timeTotal') }}</th>
                    <th style="width: 30%" />
                    <th class="text-end">{{ $t('health.timeRecent') }}</th>
                    <th class="text-end">{{ $t('health.timeImages') }}</th>
                    <th class="text-end">{{ $t('health.timePerImage') }}</th>
                    <th class="text-end">{{ $t('health.timeLast') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in timeRows" :key="row.name" :class="{ 'text-muted': !row.seconds }">
                    <td class="text-truncate" style="max-width: 220px">{{ row.name }}</td>
                    <td class="text-end num">{{ row.seconds ? duration(row.seconds) : '—' }}</td>
                    <td>
                      <span class="hbar-track d-block">
                        <span v-if="row.seconds" class="hbar" :style="{ width: (100 * row.seconds / maxTime) + '%' }" />
                      </span>
                    </td>
                    <td class="text-end num">{{ row.recent_seconds ? duration(row.recent_seconds) : '—' }}</td>
                    <td class="text-end num">{{ row.images || '—' }}</td>
                    <td class="text-end num">{{ row.images ? duration(row.seconds / row.images) : '—' }}</td>
                    <td class="text-end small" :title="row.last ? new Date(row.last).toLocaleString() : ''">
                      {{ row.last ? agoText(row.last) : '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- objects per image -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.objectsPerImage') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.objectsPerImageHint', { avg: data.totals.per_image_avg }) }}</div>
            <div class="histogram">
              <div v-for="b in data.objects_per_image" :key="b.label" class="col-bar" :title="$t('health.imagesWithObjects', { n: b.n, label: b.label })">
                <span class="col-value">{{ b.n || '' }}</span>
                <span class="col-fill" :style="{ height: pctOf(b.n, maxOf(data.objects_per_image)) + '%' }" />
                <span class="col-label">{{ b.label }}</span>
              </div>
            </div>
            <div class="axis-title">{{ $t('health.objectsAxis') }}</div>
          </div>
        </div>

        <!-- box sizes -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.boxSizes') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.boxSizesHint') }}</div>
            <div class="row g-2 mb-3">
              <div v-for="s in ['small', 'medium', 'large']" :key="s" class="col-4">
                <div class="stat-tile compact">
                  <div class="stat-value">{{ pctOf(data.box_sizes[s], totalBoxes) }}%</div>
                  <div class="stat-label">{{ $t('health.size.' + s) }}</div>
                  <div class="stat-sub">{{ $t('health.boxesN', { n: data.box_sizes[s] }) }}</div>
                </div>
              </div>
            </div>
            <div class="small fw-semibold mb-1">{{ $t('health.relativeSize') }}</div>
            <div class="histogram short">
              <div v-for="b in data.relative_sizes" :key="b.label" class="col-bar" :title="$t('health.boxesInBucket', { n: b.n, label: b.label })">
                <span class="col-value">{{ b.n || '' }}</span>
                <span class="col-fill" :style="{ height: pctOf(b.n, maxOf(data.relative_sizes)) + '%' }" />
                <span class="col-label">{{ b.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- aspect ratio -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.aspectRatio') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.aspectRatioHint') }}</div>
            <div class="histogram">
              <div v-for="b in data.aspect_ratios" :key="b.label" class="col-bar" :title="$t('health.boxesInBucket', { n: b.n, label: b.label })">
                <span class="col-value">{{ b.n || '' }}</span>
                <span class="col-fill" :style="{ height: pctOf(b.n, maxOf(data.aspect_ratios)) + '%' }" />
                <span class="col-label">{{ b.label }}</span>
              </div>
            </div>
            <div class="axis-title">{{ $t('health.aspectAxis') }}</div>
          </div>
        </div>

        <!-- heatmap -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.heatmap') }}</b></h6>
            <div class="small text-secondary mb-2">{{ $t('health.heatmapHint') }}</div>
            <div class="heatmap" :style="{ aspectRatio: imageAspect, maxWidth: heatmapMaxWidth }">
              <template v-for="(row, y) in data.heatmap" :key="'r' + y">
                <span
                  v-for="(n, x) in row"
                  :key="x + '-' + y"
                  class="cell"
                  :style="{ backgroundColor: heatColor(n) }"
                  :title="$t('health.heatCell', { n })"
                />
              </template>
            </div>
            <div class="d-flex align-items-center gap-2 small text-secondary mt-2">
              <span>0</span>
              <span class="ramp" />
              <span>{{ maxHeat }}</span>
              <span class="ms-2">{{ $t('health.heatLegend') }}</span>
            </div>
          </div>
        </div>

        <!-- image sizes -->
        <div class="col-lg-6">
          <div class="card p-3 h-100 shadow-sm">
            <h6><b>{{ $t('health.imageSizes') }}</b></h6>
            <div class="row g-2 mb-3">
              <div v-for="k in ['min', 'median', 'max']" :key="k" class="col-4">
                <div class="stat-tile compact">
                  <div class="stat-value small-value">{{ data.image_size[k][0] }}×{{ data.image_size[k][1] }}</div>
                  <div class="stat-label">{{ $t('health.sizeStat.' + k) }}</div>
                </div>
              </div>
            </div>
            <table class="table table-sm mb-0">
              <thead>
                <tr>
                  <th>{{ $t('health.resolution') }}</th>
                  <th class="text-end">{{ $t('health.imageCount') }}</th>
                  <th style="width: 45%" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in data.resolutions" :key="r.width + 'x' + r.height">
                  <td>{{ r.width }} × {{ r.height }}</td>
                  <td class="text-end">{{ r.n }}</td>
                  <td>
                    <span class="hbar-track d-block">
                      <span class="hbar" :style="{ width: pctOf(r.n, data.totals.images) + '%' }" />
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import axios from "axios";
import autoRefresh from "@/mixins/autoRefresh";

// sequential blue ramp (light -> dark) for the heatmap
const RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
  "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];

export default {
  name: "DatasetHealth",
  // the numbers follow what others annotate (heavier: once a minute)
  mixins: [autoRefresh("load", 60000)],
  props: {
    datasetId: { type: Number, required: true }
  },
  data() {
    return { data: null, stats: null, loading: false };
  },
  computed: {
    tiles() {
      const t = this.data.totals;
      const pct = t.images ? Math.round((100 * t.annotated_images) / t.images) : 0;
      return [
        { label: this.$t("health.tile.images"), value: t.images },
        { label: this.$t("health.tile.annotatedImages"), value: t.annotated_images, sub: `${pct}%` },
        { label: this.$t("health.tile.annotations"), value: t.annotations },
        { label: this.$t("health.tile.perImage"), value: t.per_image_avg },
        { label: this.$t("health.tile.categories"), value: t.categories },
        ...(this.stats ? [
          { label: this.$t("health.tile.members"), value: this.stats.total.Users },
          {
            label: this.$t("health.tile.time"),
            value: this.duration(this.stats.total["Time Annotating (s)"]),
            sub: t.images && this.stats.total["Time Annotating (s)"] ? this.$t("health.perImageTime", { t: this.duration((this.stats.average["Time (ms) per Image"] || 0) / 1000) }) : ""
          }
        ] : [])
      ];
    },
    /** members by annotations, then what models and imports added */
    people() {
      if (!this.stats) return [];
      const users = Object.entries(this.stats.users || {})
        .map(([name, v]) => ({ key: "u" + name, name, annotations: v.annotations || 0, images: v.images || 0 }))
        .sort((a, b) => b.annotations - a.annotations || a.name.localeCompare(b.name));
      const sources = (this.stats.sources || []).map((src, i) => ({
        key: "s" + i,
        source: true,
        icon: src.kind === "model" ? "fa-magic" : "fa-upload",
        name: src.kind === "model"
          ? this.$t("dataset.modelSource", { name: src.name || this.$t("dataset.unknownModel") })
          : this.$t("dataset.importSource"),
        by: src.by && src.by.length ? this.$t("dataset.ranBy", { names: src.by.join("、") }) : "",
        annotations: src.annotations || 0,
        images: src.images || 0
      }));
      return [...users, ...sources];
    },
    /** time per member (members without any time too), most first */
    timeRows() {
      if (!this.stats) return [];
      const time = this.stats.time || {};
      const names = new Set([...Object.keys(this.stats.users || {}), ...Object.keys(time)]);
      return [...names]
        .map(name => ({ name, seconds: 0, recent_seconds: 0, images: 0, last: null, ...(time[name] || {}) }))
        .sort((a, b) => b.seconds - a.seconds || a.name.localeCompare(b.name));
    },
    maxTime() {
      return Math.max(1, ...this.timeRows.map(r => r.seconds));
    },
    maxPerson() {
      return Math.max(1, ...this.people.map(p => p.annotations));
    },
    maxClass() {
      return Math.max(1, ...this.data.classes.map(c => c.annotations));
    },
    totalBoxes() {
      const s = this.data.box_sizes;
      return (s.small || 0) + (s.medium || 0) + (s.large || 0);
    },
    maxHeat() {
      return Math.max(0, ...this.data.heatmap.flat());
    },
    /** keeps the heatmap at most 300 px tall while keeping the image shape */
    heatmapMaxWidth() {
      const [w, h] = this.data.image_size.median;
      return w && h ? `${Math.round((300 * w) / h)}px` : "300px";
    },
    imageAspect() {
      const [w, h] = this.data.image_size.median;
      return w && h ? `${w} / ${h}` : "1 / 1";
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
    load({ background = false } = {}) {
      // a background refresh does not spin the button
      if (!background) this.loading = true;
      return Promise.all([
        axios.get(`/api/dataset/${this.datasetId}/health`).then(r => (this.data = r.data)),
        // members, time spent: the counts of the former statistics page
        axios.get(`/api/dataset/${this.datasetId}/stats`).then(r => (this.stats = r.data)).catch(() => {})
      ]).then(() => (this.refreshedAt = new Date())).finally(() => (this.loading = false));
    },
    /** seconds -> "2 小時 5 分" / "4 分 10 秒" / "12 秒" */
    duration(seconds) {
      const s = Math.round(seconds || 0);
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
      if (h) return this.$t("health.hm", { h, m });
      if (m) return this.$t("health.ms", { m, s: sec });
      return this.$t("health.sec", { s: sec });
    },
    /** "5 分鐘前" */
    agoText(iso) {
      const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
      const units = [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60], ["second", 1]];
      const [unit, size] = units.find(([, size]) => secs >= size) || ["second", 1];
      const n = Math.floor(secs / size);
      return this.$t("health.ago", { ago: this.$t(`time.${unit}`, { n }, n) });
    },
    pctOf(n, total) {
      return total ? Math.round((100 * (n || 0)) / total) : 0;
    },
    maxOf(buckets) {
      return Math.max(1, ...buckets.map(b => b.n));
    },
    heatColor(n) {
      if (!n) return "var(--heat-zero)";
      const i = Math.min(RAMP.length - 1, Math.floor((Math.sqrt(n) / Math.sqrt(this.maxHeat || 1)) * (RAMP.length - 1)));
      return RAMP[i];
    },
    classTitle(row) {
      return this.$t("health.classTitle", { name: row.name, n: row.annotations, images: row.images });
    },
    issueText(issue) {
      const params = { ...issue };
      if (issue.names) params.names = issue.names.join("、");
      return this.$t("health.issue." + issue.code, params);
    }
  }
};
</script>

<style scoped>
.member-head,
.member-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr) 64px;
  gap: 10px;
  align-items: center;
}
.member-head {
  font-size: 0.75rem;
  color: var(--bs-secondary-color, #6c757d);
  margin-bottom: 4px;
}
.member-row {
  padding: 3px 0;
  font-size: 0.85rem;
}
.member-row.source {
  border-top: 1px dashed var(--bs-border-color, #dee2e6);
}
.member-row.source ~ .member-row.source {
  border-top: none;
}
.member-name {
  font-weight: 600;
}
.member-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.member-bar .hbar-track {
  flex: 1;
}
.num {
  font-variant-numeric: tabular-nums;
  text-align: right;
  min-width: 40px;
}
.viz-root {
  --bar: #2a78d6;
  --track: #eef1f5;
  --heat-zero: #f1f3f5;
  --text-secondary: #52514e;
}
.stat-tile {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 10px 12px;
  height: 100%;
}
.stat-tile.compact {
  padding: 8px 10px;
  text-align: center;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.2;
  color: #0b0b0b;
}
.stat-value.small-value {
  font-size: 1rem;
}
.stat-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.stat-sub {
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.issue {
  padding: 4px 0;
  border-bottom: 1px solid #f1f3f5;
}
.issue.warning .fa {
  color: #b35c00;
}
.issue.info .fa {
  color: #2a78d6;
}
.examples {
  display: block;
  margin-left: 1.3rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}
/* one grid for all rows, so every bar starts and ends at the same place */
.hbar-list {
  display: grid;
  grid-template-columns: minmax(80px, 30%) 1fr auto auto;
  column-gap: 8px;
}
.hbar-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: subgrid;
  align-items: center;
  font-size: 0.85rem;
  padding: 3px 0;
}
.hbar-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 4px;
}
.hbar-track {
  background: var(--track);
  border-radius: 4px;
  height: 12px;
  overflow: hidden;
}
.hbar {
  display: block;
  height: 100%;
  background: var(--bar);
  border-radius: 0 4px 4px 0;
  min-width: 2px;
}
.hbar-value {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.hbar-extra {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.time-table .num {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.time-table .hbar-track {
  height: 10px;
}
.histogram {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 160px;
  border-bottom: 1px solid #ced4da;
  padding-bottom: 0;
}
.histogram.short {
  height: 110px;
}
.col-bar {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: stretch;
  position: relative;
}
.col-fill {
  display: block;
  background: var(--bar);
  border-radius: 4px 4px 0 0;
  min-height: 0;
}
.col-value {
  font-size: 0.7rem;
  text-align: center;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.col-label {
  position: absolute;
  bottom: -18px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.axis-title {
  margin-top: 22px;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.histogram.short + * {
  margin-top: 22px;
}
.heatmap {
  display: grid;
  grid-template-columns: repeat(20, 1fr);
  gap: 1px;
  width: 100%;
  margin: 0 auto;
  background: #fff;
}
.cell {
  display: block;
}
.ramp {
  display: inline-block;
  width: 120px;
  height: 10px;
  border-radius: 2px;
  background: linear-gradient(to right, #cde2fb, #3987e5, #0d366b);
}
</style>
