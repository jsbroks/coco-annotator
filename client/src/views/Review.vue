<template>
  <div class="quick-review">
    <div style="padding-top: 55px" />
    <div class="qr-bar d-flex flex-wrap align-items-center gap-2">
      <RouterLink :to="`/dataset/${datasetId}`" class="btn btn-sm btn-outline-light" :title="$t('quickReview.back')">
        <i class="fa fa-arrow-left" />
      </RouterLink>
      <div class="me-2">
        <div class="fw-semibold">{{ $t('quickReview.title') }}</div>
        <div class="small text-white-50">{{ datasetName }}</div>
      </div>

      <div class="btn-group btn-group-sm" role="group" :aria-label="$t('quickReview.layout')">
        <button
          v-for="n in GRIDS"
          :key="n"
          type="button"
          class="btn"
          :class="grid === n ? 'btn-light' : 'btn-outline-light'"
          :title="n === 1 ? $t('quickReview.single') : $t('quickReview.gridN', { n: n * n })"
          @click="setGrid(n)"
        >
          <i v-if="n === 1" class="fa fa-square-o" />
          <span v-else>{{ n }}×{{ n }}</span>
        </button>
      </div>

      <select v-model="status" class="form-select form-select-sm w-auto" :aria-label="$t('quickReview.show')">
        <option value="labeled">{{ $t('review.status.labeled') }}</option>
        <option value="rejected">{{ $t('review.status.rejected') }}</option>
        <option value="approved">{{ $t('review.status.approved') }}</option>
        <option value="all">{{ $t('review.all') }}</option>
      </select>
      <select v-model="order" class="form-select form-select-sm w-auto" :aria-label="$t('quickReview.order')">
        <option value="file_name">{{ $t('quickReview.byFileName') }}</option>
        <option value="submitted">{{ $t('quickReview.bySubmitted') }}</option>
      </select>
      <select v-model="labeler" class="form-select form-select-sm w-auto" :aria-label="$t('quickReview.by')">
        <option value="">{{ $t('quickReview.anyone') }}</option>
        <option v-for="u in labelers" :key="u" :value="u">{{ u }}</option>
      </select>

      <div class="form-check form-switch m-0 text-white-50 small" :title="$t('quickReview.syncHint')">
        <input id="qrSync" v-model="syncZoom" type="checkbox" class="form-check-input" role="switch" />
        <label class="form-check-label" for="qrSync">{{ $t('quickReview.syncZoom') }}</label>
      </div>
      <div class="form-check form-switch m-0 text-white-50 small">
        <input id="qrShow" v-model="showShapes" type="checkbox" class="form-check-input" role="switch" />
        <label class="form-check-label" for="qrShow">{{ $t('quickReview.showShapes') }} (H)</label>
      </div>

      <!-- categories of this page: hover lights one up everywhere, click keeps it -->
      <div v-if="showShapes && pageCats.length" class="cat-bar" :class="{ solo: soloCat != null }">
      <div
        ref="strip"
        class="cat-strip"
        :class="{ 'fade-left': stripFade.left, 'fade-right': stripFade.right }"
        @wheel="onStripWheel"
        @scroll="updateStripFade"
      >
        <button
          v-for="c in pageCats"
          :key="String(c.id)"
          type="button"
          class="cat-chip"
          :class="{ on: soloCat === c.id, off: (soloCat != null && soloCat !== c.id) || (hover && hover.all && hover.cat !== c.id) }"
          :style="{ '--c': c.color }"
          :title="catLabel(c.id) + ' — ' + $t('quickReview.inImages', { n: c.images }) + '\n' + $t(soloCat === c.id ? 'quickReview.soloOff' : 'quickReview.soloOn')"
          @mouseenter="hover = { cat: c.id, all: true }"
          @mouseleave="hover = null"
          @click="c.id != null && toggleSolo(c.id)"
        >
          <span class="swatch" />
          <span class="name">{{ c.name }}</span>
          <span class="count">{{ c.n }}</span>
        </button>
      </div>
        <button
          v-if="soloCat != null"
          type="button"
          class="strip-clear"
          :aria-label="$t('quickReview.soloOff')"
          :title="$t('quickReview.soloOff') + ' (Esc)'"
          @click="soloCat = null"
        >
          <i class="fa fa-times" />
        </button>
      </div>

      <div class="ms-auto d-flex align-items-center gap-2">
        <span class="small text-white-50">
          {{ total ? $t('quickReview.range', { from: (page - 1) * perPage + 1, to: Math.min(page * perPage, total), n: total }) : '' }}
        </span>
        <button type="button" class="btn btn-sm btn-outline-light" :disabled="page <= 1 || loading" @click="go(page - 1)">
          <i class="fa fa-chevron-left" />
        </button>
        <button type="button" class="btn btn-sm btn-outline-light" :disabled="page >= pages || loading" @click="go(page + 1)">
          <i class="fa fa-chevron-right" />
        </button>
        <button
          v-if="canReview && grid > 1"
          type="button"
          class="btn btn-sm btn-success"
          :disabled="!pending.length || busy"
          :title="'Shift+Y'"
          @click="approveAll"
        >
          <i class="fa fa-check-square-o" /> {{ $t('quickReview.approvePage', { n: pending.length }) }}
        </button>
      </div>
    </div>

    <div v-if="!loading && !images.length" class="qr-empty text-center text-white-50">
      <i class="fa fa-check-circle-o fa-4x d-block mb-3" />
      {{ status === 'labeled' ? $t('quickReview.allDone') : $t('exportCategories.noMatch') }}
      <div class="mt-3">
        <RouterLink :to="`/dataset/${datasetId}`" class="btn btn-sm btn-outline-light">{{ $t('quickReview.back') }}</RouterLink>
      </div>
    </div>

    <div v-else class="qr-grid" :style="{ gridTemplateColumns: `repeat(${grid}, 1fr)`, gridTemplateRows: `repeat(${Math.max(1, Math.min(grid, Math.ceil(images.length / grid)))}, 1fr)` }">
      <div
        v-for="(img, i) in images"
        :key="img.id"
        class="tile"
        :class="{ focus: i === focus, done: !!decided[img.id] }"
        @click="onTileClick(i)"
        @dblclick="openImage(img)"
      >
        <svg
          class="pic"
          :class="{ zoomed: isZoomed(img), marking: rejecting === img.id }"
          :viewBox="viewBox(img)"
          preserveAspectRatio="xMidYMid meet"
          @wheel.prevent="onWheel($event, img)"
          @mousedown="onPanStart($event, img)"
          @mouseleave="hover = null"
        >
          <image :href="imageUrl(img)" x="0" y="0" :width="img.width" :height="img.height" />
          <g v-if="showShapes">
            <g
              v-for="a in img.annotations"
              :key="a.id"
              :class="{ dim: isDim(img, a.category_id), lit: isLit(img, a.category_id), picked: editing && editing.ann.id === a.id, editable: canReview }"
              @mouseenter="hover = { cat: a.category_id, all: true }"
              @mouseleave="hover = null"
              @click.stop="onShapeClick($event, img, a, i)"
            >
              <title>{{ catLabel(a.category_id) }}{{ canReview ? '\n' + $t('quickReview.clickToEdit') : '' }}</title>
              <polygon
                v-for="(ring, k) in a.segmentation"
                :key="k"
                :points="points(ring)"
                :fill="colorOf(a)"
                fill-opacity="0.28"
                :stroke="colorOf(a)"
                stroke-width="2"
                vector-effect="non-scaling-stroke"
              />
              <template v-for="(p, k) in keypoints(a)" :key="'k' + k">
                <circle :cx="p[0]" :cy="p[1]" :r="Math.max(img.width, img.height) / 250" :fill="colorOf(a)" stroke="#fff" stroke-width="1" vector-effect="non-scaling-stroke" />
              </template>
            </g>
            <!-- problem areas: being marked for a rejection, or from the last one -->
            <g class="regions" pointer-events="none">
              <rect
                v-for="(r, k) in regionsOf(img)"
                :key="'r' + k"
                :x="r[0]"
                :y="r[1]"
                :width="r[2]"
                :height="r[3]"
                vector-effect="non-scaling-stroke"
              />
              <rect
                v-if="drawing && drawing.img === img.id"
                class="drawing"
                :x="drawing.r[0]"
                :y="drawing.r[1]"
                :width="drawing.r[2]"
                :height="drawing.r[3]"
                vector-effect="non-scaling-stroke"
              />
            </g>
          </g>
        </svg>

        <div v-if="decided[img.id]" class="stamp" :class="decided[img.id]">
          <i class="fa" :class="decided[img.id] === 'approved' ? 'fa-check' : 'fa-undo'" />
          {{ $t('review.status.' + decided[img.id]) }}
        </div>

        <div v-if="rejecting === img.id" class="reasons-bar" @click.stop @mousedown.stop @dblclick.stop>
          <div class="mark-hint">
            <i class="fa fa-crosshairs" />
            {{ regions.length ? $t('quickReview.marked', { n: regions.length }) : $t('quickReview.markHint') }}
            <button v-if="regions.length" type="button" class="btn btn-link btn-sm p-0 ms-1" @mousedown.prevent @click="regions = regions.slice(0, -1)">
              {{ $t('quickReview.undoMark') }}
            </button>
          </div>
          <RejectReasons :ref="el => { if (el) reasonsRef = el; }" :note="note" @pick="pickReason" />
        </div>

        <div class="tile-foot d-flex align-items-center gap-2">
          <span class="badge" :class="statusClass(decided[img.id] || img.status)">{{ $t('review.status.' + (decided[img.id] || img.status)) }}</span>
          <div class="min-w-0 flex-grow-1">
            <div class="fname text-truncate" :title="img.file_name">{{ img.file_name }}</div>
            <div class="meta text-truncate">
              <span v-if="img.labeled_by"><i class="fa fa-user-o" /> {{ img.labeled_by }}</span>
              <span :title="catCounts(img).map(c => `${c.name} ${c.n}`).join('\n')">{{ $t('quickReview.nShapes', { n: img.annotations.length }) }}</span>
              <span v-if="img.review_note" class="text-warning" :title="img.review_note"><i class="fa fa-comment-o" /> {{ img.review_note }}</span>
            </div>
          </div>
          <template v-if="rejecting === img.id">
            <input
              :ref="el => { if (el) noteInput = el; }"
              v-model="note"
              class="form-control form-control-sm note"
              :placeholder="$t('review.notePlaceholder')"
              @keydown.enter.stop.prevent="act(img, 'reject')"
              @keydown.esc.stop.prevent="rejecting = null"
              @keydown="onNoteKey"
              @click.stop
            />
            <button type="button" class="btn btn-sm btn-danger" :disabled="busy" @click.stop="act(img, 'reject')">
              <i class="fa fa-undo" />
            </button>
          </template>
          <template v-else-if="canReview">
            <button
              type="button"
              class="btn btn-sm btn-success"
              :disabled="busy || decided[img.id] === 'approved'"
              :title="$t('review.approve') + ' (Y)'"
              @click.stop="act(img, 'approve')"
            ><i class="fa fa-check" /></button>
            <button
              type="button"
              class="btn btn-sm btn-outline-danger"
              :disabled="busy || decided[img.id] === 'rejected'"
              :title="$t('review.reject') + ' (X)'"
              @click.stop="startReject(img)"
            ><i class="fa fa-undo" /></button>
          </template>
          <button type="button" class="btn btn-sm btn-outline-light" :title="$t('quickReview.open') + ' (Enter)'" @click.stop="openImage(img)">
            <i class="fa fa-pencil" />
          </button>
        </div>
      </div>
    </div>

    <!-- change the category of a shape, or delete it -->
    <template v-if="editing">
      <div class="menu-backdrop" @mousedown="closeEdit" @wheel="closeEdit" />
      <div class="shape-menu" :style="editing.style" @keydown.stop>
        <div class="d-flex align-items-center gap-2 mb-2">
          <i class="dot" :style="{ background: colorOf(editing.ann) }" />
          <span class="text-truncate flex-grow-1 fw-semibold" :title="catLabel(editing.ann.category_id)">{{ catLabel(editing.ann.category_id) }}</span>
          <button type="button" class="btn btn-sm btn-outline-danger py-0" :disabled="busy" :title="$t('quickReview.deleteShape') + ' (Ctrl+Del)'" @click="deleteShape">
            <i class="fa fa-trash-o" />
          </button>
        </div>
        <input
          ref="catSearch"
          v-model="catQuery"
          class="form-control form-control-sm mb-1"
          :placeholder="$t('quickReview.changeTo')"
          @keydown="onMenuKey"
        />
        <div class="cat-list">
          <button
            v-for="(c, k) in catChoices"
            :key="c.id"
            type="button"
            class="cat-item"
            :class="{ active: k === catIndex, current: c.id === editing.ann.category_id }"
            :disabled="busy"
            @mouseenter="catIndex = k"
            @click="pickCat(c)"
          >
            <i class="dot" :style="{ background: c.color || '#00e5ff' }" />
            <span class="text-truncate">{{ c.name }}</span>
            <small v-if="c.parents && c.parents.length" class="parent text-truncate">{{ pathLabel(c.parents[0]) }}</small>
            <i v-if="c.id === editing.ann.category_id" class="fa fa-check ms-auto" />
          </button>
          <div v-if="!catChoices.length" class="small text-white-50 px-2 py-1">{{ $t('exportCategories.noMatch') }}</div>
        </div>
      </div>
    </template>

    <div class="qr-help small text-white-50">
      {{ $t('quickReview.keys') }}
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { statusClass } from "@/components/annotator/ReviewBar.vue";
import { modalOpen } from "@/libs/modal";
import { pathLabel } from "@/libs/parents";
import RejectReasons from "@/components/RejectReasons.vue";
import { withReason } from "@/libs/rejectReasons";

