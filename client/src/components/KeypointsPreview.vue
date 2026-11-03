<template>
  <div class="kp-preview">
    <div class="pv-head">
      <span class="pv-title">{{ $t('keypointsPreview.title') }}</span>
      <span class="text-muted small">{{ $t('keypointsPreview.count', { points: nodes.length, edges: edges.length }) }}</span>
      <div class="ms-auto d-flex align-items-center gap-2">
        <button
          v-if="Object.keys(pinned).length"
          type="button"
          class="btn btn-link btn-sm p-0 pv-tool"
          :title="$t('keypointsPreview.resetLayout')"
          @click="pinned = {}"
        >
          <i class="fa fa-undo" />
        </button>
        <button
          type="button"
          class="btn btn-link btn-sm p-0 pv-tool"
          :class="{ on: showNames }"
          :title="$t('keypointsPreview.names')"
          @click="showNames = !showNames"
        >
          <i class="fa fa-font" />
        </button>
      </div>
    </div>

    <div class="pv-stage">
      <svg
        ref="svg"
        :viewBox="`0 0 ${W} ${H}`"
        class="pv-svg"
        @pointerdown.self="onBackground"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointerleave="onLeave"
      >
        <defs>
          <linearGradient
            v-for="e in drawnEdges"
            :id="uid + e.key"
            :key="'g' + e.key"
            gradientUnits="userSpaceOnUse"
            :x1="e.x1"
            :y1="e.y1"
            :x2="e.x2"
            :y2="e.y2"
          >
            <stop offset="0" :stop-color="e.c1" />
            <stop offset="1" :stop-color="e.c2" />
          </linearGradient>
        </defs>

        <!-- the line from the picked point to the mouse -->
        <line
          v-if="picked != null && cursor && pos[picked]"
          class="pv-rubber"
          :x1="pos[picked].x"
          :y1="pos[picked].y"
          :x2="cursor.x"
          :y2="cursor.y"
        />

        <line
          v-for="e in drawnEdges"
          :key="e.key"
          class="pv-edge"
          :class="{ dim: focus != null && !e.touches(focus), hot: focus != null && e.touches(focus) }"
          :x1="e.x1"
          :y1="e.y1"
          :x2="e.x2"
          :y2="e.y2"
          :stroke="`url(#${uid + e.key})`"
        />

        <g
          v-for="n in nodes"
          :key="'n' + n.index"
          class="pv-node"
          :class="{
            dim: focus != null && focus !== n.index && !neighbours(focus).has(n.index),
            hot: focus === n.index,
            picked: picked === n.index,
            lonely: !degree[n.index]
          }"
          :transform="`translate(${pos[n.index].x} ${pos[n.index].y})`"
          @pointerdown.stop="onDown($event, n.index)"
          @pointerenter="$emit('hover', n.index)"
          @pointerleave="$emit('hover', null)"
        >
          <circle class="halo" :r="radius[n.index] + 4.5" />
          <circle class="dot" :r="radius[n.index]" :fill="n.color" />
          <text
            v-if="(showNames && !crowded.has(n.index)) || focus === n.index || picked === n.index"
            class="pv-label"
            :x="pos[n.index].x >= W / 2 ? radius[n.index] + 4 : -radius[n.index] - 4"
            y="3.5"
            :text-anchor="pos[n.index].x >= W / 2 ? 'start' : 'end'"
          >{{ n.label }}</text>
        </g>

        <text v-if="!nodes.length" class="pv-empty" :x="W / 2" :y="H / 2" text-anchor="middle">
          {{ $t('keypointsPreview.empty') }}
        </text>
      </svg>
    </div>

    <div class="pv-help">
      <template v-if="picked != null && nodes.find(n => n.index === picked)">
        <i class="fa fa-link" />
        {{ $t('keypointsPreview.picking', { name: nodes.find(n => n.index === picked).label }) }}
      </template>
      <template v-else>{{ $t('keypointsPreview.help') }}</template>
    </div>
  </div>
</template>

