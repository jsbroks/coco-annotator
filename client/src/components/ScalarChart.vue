<template>
  <div class="scalar-chart">
    <div class="head">
      <span class="title" :title="hint || title">{{ title }}</span>
      <span v-if="hint" class="hint text-muted">{{ hint }}</span>
    </div>
    <div ref="plot" class="plot">
      <svg
        ref="svg"
        :viewBox="`0 0 ${W} ${H}`"
        class="svg"
        role="img"
        :aria-label="title"
        @mousemove="onMove"
        @mouseleave="hover = null"
      >
        <g class="grid">
          <line v-for="t in yAxis.ticks" :key="'gy' + t" :x1="L" :x2="W - R" :y1="py(t)" :y2="py(t)" />
          <line v-for="t in xAxis.ticks" :key="'gx' + t" :x1="px(t)" :x2="px(t)" :y1="T" :y2="H - B" />
        </g>
        <g class="axis">
          <text v-for="t in yAxis.ticks" :key="'ty' + t" :x="L - 5" :y="py(t) + 3" text-anchor="end">{{ tick(t, yAxis.step) }}</text>
          <text v-for="t in xAxis.ticks" :key="'tx' + t" :x="px(t)" :y="H - 5" text-anchor="middle">{{ tick(t, xAxis.step) }}</text>
        </g>
        <g v-if="marker != null && marker <= xAxis.hi" class="marker">
          <line :x1="px(marker)" :x2="px(marker)" :y1="T" :y2="H - B" />
          <text :x="px(marker) + 3" :y="T + 9">★ {{ markerLabel }}</text>
        </g>
        <g v-for="s in drawn" :key="s.name">
          <!-- raw values, faint (TensorBoard) -->
          <polyline v-if="s.smoothed !== s.points" :points="s.rawPath" class="raw" :stroke="s.color" />
          <polyline :points="s.path" class="line" :stroke="s.color" :stroke-dasharray="s.dashed ? '5 3' : null" />
          <template v-if="s.dots">
            <circle v-for="(p, i) in s.points" :key="i" :cx="px(p[0])" :cy="py(p[1])" r="2.2" :fill="s.color" />
          </template>
        </g>
        <g v-if="hover">
          <line class="cursor" :x1="px(hover.x)" :x2="px(hover.x)" :y1="T" :y2="H - B" />
          <circle v-for="h in hover.items" :key="'h' + h.name" :cx="px(h.x)" :cy="py(h.smoothed)" r="3.5" :fill="h.color" stroke="#fff" />
        </g>
      </svg>
      <div v-if="hover" class="tip" :class="{ left: hover.right }" :style="{ left: (100 * px(hover.x)) / W + '%' }">
        <div class="tip-x">epoch {{ fmtX(hover.x) }}</div>
        <div v-for="h in hover.items" :key="'t' + h.name" class="tip-row">
          <span class="swatch" :style="{ background: h.color }" />
          <span class="tip-name">{{ h.name }}</span>
          <b>{{ fmt(h.smoothed) }}</b>
          <span v-if="h.raw !== h.smoothed" class="text-muted">({{ fmt(h.raw) }})</span>
        </div>
      </div>
    </div>
    <div v-if="series.length > 1" class="legend">
      <span v-for="s in drawn" :key="'l' + s.name" class="item">
        <span class="swatch" :class="{ dashed: s.dashed }" :style="{ background: s.color }" />{{ s.name }}
      </span>
    </div>
  </div>
</template>

<script>
import { smooth, niceTicks, fmtNumber, fmtTick } from "@/libs/scalars";

/**
 * One scalar over the epochs, like a TensorBoard card: each series is drawn
 * raw (faint) and smoothed; hovering shows every series' value there.
 * series: [{ name, color, points: [[x, y], ...], dots?, dashed? }]
 */
