<template>
  <div class="export-split">
    <div class="form-check d-flex align-items-center gap-2 ps-0">
      <input
        id="exportSplitOn"
        type="checkbox"
        class="form-check-input m-0"
        :checked="enabled"
        @change="$emit('update:enabled', $event.target.checked)"
      />
      <label class="form-check-label fw-semibold mb-0" for="exportSplitOn">{{ $t('exportSplit.title') }}</label>
    </div>

    <div v-if="!enabled" class="form-text mt-1">
      {{ yolo ? $t('exportSplit.offYolo') : $t('exportSplit.offCoco') }}
    </div>

    <template v-else>
      <div class="d-flex flex-wrap align-items-center gap-1 mt-2">
        <span class="small text-muted me-1">{{ $t('exportSplit.presets') }}</span>
        <button
          v-for="preset in presets"
          :key="preset.join('/')"
          type="button"
          class="btn btn-sm py-0"
          :class="isPreset(preset) ? 'btn-primary' : 'btn-outline-secondary'"
          @click="setRatios(preset)"
        >
          {{ preset.join(' / ') }}
        </button>
      </div>

      <div class="row g-2 mt-1">
        <div v-for="(name, i) in SUBSETS" :key="name" class="col-4">
          <label class="form-label small mb-0" :for="'exportSplit' + name">
            <span class="legend-dot" :class="'bg-' + COLORS[i]" />
            {{ $t('exportSplit.' + name) }}
          </label>
          <div class="input-group input-group-sm">
            <input
              :id="'exportSplit' + name"
              type="number"
              min="0"
              max="100"
              step="1"
              class="form-control"
              :class="{ 'is-invalid': !valid }"
              :value="ratios[name]"
              @input="setOne(name, $event.target.value)"
            />
            <span class="input-group-text">%</span>
          </div>
          <div class="small text-muted text-center mt-1">
            {{ imageCount == null ? '' : $t('exportSplit.images', { n: sizes[name] }) }}
          </div>
        </div>
      </div>

      <div class="progress-stacked mt-2" style="height: 10px">
        <div
          v-for="(name, i) in SUBSETS"
          :key="name"
          class="progress"
          role="progressbar"
          :style="{ width: Math.max(0, Number(ratios[name]) || 0) + '%' }"
        >
          <div class="progress-bar" :class="'bg-' + COLORS[i]" />
        </div>
      </div>

      <div v-if="!valid" class="small text-danger mt-1">
        {{ $t('exportSplit.invalid', { sum: total }) }}
      </div>
      <div v-else-if="imageCount != null" class="small text-muted mt-1">
        {{ $t('exportSplit.estimate', { n: imageCount * perImage }) }}
      </div>

      <div class="d-flex align-items-center gap-2 mt-2">
        <label class="form-label small mb-0 text-nowrap" for="exportSplitSeed">{{ $t('exportSplit.seed') }}</label>
        <input
          id="exportSplitSeed"
          type="number"
          class="form-control form-control-sm"
          style="max-width: 110px"
          :value="seed"
          @input="$emit('update:seed', parseInt($event.target.value, 10) || 0)"
        />
        <button type="button" class="btn btn-sm btn-link p-0" @click="$emit('update:seed', randomSeed())">
          <i class="fa fa-random" /> {{ $t('exportSplit.newSeed') }}
        </button>
      </div>
      <div class="form-text mt-0">{{ $t('exportSplit.seedHint') }}</div>
      <div class="form-text mt-0">{{ yolo ? $t('exportSplit.layoutYolo') : $t('exportSplit.layoutCoco') }}</div>
    </template>
  </div>
</template>

<script>
const SUBSETS = ["train", "val", "test"];

/** Same allocation as the server (geometry/yolo_format.py split_images) */
export function splitSizes(n, ratios) {
  const sizes = {};
  ["val", "test"].forEach(name => (sizes[name] = Math.round((n * (Number(ratios[name]) || 0)) / 100)));
  ["val", "test"].forEach(name => {
    if ((Number(ratios[name]) || 0) > 0 && sizes[name] === 0 && n - sizes.val - sizes.test > 1) sizes[name] = 1;
  });
  while (n && n - sizes.val - sizes.test < 1) {
    const largest = sizes.val >= sizes.test ? "val" : "test";
    sizes[largest] -= 1;
  }
  return { train: n - sizes.val - sizes.test, val: sizes.val, test: sizes.test };
}

export function splitValid(ratios) {
  const values = SUBSETS.map(name => Number(ratios[name]));
  if (values.some(v => !Number.isFinite(v) || v < 0)) return false;
  return values[0] > 0 && Math.abs(values.reduce((a, b) => a + b, 0) - 100) < 0.01;
}

export default {
  name: "ExportSplit",
  props: {
    enabled: { type: Boolean, default: false },
    ratios: { type: Object, required: true },
    seed: { type: Number, default: 42 },
    /** images that will be exported (null while unknown) */
    imageCount: { type: Number, default: null },
    // versions of each picture (augmentation): pictures are split, each with its versions
    perImage: { type: Number, default: 1 },
    yolo: { type: Boolean, default: false }
  },
  emits: ["update:enabled", "update:ratios", "update:seed"],
  data() {
    return {
      SUBSETS,
      COLORS: ["primary", "warning", "success"],
      presets: [[80, 20, 0], [70, 20, 10], [80, 10, 10], [70, 15, 15]]
    };
  },
  computed: {
    total() {
      return SUBSETS.reduce((n, name) => n + (Number(this.ratios[name]) || 0), 0);
    },
    valid() {
      return splitValid(this.ratios);
    },
    sizes() {
      const sizes = splitSizes(this.imageCount || 0, this.ratios);
      return Object.fromEntries(Object.entries(sizes).map(([k, v]) => [k, v * this.perImage]));
    }
  },
  methods: {
    isPreset(preset) {
      return SUBSETS.every((name, i) => Number(this.ratios[name]) === preset[i]);
    },
    setRatios([train, val, test]) {
      this.$emit("update:ratios", { train, val, test });
    },
    /** Editing val or test gives / takes the difference from train */
    setOne(name, raw) {
      const value = raw === "" ? "" : Math.max(0, Math.min(100, Number(raw)));
      const next = { ...this.ratios, [name]: value };
      if (name !== "train" && value !== "") {
        const rest = 100 - (Number(next.val) || 0) - (Number(next.test) || 0);
        if (rest > 0) next.train = rest;
      }
      this.$emit("update:ratios", next);
    },
    randomSeed() {
      return Math.floor(Math.random() * 100000);
    }
  }
};
</script>

<style scoped>
.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 2px;
}
</style>