<script>
// where a person's keypoints usually are (facing the viewer, so "left" is on
// the right), in a 1 x 1.15 box: these are placed there, the rest around them
const BODY = {
  head: [0.5, -0.052],
  head_top: [0.5, -0.052],
  nose: [0.5, 0.11],
  left_eye_inner: [0.547, 0.063],
  left_eye: [0.588, 0.056],
  left_eye_outer: [0.628, 0.063],
  right_eye_inner: [0.453, 0.063],
  right_eye: [0.412, 0.056],
  right_eye_outer: [0.372, 0.063],
  left_ear: [0.675, 0.09],
  right_ear: [0.325, 0.09],
  mouth: [0.5, 0.171],
  left_mouth: [0.547, 0.171],
  right_mouth: [0.453, 0.171],
  chin: [0.5, 0.218],
  neck: [0.5, 0.215],
  left_shoulder: [0.68, 0.27],
  right_shoulder: [0.32, 0.27],
  thorax: [0.5, 0.27],
  chest: [0.5, 0.33],
  spine: [0.5, 0.42],
  left_elbow: [0.76, 0.43],
  right_elbow: [0.24, 0.43],
  left_wrist: [0.81, 0.58],
  right_wrist: [0.19, 0.58],
  left_hand: [0.83, 0.63],
  right_hand: [0.17, 0.63],
  left_thumb: [0.765, 0.645],
  right_thumb: [0.235, 0.645],
  left_index: [0.82, 0.685],
  right_index: [0.18, 0.685],
  left_pinky: [0.88, 0.65],
  right_pinky: [0.12, 0.65],
  pelvis: [0.5, 0.56],
  mid_hip: [0.5, 0.56],
  left_hip: [0.59, 0.56],
  right_hip: [0.41, 0.56],
  left_knee: [0.61, 0.77],
  right_knee: [0.39, 0.77],
  left_ankle: [0.62, 0.97],
  right_ankle: [0.38, 0.97],
  left_heel: [0.6, 1.02],
  right_heel: [0.4, 1.02],
  left_foot: [0.67, 1.03],
  right_foot: [0.33, 1.03],
  left_foot_index: [0.68, 1.04],
  right_foot_index: [0.32, 1.04],
  left_big_toe: [0.68, 1.04],
  right_big_toe: [0.32, 1.04],
  left_small_toe: [0.71, 1.03],
  right_small_toe: [0.29, 1.03]
};

/** one spelling for a body part: leftEye, left-eye, L_eye, eye_left -> left_eye */
function bodyKey(label) {
  let k = String(label || "")
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase()
    .replace(/[\s.-]+/g, "_");
  k = k.replace(/^l_/, "left_").replace(/^r_/, "right_");
  k = k.replace(/^(.*)_left$/, "left_$1").replace(/^(.*)_right$/, "right_$1");
  return k;
}

let instances = 0;

/**
 * How the keypoints connect, drawn: person keypoints where they are on a
 * body, the others laid out by their connections. Clicking two points
 * connects them (or takes the connection away); points can be dragged.
 */
