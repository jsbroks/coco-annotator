<template>
  <div class="video-list">
    <div class="d-flex gap-2 flex-wrap align-items-center">
      <label class="form-label mb-0 me-auto">{{ $t('video.title') }}</label>
      <button type="button" class="btn btn-outline-primary btn-sm" :disabled="disabled" @click="$refs.picker.click()">
        <i class="fa fa-film" /> {{ videos.length ? $t('video.addMore') : $t('video.choose') }}
      </button>
      <button v-if="videos.length" type="button" class="btn btn-link btn-sm" :disabled="disabled" @click="clear">
        {{ $t('importDataset.clear') }}
      </button>
    </div>
    <input ref="picker" type="file" multiple :accept="accept" class="d-none" @change="add" />

    <div v-if="!videos.length" class="form-text">{{ $t('video.emptyHint') }}</div>

    <template v-else>
      <!-- totals -->
      <div class="totals small mt-2">
        <span><i class="fa fa-film" /> {{ $t('video.totalVideos', { n: videos.length }) }}</span>
        <span>{{ $t('video.totalDuration') }} <strong>{{ fmt(totals.duration) }}</strong></span>
        <span>{{ $t('video.totalFrames') }} <strong>{{ totals.frames.toLocaleString() }}</strong></span>
        <span v-if="totals.trimmed">
          {{ $t('video.selected') }} <strong>{{ fmt(totals.selDuration) }}</strong>（{{ totals.selFrames.toLocaleString() }} {{ $t('video.frameUnit') }}）
        </span>
        <span>{{ $t('video.expectedTotal') }} <strong>≈ {{ totals.expected.toLocaleString() }}</strong> {{ $t('video.frames') }}</span>
        <span v-if="totals.uploading" class="text-primary"><i class="fa fa-spinner fa-spin" /> {{ $t('video.uploadingN', { n: totals.uploading }) }}</span>
      </div>

      <!-- interval and limit, for all videos -->
      <div class="row g-2 mt-1">
        <div class="col-sm-7">
          <label class="form-label small mb-0" for="videoEvery">{{ $t('video.everyLabel') }}</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">{{ $t('video.everyPrefix') }}</span>
            <input
              v-if="unit === 'seconds'"
              id="videoEvery"
              v-model.number="everySeconds"
              type="number" min="0.04" max="3600" step="0.5"
              class="form-control"
              :disabled="disabled"
            />
            <input
              v-else
              id="videoEvery"
              v-model.number="everyFrames"
              type="number" min="1" max="100000" step="1"
              class="form-control"
              :disabled="disabled"
            />
            <select v-model="unit" class="form-select unit-select" :disabled="disabled" :aria-label="$t('video.unit')">
              <option value="seconds">{{ $t('video.seconds') }}</option>
              <option value="frames">{{ $t('video.frameUnit') }}</option>
            </select>
            <span class="input-group-text">{{ $t('video.everySuffix') }}</span>
          </div>
        </div>
        <div class="col-sm-5">
          <label class="form-label small mb-0" for="videoMax">{{ $t('video.max') }}</label>
          <div class="input-group input-group-sm">
            <input id="videoMax" v-model.number="maxFrames" type="number" min="1" max="20000" step="100" class="form-control" :disabled="disabled" />
            <span class="input-group-text">{{ $t('video.frames') }}</span>
          </div>
        </div>
      </div>

      <!-- one card per video -->
      <div v-for="(v, i) in videos" :key="v.key" class="video-card mt-2">
        <div class="d-flex gap-2 align-items-start">
          <video
            v-if="v.url && v.playable !== false"
            :ref="el => (players[v.key] = el)"
            class="preview flex-shrink-0"
            :src="v.url"
            preload="metadata"
            muted
            controls
            @error="v.playable = false"
            @loadedmetadata="v.playable = true"
          />
          <div v-else class="preview no-preview flex-shrink-0">
            <i class="fa fa-film fa-2x" />
            <span class="small">{{ $t('video.noPreview') }}</span>
          </div>

          <div class="flex-grow-1 min-w-0">
            <div class="d-flex align-items-center gap-2">
              <strong class="text-truncate" :title="v.name">{{ i + 1 }}. {{ v.name }}</strong>
              <span class="small text-muted text-nowrap">{{ size(v.size) }}</span>
              <button type="button" class="btn btn-link btn-sm text-danger ms-auto p-0" :disabled="disabled" :title="$t('video.remove')" @click="remove(v)">
                <i class="fa fa-times" />
              </button>
            </div>

            <template v-if="v.status === 'uploading'">
              <div class="progress mt-1" style="height: 8px">
                <div class="progress-bar" :class="{ 'progress-bar-striped progress-bar-animated': v.pct >= 100 }" :style="{ width: Math.max(v.pct, 1) + '%' }" />
              </div>
              <div class="small mt-1" :class="stalled(v) ? 'text-danger' : 'text-muted'">
                <template v-if="v.pct >= 100">
                  <i class="fa fa-spinner fa-spin" /> {{ $t('video.probing') }}
                </template>
                <template v-else>
                  {{ $t('video.uploading') }} {{ size(v.loaded) }} / {{ size(v.size) }}（{{ Math.floor(v.pct) }}%）
                  <template v-if="v.speed"> · {{ size(v.speed) }}/s · {{ $t('video.left', { t: eta(v) }) }}</template>
                  <div v-if="stalled(v)"><i class="fa fa-exclamation-triangle" /> {{ $t('video.stalled') }}</div>
                </template>
              </div>
            </template>
            <div v-else-if="v.status === 'waiting'" class="small text-muted mt-1"><i class="fa fa-clock-o" /> {{ $t('video.waiting') }}</div>
            <div v-else-if="v.status === 'error'" class="small text-danger mt-1"><i class="fa fa-exclamation-circle" /> {{ v.error }}</div>

            <template v-else-if="v.info">
              <div class="small text-muted info-line">
                <span>{{ $t('video.duration') }} {{ fmt(v.info.duration) }}</span>
                <span>{{ v.info.fps }} fps</span>
                <span>{{ (v.info.frames || 0).toLocaleString() }} {{ $t('video.frameUnit') }}</span>
                <span v-if="v.info.width">{{ v.info.width }}×{{ v.info.height }}</span>
              </div>

              <!-- start / end -->
              <div class="trim mt-1">
                <div class="range-pair">
                  <input
                    type="range" class="form-range" min="0" :max="v.info.duration || 0" step="0.1"
                    :value="v.start" :disabled="disabled"
                    @input="setStart(v, $event.target.value)"
                  />
                  <input
                    type="range" class="form-range" min="0" :max="v.info.duration || 0" step="0.1"
                    :value="v.end" :disabled="disabled"
                    @input="setEnd(v, $event.target.value)"
                  />
                  <div class="range-fill" :style="fillStyle(v)" />
                </div>
                <div class="d-flex flex-wrap align-items-center gap-1 small mt-1">
                  <span>{{ $t('video.start') }}</span>
                  <input
                    class="form-control form-control-sm time-input"
                    :value="fmt(v.start)" :disabled="disabled"
                    @keydown.enter.prevent="$event.target.blur()"
                    @change="setStart(v, parseTime($event.target.value), $event)"
                  />
                  <button
                    v-if="v.playable"
                    type="button" class="btn btn-outline-secondary btn-sm py-0 px-1"
                    :title="$t('video.useCurrent')" :disabled="disabled" @click="setStart(v, current(v))"
                  ><i class="fa fa-step-backward" /></button>
                  <span class="ms-2">{{ $t('video.end') }}</span>
                  <input
                    class="form-control form-control-sm time-input"
                    :value="fmt(v.end)" :disabled="disabled"
                    @keydown.enter.prevent="$event.target.blur()"
                    @change="setEnd(v, parseTime($event.target.value), $event)"
                  />
                  <button
                    v-if="v.playable"
                    type="button" class="btn btn-outline-secondary btn-sm py-0 px-1"
                    :title="$t('video.useCurrent')" :disabled="disabled" @click="setEnd(v, current(v))"
                  ><i class="fa fa-step-forward" /></button>
                  <a v-if="isTrimmed(v)" href="#" class="ms-1" @click.prevent="resetTrim(v)">{{ $t('video.wholeVideo') }}</a>
                  <span class="ms-auto text-nowrap">
                    {{ fmt(v.end - v.start) }} · {{ $t('video.expected', { n: expected(v).toLocaleString() }) }}
                  </span>
                </div>
              </div>
            </template>

            <div v-if="v.stage" class="progress mt-1" style="height: 14px">
              <div class="progress-bar bg-info" :style="{ width: v.stage.pct + '%' }">
                {{ $t('video.stage.extract', { name: '' }) }} {{ Math.round(v.stage.pct) }}%
              </div>
            </div>
            <div v-if="v.done !== undefined" class="small text-success mt-1">
              <i class="fa fa-check" /> {{ $t('video.addedN', { n: v.done }) }}
            </div>
          </div>
        </div>
      </div>
      <div class="form-text">{{ $t('video.hint') }}</div>
    </template>
  </div>