export default {
  name: "ScalarChart",
  props: {
    title: { type: String, required: true },
    hint: { type: String, default: "" },
    series: { type: Array, required: true },
    // 0..0.99
    smoothing: { type: Number, default: 0.6 },
    // the x range to show (all charts of a run share it)
    xMax: { type: Number, default: null },
    // an epoch to mark (the best one)
    marker: { type: Number, default: null },
    markerLabel: { type: String, default: "" }
  },
  data() {
    return { W: 420, H: 210, L: 46, R: 10, T: 10, B: 20, hover: null };
  },
  computed: {
    drawn() {
      return this.series
        .filter(s => s.points.length)
        .map(s => {
          // few points (one per epoch): smoothing would hide them
          const smoothed = s.points.length > 20 ? smooth(s.points, this.smoothing) : s.points;
          return {
            ...s,
            smoothed,
            path: this.path(smoothed),
            rawPath: smoothed !== s.points ? this.path(s.points) : ""
          };
        });
    },
    yAxis() {
      let lo = Infinity;
      let hi = -Infinity;
      this.series.forEach(s =>
        s.points.forEach(([, y]) => {
          if (Number.isFinite(y)) {
            lo = Math.min(lo, y);
            hi = Math.max(hi, y);
          }
        })
      );
      if (!Number.isFinite(lo)) return niceTicks(0, 1, 4);
      // a little room above and below; not below 0 for values that never are
      const pad = (hi - lo) * 0.05;
      let a = lo - pad;
      let b = hi + pad;
      if (lo >= 0) a = Math.max(0, a);
      if (b <= a) b = a === 0 ? 1 : a + Math.abs(a) * 0.1;
      return niceTicks(a, b, 4);
    },
    xAxis() {
      let hi = this.xMax || 0;
      this.series.forEach(s => s.points.forEach(([x]) => (hi = Math.max(hi, x))));
      hi = Math.max(1, hi);
      // whole epochs on the axis
      let t = niceTicks(0, hi, 5);
      if (t.step < 1) t = { ticks: Array.from({ length: Math.floor(hi) + 1 }, (_, i) => i), step: 1 };
      return { ticks: t.ticks.filter(v => v <= hi), step: t.step, lo: 0, hi };
    }
  },
  mounted() {
    // drawn at its real size: the text stays readable on a phone
    this.fit();
    if (typeof ResizeObserver !== "undefined") {
      this.observer = new ResizeObserver(() => this.fit());
      this.observer.observe(this.$refs.plot);
    }
  },
  beforeUnmount() {
    if (this.observer) this.observer.disconnect();
  },
  methods: {
    fit() {
      const width = this.$refs.plot && this.$refs.plot.clientWidth;
      if (!width) return;
      this.W = Math.round(width);
      this.H = Math.round(Math.min(260, Math.max(170, width * 0.5)));
    },
    px(x) {
      return this.L + ((x - this.xAxis.lo) / (this.xAxis.hi - this.xAxis.lo)) * (this.W - this.L - this.R);
    },
    py(y) {
      const { lo, hi } = this.yAxis;
      return this.T + (1 - (y - lo) / (hi - lo)) * (this.H - this.T - this.B);
    },
    path(points) {
      return points
        .filter(p => Number.isFinite(p[1]))
        .map(p => `${this.px(p[0]).toFixed(1)},${this.py(p[1]).toFixed(1)}`)
        .join(" ");
    },
    fmt(v) {
      return fmtNumber(v);
    },
    tick(v, step) {
      return fmtTick(v, step);
    },
    fmtX(x) {
      return Number.isInteger(x) ? x : x.toFixed(2);
    },
    onMove(e) {
      const rect = this.$refs.svg.getBoundingClientRect();
      const sx = ((e.clientX - rect.left) / rect.width) * this.W;
      const x = this.xAxis.lo + ((sx - this.L) / (this.W - this.L - this.R)) * (this.xAxis.hi - this.xAxis.lo);
      const items = [];
      let nearest = null;
      this.drawn.forEach(s => {
        // the point of this series closest to the mouse (sorted by x)
        const pts = s.points;
        let a = 0;
        let b = pts.length - 1;
        while (b - a > 1) {
          const m = (a + b) >> 1;
          if (pts[m][0] < x) a = m;
          else b = m;
        }
        const i = Math.abs(pts[a][0] - x) <= Math.abs(pts[b][0] - x) ? a : b;
        items.push({ name: s.name, color: s.color, x: pts[i][0], raw: pts[i][1], smoothed: s.smoothed[i][1] });
        if (nearest == null || Math.abs(pts[i][0] - x) < Math.abs(nearest - x)) nearest = pts[i][0];
      });
      this.hover = items.length ? { x: nearest, items, right: sx > this.W * 0.6 } : null;
    }
  }
};
</script>

<style scoped>
.scalar-chart {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 8px 10px 6px;
  background: #fff;
  height: 100%;
}
.head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}
.title {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  font-family: Menlo, Consolas, monospace;
}
.hint {
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.plot {
  position: relative;
}
.svg {
  width: 100%;
  height: auto;
  display: block;
}
.grid line {
  stroke: #f1f3f5;
}
.axis text {
  font-size: 10px;
  fill: #868e96;
  font-variant-numeric: tabular-nums;
}
.line {
  fill: none;
  stroke-width: 1.8;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.raw {
  fill: none;
  stroke-width: 1;
  opacity: 0.25;
}
.marker line {
  stroke: #e0a800;
  stroke-width: 1.2;
  stroke-dasharray: 4 3;
}
.marker text {
  font-size: 10px;
  fill: #b58900;
}
.cursor {
  stroke: #adb5bd;
  stroke-dasharray: 3 3;
}
.tip {
  position: absolute;
  top: 4px;
  transform: translateX(10px);
  background: rgba(33, 37, 41, 0.92);
  color: #fff;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 0.72rem;
  pointer-events: none;
  white-space: nowrap;
  z-index: 2;
}
.tip.left {
  transform: translateX(calc(-100% - 10px));
}
.tip-x {
  color: #ced4da;
}
.tip-row {
  display: flex;
  align-items: center;
  gap: 5px;
  font-variant-numeric: tabular-nums;
}
.tip .text-muted {
  color: #adb5bd !important;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  font-size: 0.72rem;
  color: #495057;
}
.swatch {
  display: inline-block;
  width: 12px;
  height: 3px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}
</style>