export default {
  name: "KeypointsPreview",
  props: {
    // [{ label, color, edges: [label] }] as KeypointsDefinition keeps them
    keypoints: { type: Array, required: true },
    // a keypoint pointed at in the list
    highlight: { type: Number, default: null }
  },
  emits: ["hover", "toggle"],
  data() {
    return {
      W: 300,
      H: 340,
      pinned: {},
      picked: null,
      cursor: null,
      drag: null,
      showNames: true,
      uid: "kpv" + ++instances + "-"
    };
  },
  computed: {
    nodes() {
      return this.keypoints
        .map((kp, index) => ({ index, label: kp.label, color: kp.color || "#888" }))
        .filter(n => n.label);
    },
    byLabel() {
      const m = {};
      this.nodes.forEach(n => (m[n.label] = n.index));
      return m;
    },
    edges() {
      const seen = new Set();
      const out = [];
      this.keypoints.forEach((kp, a) => {
        if (!kp.label) return;
        kp.edges.forEach(label => {
          const b = this.byLabel[label];
          if (b == null || b === a) return;
          const key = a < b ? a + "_" + b : b + "_" + a;
          if (seen.has(key)) return;
          seen.add(key);
          out.push({ a: Math.min(a, b), b: Math.max(a, b), key });
        });
      });
      return out;
    },
    degree() {
      const d = {};
      this.edges.forEach(e => {
        d[e.a] = (d[e.a] || 0) + 1;
        d[e.b] = (d[e.b] || 0) + 1;
      });
      return d;
    },
    // positions in the layout's own space
    world() {
      return this.layout();
    },
    // fitted into the picture (kept still while a point is dragged)
    view() {
      if (this.drag && this.drag.view) return this.drag.view;
      return this.fit(this.world);
    },
    pos() {
      const out = {};
      const v = this.view;
      Object.keys(this.world).forEach(i => {
        const p = this.world[i];
        out[i] = { x: v.ox + p.x * v.s, y: v.oy + p.y * v.s };
      });
      return out;
    },
    drawnEdges() {
      const color = i => (this.keypoints[i] && this.keypoints[i].color) || "#888";
      return this.edges
        .filter(e => this.pos[e.a] && this.pos[e.b])
        .map(e => ({
          key: e.key,
          x1: this.pos[e.a].x,
          y1: this.pos[e.a].y,
          x2: this.pos[e.b].x,
          y2: this.pos[e.b].y,
          c1: color(e.a),
          c2: color(e.b),
          touches: i => e.a === i || e.b === i
        }));
    },
    // smaller dots where points are close together (a face, a hand)
    radius() {
      const out = {};
      const list = this.nodes.map(n => n.index);
      list.forEach(a => {
        let d = Infinity;
        list.forEach(b => {
          if (a !== b && this.pos[a] && this.pos[b]) d = Math.min(d, Math.hypot(this.pos[a].x - this.pos[b].x, this.pos[a].y - this.pos[b].y));
        });
        out[a] = Math.max(3.5, Math.min(6.5, d * 0.42));
      });
      return out;
    },
    // points too close to name without the names running into each other
    // (a face): named when pointed at
    crowded() {
      const out = new Set();
      // each name's box, on the side of its point away from the middle
      const box = n => {
        const p = this.pos[n.index];
        if (!p) return null;
        const w = n.label.length * 5.8;
        const x0 = p.x >= this.W / 2 ? p.x + 10 : p.x - 10 - w;
        return { x0, x1: x0 + w, y: p.y, i: n.index };
      };
      const boxes = this.nodes.map(box).filter(Boolean);
      boxes.forEach((p, k) =>
        boxes.slice(k + 1).forEach(q => {
          if (Math.abs(p.y - q.y) < 12 && p.x0 < q.x1 && q.x0 < p.x1) {
            out.add(p.i);
            out.add(q.i);
          }
        })
      );
      return out;
    },
    focus() {
      return this.picked != null ? this.picked : this.highlight;
    }
  },
  watch: {
    keypoints() {
      if (this.picked != null && !(this.keypoints[this.picked] && this.keypoints[this.picked].label)) this.picked = null;
    }
  },
  mounted() {
    this.onKey = e => {
      if (e.key === "Escape" && this.picked != null) {
        this.picked = null;
        e.stopPropagation();
      }
    };
    window.addEventListener("keydown", this.onKey, true);
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.onKey, true);
  },
  methods: {
    neighbours(i) {
      const s = new Set();
      this.edges.forEach(e => {
        if (e.a === i) s.add(e.b);
        if (e.b === i) s.add(e.a);
      });
      return s;
    },
    /** body keypoints where they belong; the rest pushed apart and pulled
     *  along their connections (a few hundred small steps, the same result
     *  every time) */
    layout() {
      const nodes = this.nodes;
      const n = nodes.length;
      const out = {};
      if (!n) return out;
      const fixed = {};
      let onBody = 0;
      nodes.forEach(nd => {
        const k = this.pinned[nd.label];
        const b = BODY[bodyKey(nd.label)];
        if (k) fixed[nd.index] = { x: k.x, y: k.y };
        else if (b) {
          fixed[nd.index] = { x: b[0], y: b[1] };
          onBody++;
        }
      });
      // too few body parts to be a body: lay everything out freely
      if (onBody && onBody < Math.min(3, n)) {
        nodes.forEach(nd => {
          if (!this.pinned[nd.label]) delete fixed[nd.index];
        });
      }
      const ideal = Object.keys(fixed).length ? 0.12 : 1 / Math.sqrt(n + 1);
      // start on a circle (free points next to a fixed neighbour when they have one)
      const p = {};
      nodes.forEach((nd, k) => {
        if (fixed[nd.index]) {
          p[nd.index] = { ...fixed[nd.index] };
          return;
        }
        const a = (2 * Math.PI * k) / n - Math.PI / 2;
        p[nd.index] = { x: 0.5 + 0.4 * Math.cos(a), y: 0.55 + 0.4 * Math.sin(a) };
      });
      nodes.forEach((nd, k) => {
        if (fixed[nd.index]) return;
        const anchor = [...this.neighbours(nd.index)].find(j => fixed[j]);
        if (anchor != null) {
          const a = (2 * Math.PI * k) / n;
          p[nd.index] = { x: fixed[anchor].x + ideal * Math.cos(a), y: fixed[anchor].y + ideal * Math.sin(a) };
        }
      });
      const free = nodes.filter(nd => !fixed[nd.index]).map(nd => nd.index);
      if (free.length) {
        const all = nodes.map(nd => nd.index);
        let t = 0.08;
        for (let it = 0; it < 300; it++) {
          const f = {};
          free.forEach(i => (f[i] = { x: 0, y: 0 }));
          free.forEach(i => {
            all.forEach(j => {
              if (i === j) return;
              let dx = p[i].x - p[j].x;
              let dy = p[i].y - p[j].y;
              let d2 = dx * dx + dy * dy;
              if (d2 < 1e-6) {
                dx = 0.01 * ((i % 3) - 1 || 1);
                dy = 0.01;
                d2 = 2e-4;
              }
              const d = Math.sqrt(d2);
              const r = (ideal * ideal) / d;
              f[i].x += (dx / d) * r;
              f[i].y += (dy / d) * r;
            });
            // a little pull to the middle keeps loose points in view
            f[i].x += (0.5 - p[i].x) * 0.05;
            f[i].y += (0.55 - p[i].y) * 0.05;
          });
          this.edges.forEach(({ a, b }) => {
            const dx = p[b].x - p[a].x;
            const dy = p[b].y - p[a].y;
            const d = Math.sqrt(dx * dx + dy * dy) || 1e-3;
            const s = (d * d) / ideal;
            if (f[a]) {
              f[a].x += (dx / d) * s;
              f[a].y += (dy / d) * s;
            }
            if (f[b]) {
              f[b].x -= (dx / d) * s;
              f[b].y -= (dy / d) * s;
            }
          });
          free.forEach(i => {
            const m = Math.sqrt(f[i].x * f[i].x + f[i].y * f[i].y) || 1;
            const step = Math.min(m, t);
            p[i].x += (f[i].x / m) * step;
            p[i].y += (f[i].y / m) * step;
          });
          t *= 0.985;
        }
      }
      nodes.forEach(nd => (out[nd.index] = p[nd.index]));
      return out;
    },
    fit(world) {
      const pts = Object.values(world);
      const pad = 26;
      if (!pts.length) return { s: 1, ox: 0, oy: 0 };
      let x0 = Infinity;
      let y0 = Infinity;
      let x1 = -Infinity;
      let y1 = -Infinity;
      pts.forEach(q => {
        x0 = Math.min(x0, q.x);
        y0 = Math.min(y0, q.y);
        x1 = Math.max(x1, q.x);
        y1 = Math.max(y1, q.y);
      });
      // not bigger than a whole body would be
      const w = Math.max(x1 - x0, 0.35);
      const h = Math.max(y1 - y0, 0.35);
      const s = Math.min((this.W - 2 * pad - 60) / w, (this.H - 2 * pad) / h);
      return { s, ox: this.W / 2 - ((x0 + x1) / 2) * s, oy: this.H / 2 - ((y0 + y1) / 2) * s };
    },
    point(e) {
      const r = this.$refs.svg.getBoundingClientRect();
      return { x: ((e.clientX - r.left) / r.width) * this.W, y: ((e.clientY - r.top) / r.height) * this.H };
    },
    onDown(e, index) {
      const at = this.point(e);
      this.drag = { index, start: at, moved: false, view: null };
      if (e.target.setPointerCapture) {
        try {
          this.$refs.svg.setPointerCapture(e.pointerId);
        } catch {
          // not every browser lets an svg capture
        }
      }
    },
    onMove(e) {
      const at = this.point(e);
      this.cursor = at;
      const d = this.drag;
      if (!d) return;
      if (!d.moved && Math.hypot(at.x - d.start.x, at.y - d.start.y) < 4) return;
      if (!d.moved) {
        d.moved = true;
        d.view = this.fit(this.world);
      }
      const v = d.view;
      const label = this.keypoints[d.index] && this.keypoints[d.index].label;
      if (!label) return;
      this.pinned = {
        ...this.pinned,
        [label]: { x: (at.x - v.ox) / v.s, y: (at.y - v.oy) / v.s }
      };
    },
    onUp() {
      const d = this.drag;
      this.drag = null;
      if (!d || d.moved) return;
      // a click: pick the first point, then connect it with the next
      if (this.picked == null) this.picked = d.index;
      else if (this.picked === d.index) this.picked = null;
      else {
        this.$emit("toggle", this.picked, d.index);
        // and carry on from there (a chain of clicks draws a limb)
        this.picked = d.index;
      }
    },
    onLeave() {
      this.cursor = null;
      if (this.drag && !this.drag.moved) this.drag = null;
    },
    onBackground() {
      this.picked = null;
    }
  }
};
</script>