const GRIDS = [1, 2, 3, 4];
const GRID_KEY = "review/quickGrid";

function readGrid() {
  try {
    const n = parseInt(localStorage.getItem(GRID_KEY), 10);
    return GRIDS.includes(n) ? n : 3;
  } catch {
    return 3;
  }
}

/**
 * Quick review: one or several images at a time with their annotations drawn,
 * approve / reject each (or the whole page) without opening the annotator.
 */
export default {
  name: "Review",
  components: { RejectReasons },
  props: { identifier: { type: [String, Number], required: true } },
  data() {
    return {
      GRIDS,
      grid: readGrid(),
      status: this.$route.query.status || "labeled",
      labeler: "",
      order: (() => { try { return localStorage.getItem("review/quickOrder") || "file_name"; } catch { return "file_name"; } })(),
      showShapes: true,
      // a category hovered (a shape or the category list): lit in every image
      hover: null,
      // the category strip in the bar: fade the edges that can be scrolled to
      stripFade: { left: false, right: false },
      // a category clicked in a list: only that one shows in every image
      soloCat: null,
      // the shape whose category is being changed: { img, ann, style }
      editing: null,
      catQuery: "",
      catIndex: 0,
      images: [],
      categories: {},
      labelers: [],
      canReview: false,
      datasetName: "",
      total: 0,
      page: 1,
      pages: 1,
      loading: false,
      busy: false,
      focus: 0,
      decided: {},
      views: {},
      // zoom / move every image on the page together (Shift does the other)
      syncZoom: (() => { try { return localStorage.getItem("review/syncZoom") !== "false"; } catch { return true; } })(),
      panMoved: false,
      rejecting: null,
      // problem areas marked while rejecting, [[x, y, w, h], ...] in image pixels
      regions: [],
      drawing: null,
      note: "",
      noteInput: null,
      reasonsRef: null,
      loadSeq: 0,
      advanceTimer: null
    };
  },
  computed: {
    datasetId() {
      return parseInt(this.identifier, 10);
    },
    perPage() {
      return this.grid * this.grid;
    },
    /** categories to change a shape to (the dataset's and any in use), filtered by the search box */
    catChoices() {
      const q = this.catQuery.trim().toLowerCase();
      // only the dataset's own categories (others are refused by the server)
      return Object.values(this.categories)
        .filter(c => c.in_dataset !== false)
        .filter(c => !q || c.name.toLowerCase().includes(q) || (c.parents || []).some(p => p.toLowerCase().includes(q)))
        .sort((a, b) => a.name.localeCompare(b.name, "zh-Hant", { numeric: true }) || a.id - b.id);
    },
    /** categories used on this page: how many shapes, on how many images */
    pageCats() {
      const rows = {};
      this.images.forEach(img => {
        const seen = new Set();
        img.annotations.forEach(a => {
          const key = String(a.category_id);
          const c = this.categories[a.category_id];
          const row = rows[key] || (rows[key] = {
            id: a.category_id == null ? null : a.category_id, n: 0, images: 0,
            name: c ? c.name : this.$t("quickReview.noCategory"), color: (c && c.color) || "#00e5ff"
          });
          row.n += 1;
          if (!seen.has(key)) {
            seen.add(key);
            row.images += 1;
          }
        });
      });
      return Object.values(rows).sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
    },
    pending() {
      return this.images.filter(i => !this.decided[i.id] && i.status !== "approved");
    }
  },
  watch: {
    status() { this.go(1); },
    labeler() { this.go(1); },
    catQuery() {
      this.catIndex = 0;
    },
    soloCat(cat) {
      // keep the kept category visible in the strip
      if (cat == null) return;
      this.$nextTick(() => {
        const el = this.$refs.strip && this.$refs.strip.querySelector(".cat-chip.on");
        if (el) el.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
    },
    grid() {
      this.$nextTick(this.measure);
    },
    syncZoom(value) {
      try {
        localStorage.setItem("review/syncZoom", String(value));
      } catch {
        // not remembered
      }
    },
    order(value) {
      try {
        localStorage.setItem("review/quickOrder", value);
      } catch {
        // not remembered
      }
      this.go(1);
    }
  },
  methods: {
    statusClass,
    setGrid(n) {
      // keep the first image of the current page in view
      const first = (this.page - 1) * this.perPage;
      this.grid = n;
      try {
        localStorage.setItem(GRID_KEY, String(n));
      } catch {
        // not remembered
      }
      this.go(Math.floor(first / (n * n)) + 1);
    },
    /* ---------- zoom (wheel, at the cursor) and pan (drag) per image ---------- */
    viewOf(img) {
      return this.views[img.id] || { x: 0, y: 0, w: img.width, h: img.height };
    },
    viewBox(img) {
      const v = this.viewOf(img);
      return `${v.x} ${v.y} ${v.w} ${v.h}`;
    },
    isZoomed(img) {
      return !!this.views[img.id];
    },
    /** screen point -> image coordinates (the svg letterboxes the image) */
    toImage(svg, clientX, clientY) {
      const pt = svg.createSVGPoint();
      pt.x = clientX;
      pt.y = clientY;
      return pt.matrixTransform(svg.getScreenCTM().inverse());
    },
    setView(img, v) {
      // fully out: back to the whole image
      if (v.w >= img.width && v.h >= img.height) {
        const views = { ...this.views };
        delete views[img.id];
        this.views = views;
        return;
      }
      // keep inside the image
      v.w = Math.min(v.w, img.width);
      v.h = Math.min(v.h, img.height);
      v.x = Math.min(Math.max(0, v.x), img.width - v.w);
      v.y = Math.min(Math.max(0, v.y), img.height - v.h);
      this.views = { ...this.views, [img.id]: v };
    },
    zoomAt(img, svg, clientX, clientY, factor) {
      const p = this.toImage(svg, clientX, clientY);
      const v = this.viewOf(img);
      const minSize = Math.max(16, Math.min(img.width, img.height) / 40);
      let w = v.w * factor, h = v.h * factor;
      if (w < minSize || h < minSize) return;
      // the point under the cursor stays under the cursor
      this.setView(img, { x: p.x - (p.x - v.x) * factor, y: p.y - (p.y - v.y) * factor, w, h });
    },
    onWheel(e, img) {
      const factor = Math.exp((e.deltaY > 0 ? 1 : -1) * Math.min(Math.abs(e.deltaY), 120) / 600);
      if (this.syncZoom !== e.shiftKey) {
        // every image on the page zooms to the same place (Shift: the other way round)
        const v0 = this.viewOf(img);
        const minSize = Math.max(16, Math.min(img.width, img.height) / 40);
        if (factor < 1 && (v0.w * factor < minSize || v0.h * factor < minSize)) return;
        const svg = e.currentTarget;
        const p = this.toImage(svg, e.clientX, e.clientY);
        this.images.forEach(other => {
          const v = this.viewOf(other);
          const sx = other.width / img.width, sy = other.height / img.height;
          const ox = p.x * sx, oy = p.y * sy;
          this.setView(other, { x: ox - (ox - v.x) * factor, y: oy - (oy - v.y) * factor, w: v.w * factor, h: v.h * factor });
        });
        return;
      }
      this.focus = this.images.indexOf(img);
      this.zoomAt(img, e.currentTarget, e.clientX, e.clientY, factor);
    },
    regionsOf(img) {
      if (this.rejecting === img.id) return this.regions;
      const status = this.decided[img.id] || img.status;
      return status === "rejected" ? img.review_regions || [] : [];
    },
    /** rejecting: drag on the image to mark a problem area */
    startMark(e, img) {
      const svg = e.currentTarget;
      const p0 = this.toImage(svg, e.clientX, e.clientY);
      const clamp = (v, max) => Math.min(Math.max(0, v), max);
      const rect = ev => {
        const p = this.toImage(svg, ev.clientX, ev.clientY);
        const x0 = clamp(Math.min(p0.x, p.x), img.width), y0 = clamp(Math.min(p0.y, p.y), img.height);
        const x1 = clamp(Math.max(p0.x, p.x), img.width), y1 = clamp(Math.max(p0.y, p.y), img.height);
        return [x0, y0, x1 - x0, y1 - y0];
      };
      this.drawing = { img: img.id, r: [p0.x, p0.y, 0, 0] };
      const move = ev => {
        this.drawing = { img: img.id, r: rect(ev) };
      };
      const up = ev => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
        const r = rect(ev);
        this.drawing = null;
        // a click is not a box (and not a tile click either)
        const ctm = svg.getScreenCTM();
        if (r[2] * ctm.a > 6 && r[3] * ctm.d > 6) {
          this.regions = [...this.regions, r.map(v => Math.round(v))];
          this.panMoved = true;
        }
        this.$nextTick(() => this.noteInput && this.noteInput.focus());
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
    },
    onPanStart(e, img) {
      // a new press: whatever the last drag left behind no longer counts
      this.panMoved = false;
      if (e.button === 0 && this.rejecting === img.id && !e.shiftKey) {
        e.preventDefault();
        this.startMark(e, img);
        return;
      }
      if (e.button !== 0 || !this.isZoomed(img)) return;
      const svg = e.currentTarget;
      const start = this.toImage(svg, e.clientX, e.clientY);
      const together = this.syncZoom !== e.shiftKey;
      const others = together ? this.images.filter(o => this.isZoomed(o)) : [img];
      const starts = Object.fromEntries(others.map(o => [o.id, { ...this.viewOf(o) }]));
      this.panMoved = false;
      const move = ev => {
        // move the view so the grabbed point follows the mouse (the others the same share)
        const ctm = svg.getScreenCTM();
        const dx = (ev.clientX - e.clientX) / ctm.a, dy = (ev.clientY - e.clientY) / ctm.d;
        if (Math.abs(ev.clientX - e.clientX) + Math.abs(ev.clientY - e.clientY) > 3) this.panMoved = true;
        others.forEach(o => {
          const v0 = starts[o.id];
          const sx = o.width / img.width, sy = o.height / img.height;
          this.setView(o, { ...v0, x: v0.x - dx * sx, y: v0.y - dy * sy });
        });
      };
      const up = () => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
      void start;
    },
    onTileClick(i) {
      // the end of a drag is not a click
      if (this.panMoved) {
        this.panMoved = false;
        return;
      }
      this.focus = i;
    },
    resetZoom() {
      this.views = {};
    },
    imageUrl(img) {
      // the whole file for one image or a zoomed one; smaller copies for a grid
      if (this.grid === 1 || (this.views[img.id] && this.views[img.id].w < img.width * 0.7)) return `/api/image/${img.id}`;
      const width = { 2: 1000, 3: 700, 4: 520 }[this.grid] || 700;
      return `/api/image/${img.id}?width=${Math.min(width, img.width)}`;
    },
    points(ring) {
      const out = [];
      for (let i = 0; i + 1 < ring.length; i += 2) out.push(`${ring[i]},${ring[i + 1]}`);
      return out.join(" ");
    },
    keypoints(a) {
      const k = a.keypoints || [];
      const out = [];
      for (let i = 0; i + 2 < k.length; i += 3) if (k[i + 2] > 0) out.push([k[i], k[i + 1]]);
      return out;
    },
    /** the category to show alone in this image, or null for all */
    focusCat(img) {
      if (this.hover && (this.hover.all || this.hover.img === img.id)) return this.hover.cat;
      return this.soloCat;
    },
    isDim(img, cat) {
      const f = this.focusCat(img);
      return f != null && f !== cat;
    },
    isLit(img, cat) {
      const f = this.focusCat(img);
      return f != null && f === cat;
    },
    pathLabel,
    onShapeClick(e, img, ann, i) {
      if (this.panMoved) {
        this.panMoved = false;
        return;
      }
      this.focus = i;
      if (!this.canReview) return;
      // next to the cursor, inside the window
      const left = Math.min(e.clientX + 8, window.innerWidth - 280);
      const top = Math.min(e.clientY + 8, window.innerHeight - 330);
      this.editing = { img, ann, style: { left: `${Math.max(8, left)}px`, top: `${Math.max(8, top)}px` } };
      this.catQuery = "";
      this.catIndex = Math.max(0, this.catChoices.findIndex(c => c.id === ann.category_id));
      this.$nextTick(() => this.$refs.catSearch && this.$refs.catSearch.focus());
    },
    closeEdit() {
      this.editing = null;
    },
    /** keys in the shape menu's search box */
    onMenuKey(e) {
      if (e.key === "ArrowDown") this.moveCat(1);
      else if (e.key === "ArrowUp") this.moveCat(-1);
      else if (e.key === "Enter") this.pickCat(this.catChoices[this.catIndex]);
      else if (e.key === "Escape") this.closeEdit();
      // Ctrl+Delete deletes the shape (not Ctrl+Backspace, which deletes a word)
      else if (e.key === "Delete" && (e.ctrlKey || e.metaKey)) this.deleteShape();
      else return;
      e.preventDefault();
    },
    moveCat(d) {
      const n = this.catChoices.length;
      if (n) this.catIndex = (this.catIndex + d + n) % n;
    },
    async pickCat(c) {
      const ed = this.editing;
      if (!c || !ed || this.busy) return;
      if (c.id === ed.ann.category_id) return this.closeEdit();
      this.busy = true;
      try {
        await axios.put(`/api/annotation/${ed.ann.id}`, { category_id: c.id });
        ed.ann.category_id = c.id;
        this.$toastr.success(this.$t("quickReview.changedTo", { name: c.name }));
        this.closeEdit();
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      } finally {
        this.busy = false;
      }
    },
    async deleteShape() {
      const ed = this.editing;
      if (!ed || this.busy) return;
      this.busy = true;
      try {
        await axios.delete(`/api/annotation/${ed.ann.id}`);
        ed.img.annotations = ed.img.annotations.filter(a => a.id !== ed.ann.id);
        this.$toastr.success(this.$t("quickReview.shapeDeleted"));
        this.closeEdit();
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      } finally {
        this.busy = false;
      }
    },
    /** the mouse wheel scrolls the category strip sideways */
    onStripWheel(e) {
      const el = this.$refs.strip;
      if (!el || el.scrollWidth <= el.clientWidth || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    },
    updateStripFade() {
      const el = this.$refs.strip;
      if (!el) return;
      this.stripFade = {
        left: el.scrollLeft > 2,
        right: el.scrollLeft + el.clientWidth < el.scrollWidth - 2
      };
    },
    toggleSolo(cat) {
      this.soloCat = this.soloCat === cat ? null : cat;
      this.hover = null;
    },
    catLabel(id) {
      const c = this.categories[id];
      if (!c) return this.$t("quickReview.noCategory");
      const parent = (c.parents || [])[0];
      return parent ? `${pathLabel(parent)} › ${c.name}` : c.name;
    },
    /** categories used on one image, most used first */
    catCounts(img) {
      const counts = {};
      img.annotations.forEach(a => (counts[a.category_id] = (counts[a.category_id] || 0) + 1));
      return Object.entries(counts)
        .map(([id, n]) => {
          const c = this.categories[id];
          const cid = id === "null" || id === "undefined" ? null : Number(id);
          return { id: cid, n, name: c ? c.name : this.$t("quickReview.noCategory"), color: (c && c.color) || "#00e5ff" };
        })
        .sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
    },
    measure() {
      this.$nextTick(this.updateStripFade);
    },
    colorOf(a) {
      const c = this.categories[a.category_id];
      return (c && c.color) || "#00e5ff";
    },
    async load() {
      // only the newest request counts (keys can ask for pages faster than they arrive)
      const seq = ++this.loadSeq;
      clearTimeout(this.advanceTimer);
      this.advanceTimer = null;
      this.loading = true;
      try {
        const r = await axios.get(`/api/review/dataset/${this.datasetId}/queue`, {
          params: { status: this.status, user: this.labeler, order: this.order, page: this.page, per_page: this.perPage }
        });
        if (seq !== this.loadSeq) return;
        const d = r.data;
        this.images = d.images || [];
        this.categories = Object.fromEntries((d.categories || []).map(c => [c.id, c]));
        this.labelers = d.labelers || [];
        this.canReview = !!d.can_review;
        this.datasetName = d.dataset_name || "";
        this.total = d.total;
        this.pages = d.pages;
        if (this.page > this.pages) {
          this.page = Math.max(1, this.pages);
          if (this.total) return this.load();
        }
        this.decided = {};
        this.views = {};
        this.focus = 0;
        this.rejecting = null;
        this.regions = [];
        this.drawing = null;
        this.editing = null;
        this.hover = null;
      } finally {
        if (seq === this.loadSeq) {
          this.loading = false;
          this.$nextTick(this.measure);
        }
      }
    },
    go(page) {
      this.page = Math.max(1, page);
      this.load();
    },
    openImage(img) {
      this.$router.push({ name: "annotate", params: { identifier: img.id } });
    },
    /** a number key in the empty reason box picks that saved reason */
    onNoteKey(e) {
      const r = this.reasonsRef && this.reasonsRef.forKey(e, this.note);
      if (!r) return;
      e.preventDefault();
      e.stopPropagation();
      this.pickReason(r);
    },
    pickReason(r) {
      this.note = withReason(this.note, r);
      this.$nextTick(() => this.noteInput && this.noteInput.focus());
    },
    startReject(img) {
      if (!this.canReview) return;
      this.rejecting = img.id;
      this.note = "";
      this.regions = [];
      this.$nextTick(() => this.noteInput && this.noteInput.focus());
    },
    async act(img, action) {
      if (this.busy || !this.canReview) return;
      this.busy = true;
      try {
        const body = { action, note: action === "reject" ? this.note : "" };
        if (action === "reject") body.regions = this.regions;
        const r = await axios.post(`/api/review/image/${img.id}`, body);
        img.review_regions = r.data.review_regions || [];
        this.decided = { ...this.decided, [img.id]: action === "approve" ? "approved" : "rejected" };
        this.rejecting = null;
        this.afterDecision();
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      } finally {
        this.busy = false;
      }
    },
    async approveAll() {
      const ids = this.pending.map(i => i.id);
      if (!ids.length || this.busy) return;
      this.busy = true;
      try {
        await axios.post(`/api/review/image/${ids[0]}`, { action: "approve", image_ids: ids });
        const decided = { ...this.decided };
        ids.forEach(id => (decided[id] = "approved"));
        this.decided = decided;
        this.$toastr.success(this.$t("quickReview.approvedN", { n: ids.length }));
        this.afterDecision();
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      } finally {
        this.busy = false;
      }
    },
    /** next undecided image on the page, or the next page once all are done */
    afterDecision() {
      const next = this.images.findIndex((img, i) => i > this.focus && !this.decided[img.id]);
      const any = this.images.findIndex(img => !this.decided[img.id]);
      if (next >= 0) this.focus = next;
      else if (any >= 0) this.focus = any;
      else {
        // the page is done. Images that left this list make the next ones move
        // up: load the same page again; otherwise go on to the next page.
        const page = this.page;
        const seq = this.loadSeq;
        const left = this.status !== "all" && this.images.some(img => this.decided[img.id] && this.decided[img.id] !== this.status);
        clearTimeout(this.advanceTimer);
        this.advanceTimer = setTimeout(() => {
          this.advanceTimer = null;
          if (this.page !== page || this.loadSeq !== seq || this.loading) return;
          if (left) this.load();
          else if (page < this.pages) this.go(page + 1);
        }, 600);
      }
    },
    onKey(e) {
      if (modalOpen()) return;
      if (this.editing) {
        if (e.key === "Escape") this.closeEdit();
        return;
      }
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      // browser shortcuts (Ctrl+1, Ctrl+P, ...) are not ours; Shift is (Shift+Y)
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      // the reject box is open (but not focused): keys belong to it
      if (this.rejecting != null) {
        const rejected = this.images.find(i => i.id === this.rejecting);
        if (e.key === "Escape") {
          e.preventDefault();
          this.rejecting = null;
        } else if (e.key === "Enter" && rejected) {
          e.preventDefault();
          this.act(rejected, "reject");
        } else if (/^[1-9]$/.test(e.key) && this.reasonsRef) {
          const r = this.reasonsRef.reasons[Number(e.key) - 1];
          if (r) {
            e.preventDefault();
            this.pickReason(r);
          }
        }
        return;
      }
      // Enter / Space on a focused button presses that button
      if ((tag === "BUTTON" || tag === "A") && (e.key === "Enter" || e.key === " ")) return;
      const img = this.images[this.focus];
      const cols = this.grid;
      const key = e.key.toLowerCase();
      const move = { arrowright: 1, arrowleft: -1, arrowdown: cols, arrowup: -cols }[key];
      if (move !== undefined) {
        e.preventDefault();
        const to = this.focus + move;
        if (to >= 0 && to < this.images.length) this.focus = to;
        else if (to >= this.images.length && this.page < this.pages && !this.loading) this.go(this.page + 1);
        else if (to < 0 && this.page > 1 && !this.loading) this.go(this.page - 1);
        return;
      }
      if (key === "y" && e.shiftKey) {
        e.preventDefault();
        this.approveAll();
      } else if (key === "y" && img) {
        e.preventDefault();
        if (this.decided[img.id] !== "approved") this.act(img, "approve");
      } else if (key === "x" && img) {
        e.preventDefault();
        if (this.decided[img.id] !== "rejected") this.startReject(img);
      } else if (key === "enter" && img) {
        e.preventDefault();
        this.openImage(img);
      } else if (key === "escape" && this.soloCat != null) {
        this.soloCat = null;
      } else if (key === "0" || key === "escape") {
        this.resetZoom();
      } else if (key === "h") {
        this.showShapes = !this.showShapes;
      } else if (/^[1-4]$/.test(key)) {
        this.setGrid(parseInt(key, 10));
      } else if (key === "pagedown" || key === "n") {
        if (this.page < this.pages && !this.loading) this.go(this.page + 1);
      } else if (key === "pageup" || key === "p") {
        if (this.page > 1 && !this.loading) this.go(this.page - 1);
      }
    }
  },
  created() {
    this.load();
    window.addEventListener("keydown", this.onKey);
    window.addEventListener("resize", this.measure);
  },
  beforeUnmount() {
    clearTimeout(this.advanceTimer);
    this.loadSeq++;
    window.removeEventListener("keydown", this.onKey);
    window.removeEventListener("resize", this.measure);
  }
};
</script>

<style scoped>
.quick-review {
  background: #1f2430;
  height: var(--vh);
  display: flex;
  flex-direction: column;
  text-align: left;
  color: #e9ecef;
}
.qr-bar {
  padding: 8px 16px;
  background: #2a2f3c;
  border-bottom: 1px solid #383e4c;
}
.qr-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  gap: 8px;
  padding: 8px;
}
.tile {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: #14171f;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}
.tile.focus {
  border-color: #ffc107;
}
.tile.done .pic {
  opacity: 0.55;
}
.pic {
  flex: 1;
  min-height: 0;
  width: 100%;
}
.pic.zoomed {
  cursor: grab;
}
.pic.zoomed:active {
  cursor: grabbing;
}
.tile-foot {
  padding: 4px 8px;
  background: #262b37;
  font-size: 0.8rem;
}
.fname {
  font-weight: 600;
}
.meta {
  color: #adb5bd;
  font-size: 0.72rem;
}
.meta span + span::before {
  content: "·";
  margin: 0 5px;
}
.note {
  max-width: 220px;
}
.stamp {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.85rem;
  color: #fff;
}
.stamp.approved {
  background: #198754;
}
.stamp.rejected {
  background: #dc3545;
}
.min-w-0 {
  min-width: 0;
}
.dim {
  opacity: 0.15;
}
.lit polygon {
  fill-opacity: 0.5;
}
.legend {
  position: absolute;
  top: 6px;
  left: 6px;
  max-width: calc(100% - 110px);
  max-height: 45%;
  overflow: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  cursor: default;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(20, 23, 31, 0.82);
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: nowrap;
}
.chip b {
  color: #adb5bd;
  font-weight: 600;
}
.chip {
  flex: none;
  cursor: pointer;
}
.chip.on {
  box-shadow: inset 0 0 0 1.5px #ffc107;
}
.cat-bar {
  /* takes the room left in its row of the bar */
  flex: 1 1 240px;
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 3px;
  border-radius: 999px;
  background: #1c2029;
  border: 1px solid #3a4150;
  transition: border-color 0.15s;
}
.cat-bar.solo {
  border-color: rgba(255, 193, 7, 0.6);
}
.cat-strip {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.22) transparent;
}
/* soft edges where there is more to scroll to */
.cat-strip.fade-right {
  -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent);
  mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent);
}
.cat-strip.fade-left {
  -webkit-mask-image: linear-gradient(to left, #000 calc(100% - 28px), transparent);
  mask-image: linear-gradient(to left, #000 calc(100% - 28px), transparent);
}
.cat-strip.fade-left.fade-right {
  -webkit-mask-image: linear-gradient(to right, transparent, #000 28px, #000 calc(100% - 28px), transparent);
  mask-image: linear-gradient(to right, transparent, #000 28px, #000 calc(100% - 28px), transparent);
}
.cat-strip::-webkit-scrollbar {
  height: 4px;
}
.cat-strip::-webkit-scrollbar-track {
  background: transparent;
  margin: 0 14px;
}
.cat-strip::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 4px;
}
.cat-strip:hover::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.35);
}
.cat-chip {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 4px 3px 10px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #ced4da;
  font-size: 0.8rem;
  line-height: 1.3;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, opacity 0.15s, box-shadow 0.15s;
}
.cat-chip:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.cat-chip .swatch {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--c) 30%, transparent);
}
.cat-chip .count {
  min-width: 24px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.09);
  color: #adb5bd;
  font-size: 0.72rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