</template>

<script>
import axios from "axios";

const CHUNK = 8 * 1024 * 1024; // bytes per request
const RETRIES = 5;
const ACCEPT = ".mp4,.mov,.avi,.mkv,.webm,.m4v,.mpg,.mpeg,.wmv,video/*";
let counter = 0;

/**
 * Videos for the import dialog. Each one is uploaded as soon as it is picked
 * (the server reports its length, fps and frame count); then its start / end
 * can be set before the frames are extracted with ``importInto``.
 */
export default {
  name: "VideoList",
  props: {
    disabled: { type: Boolean, default: false }
  },
  emits: ["change"],
  data() {
    return {
      accept: ACCEPT,
      videos: [],
      players: {},
      unit: "seconds",
      everySeconds: 1,
      everyFrames: 10,
      maxFrames: 1000,
      uploading: false,
      now: Date.now(),
      ticker: null
    };
  },
  computed: {
    totals() {
      const t = { duration: 0, frames: 0, selDuration: 0, selFrames: 0, expected: 0, trimmed: false, uploading: 0 };
      this.videos.forEach(v => {
        if (v.status === "uploading" || v.status === "waiting") t.uploading += 1;
        if (!v.info) return;
        t.duration += v.info.duration || 0;
        t.frames += v.info.frames || 0;
        const span = this.span(v);
        t.selDuration += v.end - v.start;
        t.selFrames += span.count;
        t.expected += this.expected(v);
        if (this.isTrimmed(v)) t.trimmed = true;
      });
      return t;
    },
    valid() {
      const everyOk = this.unit === "frames"
        ? Number.isInteger(this.everyFrames) && this.everyFrames >= 1
        : this.everySeconds >= 0.04;
      return everyOk && this.maxFrames >= 1 && this.videos.every(v => v.status !== "ready" || v.end > v.start);
    },
    state() {
      return {
        count: this.videos.length,
        ready: this.videos.filter(v => v.status === "ready").length,
        busy: this.totals.uploading > 0,
        valid: this.valid
      };
    }
  },
  watch: {
    state: {
      deep: true,
      immediate: true,
      handler(state) {
        this.$emit("change", state);
      }
    }
  },
  beforeUnmount() {
    if (this.ticker) clearInterval(this.ticker);
    this.clear();
  },
  methods: {
    // ------------------------------------------------------------ helpers
    fmt(seconds) {
      if (seconds == null || isNaN(seconds)) return "--:--";
      const s = Math.max(0, seconds);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const rest = (s % 60).toFixed(1).padStart(4, "0");
      return h ? `${h}:${String(m).padStart(2, "0")}:${rest}` : `${String(m).padStart(2, "0")}:${rest}`;
    },
    /** "1:23.5", "83.5" or "0:01:23" -> seconds (NaN if not a time) */
    parseTime(text) {
      const parts = String(text).trim().split(":").map(Number);
      if (!parts.length || parts.some(isNaN)) return NaN;
      return parts.reduce((total, p) => total * 60 + p, 0);
    },
    size(bytes) {
      const mb = bytes / 1024 / 1024;
      return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
    },
    isTrimmed(v) {
      return v.info && (v.start > 0.05 || v.end < (v.info.duration || 0) - 0.05);
    },
    /** frames [first, last] the server will look at */
    span(v) {
      const fps = v.info.fps || 30;
      const first = Math.round(v.start * fps);
      const last = Math.min((v.info.frames || 1) - 1, Math.round(v.end * fps));
      return { first, last, count: Math.max(0, last - first + 1) };
    },
    expected(v) {
      if (!v.info) return 0;
      const step = this.unit === "frames"
        ? Math.max(1, this.everyFrames || 1)
        : Math.max(1, Math.round((this.everySeconds || 1) * (v.info.fps || 30)));
      return Math.min(this.maxFrames || 0, Math.ceil(this.span(v).count / step));
    },
    fillStyle(v) {
      const d = v.info.duration || 1;
      return { left: `${(100 * v.start) / d}%`, width: `${(100 * (v.end - v.start)) / d}%` };
    },
    current(v) {
      const player = this.players[v.key];
      return player ? player.currentTime : 0;
    },
    setStart(v, value, event) {
      const n = Number(value);
      if (!isNaN(n)) v.start = Math.min(Math.max(0, n), Math.max(0, v.end - 0.1));
      if (event) event.target.value = this.fmt(v.start);
      this.seek(v, v.start);
    },
    setEnd(v, value, event) {
      const n = Number(value);
      if (!isNaN(n)) v.end = Math.max(Math.min(v.info.duration || n, n), v.start + 0.1);
      if (event) event.target.value = this.fmt(v.end);
      this.seek(v, v.end);
    },
    seek(v, time) {
      const player = this.players[v.key];
      if (player && v.playable) player.currentTime = time;
    },
    resetTrim(v) {
      v.start = 0;
      v.end = v.info.duration || 0;
    },

    // ------------------------------------------------------------ list
    add(event) {
      const names = new Set(this.videos.map(v => v.name));
      for (const file of event.target.files) {
        if (names.has(file.name)) continue;
        names.add(file.name);
        counter += 1;
        this.videos.push({
          key: counter, file, name: file.name, size: file.size, url: URL.createObjectURL(file),
          playable: null, status: "waiting", pct: 0, info: null, uploadId: null, start: 0, end: 0,
          error: "", stage: null, done: undefined, controller: null
        });
      }
      event.target.value = "";
      this.uploadQueue();
    },
    /** one upload at a time, in the order picked */
    async uploadQueue() {
      if (this.uploading) return;
      this.uploading = true;
      try {
        for (;;) {
          const v = this.videos.find(x => x.status === "waiting");
          if (!v) break;
          await this.upload(v);
        }
      } finally {
        this.uploading = false;
      }
    },
    async upload(v) {
      v.status = "uploading";
      Object.assign(v, { loaded: 0, speed: 0, lastLoaded: 0, lastTime: Date.now(), progressAt: Date.now() });
      if (!this.ticker) this.ticker = setInterval(() => (this.now = Date.now()), 1000);
      v.controller = new AbortController();
      const signal = v.controller.signal;
      const track = loaded => {
        const now = Date.now();
        v.pct = v.size ? (100 * loaded) / v.size : 100;
        // speed over the last few seconds (smoothed)
        const dt = (now - v.lastTime) / 1000;
        if (dt >= 1) {
          const rate = (loaded - v.lastLoaded) / dt;
          v.speed = v.speed ? v.speed * 0.6 + rate * 0.4 : rate;
          v.lastTime = now;
          v.lastLoaded = loaded;
        }
        if (loaded > v.loaded) v.progressAt = now;
        v.loaded = loaded;
      };
      try {
        // in pieces: proxies often refuse one big request, and a lost piece is just sent again
        const started = await axios.post("/api/dataset/video/stage/start", { name: v.name, size: v.size }, { signal });
        v.uploadId = started.data.upload_id;
        let offset = 0;
        while (offset < v.size) {
          const piece = v.file.slice(offset, offset + CHUNK);
          for (let attempt = 1; ; attempt++) {
            try {
              const r = await axios.put(`/api/dataset/video/stage/${v.uploadId}/chunk?offset=${offset}`, piece, {
                headers: { "Content-Type": "application/octet-stream" },
                signal,
                onUploadProgress: e => track(offset + e.loaded)
              });
              offset = r.data.received;
              break;
            } catch (error) {
              const status = error.response && error.response.status;
              if (axios.isCancel(error) || attempt >= RETRIES || (status && status < 500 && status !== 408 && status !== 429)) throw error;
              await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
            }
          }
          track(offset);
        }
        v.pct = 100;
        const r = await axios.post(`/api/dataset/video/stage/${v.uploadId}/finish`, null, { signal });
        if (!this.videos.includes(v)) {
          this.discard(r.data.upload_id);
          return;
        }
        v.uploadId = r.data.upload_id;
        v.info = r.data;
        v.start = 0;
        v.end = r.data.duration || 0;
        v.status = "ready";
      } catch (error) {
        if (axios.isCancel(error)) return;
        this.discard(v.uploadId);
        v.uploadId = null;
        v.status = "error";
        v.error = (error.response && error.response.data && error.response.data.message) || String(error);
      } finally {
        v.controller = null;
        if (!this.videos.some(x => x.status === "uploading") && this.ticker) {
          clearInterval(this.ticker);
          this.ticker = null;
        }
      }
    },
    /** no bytes sent for 20 s */
    stalled(v) {
      return v.pct < 100 && this.now - v.progressAt > 20000;
    },
    eta(v) {
      if (!v.speed) return "–";
      const seconds = Math.round((v.size - v.loaded) / v.speed);
      if (seconds < 60) return this.$t("video.seconds_n", { n: seconds });
      const m = Math.floor(seconds / 60);
      return m < 60 ? this.$t("video.minutes_n", { m, s: seconds % 60 }) : this.$t("video.hours_n", { h: Math.floor(m / 60), m: m % 60 });
    },
    discard(uploadId) {
      if (uploadId) axios.delete(`/api/dataset/video/stage/${uploadId}`).catch(() => {});
    },
    remove(v) {
      if (v.controller) v.controller.abort();
      if (v.uploadId && v.done === undefined) this.discard(v.uploadId);
      if (v.url) URL.revokeObjectURL(v.url);
      this.videos = this.videos.filter(x => x !== v);
      delete this.players[v.key];
    },
    clear() {
      [...this.videos].forEach(v => this.remove(v));
    },
    /** after an import: forget the videos (their uploads are used up) */
    reset() {
      this.videos.forEach(v => v.url && URL.revokeObjectURL(v.url));
      this.videos = [];
      this.players = {};
    },

    // ------------------------------------------------------------ import
    /** Extract the frames of every ready video into the dataset; returns the frames added. */
    async importInto(datasetId, waitForTask) {
      let total = 0;
      for (const v of this.videos.filter(x => x.status === "ready")) {
        const form = new FormData();
        form.append("upload_id", v.uploadId);
        if (this.unit === "frames") form.append("every_frames", this.everyFrames);
        else form.append("every_seconds", this.everySeconds);
        if (this.isTrimmed(v)) {
          form.append("start_seconds", v.start.toFixed(3));
          if (v.end < (v.info.duration || 0) - 0.05) form.append("end_seconds", v.end.toFixed(3));
        }
        form.append("max_frames", this.maxFrames);
        v.stage = { pct: 0 };
        try {
          const r = await axios.post(`/api/dataset/${datasetId}/video`, form, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          const task = await waitForTask(r.data.id, pct => (v.stage.pct = pct));
          if (task && task.errors) this.$toastr.error(this.$t("video.failed", { name: v.name }));
          const added = await axios.get(`/api/dataset/${datasetId}/data`, { params: { folder: r.data.folder, limit: 1 } })
            .then(res => res.data.total).catch(() => 0);
          v.done = added;
          total += added;
        } catch (error) {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(`${v.name}: ${data.message || error}`);
        } finally {
          v.stage = null;
        }
      }
      return total;
    }
  }
};
</script>

<style scoped>
.totals {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  background: #f1f5fb;
  border: 1px solid #dbe5f3;
  border-radius: 6px;
  padding: 6px 10px;
}
.video-card {
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 8px;
}
.preview {
  width: 176px;
  height: 99px;
  background: #000;
  border-radius: 4px;
}
.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #adb5bd;
  background: #343a40;
  text-align: center;
  padding: 4px;
}
.min-w-0 {
  min-width: 0;
}
.info-line span + span::before {
  content: "·";
  margin: 0 6px;
}
.unit-select {
  max-width: 5.5rem;
  flex: 0 0 auto;
}
.time-input {
  width: 6.5rem;
  font-variant-numeric: tabular-nums;
}
.range-pair {
  position: relative;
  height: 20px;
}
.range-pair .form-range {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  pointer-events: none;
  background: transparent;
}
.range-pair .form-range::-webkit-slider-thumb {
  pointer-events: auto;
  position: relative;
  z-index: 2;
}
.range-pair .form-range::-moz-range-thumb {
  pointer-events: auto;
}
.range-pair .form-range::-webkit-slider-runnable-track {
  background: transparent;
}
.range-pair .form-range::-moz-range-track {
  background: transparent;
}
.range-pair::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 8px;
  height: 4px;
  border-radius: 2px;
  background: #dee2e6;
}
.range-fill {
  position: absolute;
  top: 8px;
  height: 4px;
  border-radius: 2px;
  background: #0d6efd;
}
</style>