<style scoped>
.kp-preview {
  border: 1px solid #e9ecef;
  border-radius: 10px;
  background: #fff;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
}
.pv-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pv-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.pv-tool {
  color: #adb5bd;
  text-decoration: none;
}
.pv-tool:hover,
.pv-tool.on {
  color: #495057;
}
.pv-stage {
  margin-top: 4px;
  border-radius: 8px;
  background-color: #f8f9fb;
  background-image: radial-gradient(#dee2e6 1px, transparent 1px);
  background-size: 16px 16px;
}
.pv-svg {
  width: 100%;
  height: auto;
  /* the whole picture in view next to a long list */
  max-height: calc(var(--vh, 100vh) - 330px);
  min-height: 220px;
  display: block;
  touch-action: none;
  user-select: none;
}
.pv-edge {
  stroke-width: 3.5;
  stroke-linecap: round;
  opacity: 0.85;
  transition: opacity 0.15s, stroke-width 0.15s;
}
.pv-edge.dim {
  opacity: 0.15;
}
.pv-edge.hot {
  stroke-width: 5;
  opacity: 1;
}
.pv-rubber {
  stroke: #0d6efd;
  stroke-width: 2;
  stroke-dasharray: 5 4;
  pointer-events: none;
}
.pv-node {
  cursor: pointer;
  transition: opacity 0.15s;
}
.pv-node .halo {
  fill: transparent;
}
.pv-node .dot {
  stroke: #fff;
  stroke-width: 2;
  filter: drop-shadow(0 1px 1.5px rgba(0, 0, 0, 0.3));
}
.pv-node.lonely .dot {
  stroke: #adb5bd;
  stroke-dasharray: 2 2;
}
.pv-node:hover .halo,
.pv-node.hot .halo {
  fill: rgba(13, 110, 253, 0.15);
}
.pv-node.picked .halo {
  fill: rgba(13, 110, 253, 0.25);
  stroke: #0d6efd;
  stroke-width: 1.5;
}
.pv-node.dim {
  opacity: 0.3;
}
.pv-label {
  font-size: 10.5px;
  fill: #343a40;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 3px;
  pointer-events: none;
}
.pv-node.hot .pv-label,
.pv-node.picked .pv-label {
  font-weight: 700;
}
.pv-empty {
  font-size: 12px;
  fill: #adb5bd;
}
.pv-help {
  margin-top: 6px;
  font-size: 0.75rem;
  color: #868e96;
  min-height: 1.2em;
}
.pv-help .fa {
  color: #0d6efd;
}
</style>