.cat-chip.on {
  background: color-mix(in srgb, var(--c) 26%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 75%, white 10%);
  color: #fff;
}
.cat-chip.on .count {
  background: color-mix(in srgb, var(--c) 55%, transparent);
  color: #fff;
}
.cat-chip.off {
  opacity: 0.38;
}
.cat-chip.off:hover {
  opacity: 0.85;
}
.strip-clear {
  flex: none;
  width: 24px;
  height: 24px;
  margin-left: 2px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #ced4da;
  font-size: 0.75rem;
  cursor: pointer;
}
.strip-clear:hover {
  background: rgba(255, 193, 7, 0.25);
  color: #fff;
}
.solo-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px 3px 10px;
  border-radius: 999px;
  background: rgba(255, 193, 7, 0.15);
  border: 1px solid #ffc107;
  font-size: 0.8rem;
}
.solo-tag .btn-close {
  font-size: 0.6rem;
}
.chip.off {
  opacity: 0.35;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  display: inline-block;
}
.editable {
  cursor: pointer;
}
.picked polygon {
  stroke: #fff;
  stroke-width: 3;
  stroke-dasharray: 6 4;
  fill-opacity: 0.5;
}
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1050;
}
.shape-menu {
  position: fixed;
  z-index: 1051;
  width: 270px;
  padding: 10px;
  background: #2a2f3c;
  border: 1px solid #454c5c;
  border-radius: 8px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.85rem;
}
.cat-list {
  max-height: 240px;
  overflow: auto;
}
.cat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 4px 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  text-align: left;
}
.cat-item.active {
  background: #3b4252;
}
.cat-item.current {
  color: #ffc107;
}
.cat-item .parent {
  color: #8f98a8;
  font-size: 0.7rem;
}
.pic.marking {
  cursor: crosshair;
}
.regions rect {
  fill: rgba(255, 107, 107, 0.12);
  stroke: #ff6b6b;
  stroke-width: 2;
  stroke-dasharray: 8 5;
}
.regions rect.drawing {
  stroke: #ffc107;
  fill: rgba(255, 193, 7, 0.12);
}
.mark-hint {
  margin-bottom: 4px;
  color: #ff8787;
  font-size: 0.78rem;
}
.reasons-bar {
  padding: 5px 8px 0;
  background: #262b37;
  border-top: 1px solid #383e4c;
}
.qr-empty {
  margin-top: 18vh;
}
.qr-help {
  padding: 2px 16px 6px;
}
</style>
