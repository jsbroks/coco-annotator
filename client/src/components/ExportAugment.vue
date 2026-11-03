<template>
  <div class="export-augment">
    <div class="form-check d-flex align-items-center gap-2 ps-0">
      <input
        id="exportAugmentOn"
        type="checkbox"
        class="form-check-input m-0"
        :checked="modelValue.enabled"
        @change="set({ enabled: $event.target.checked })"
      />
      <label class="form-check-label fw-semibold mb-0" for="exportAugmentOn">{{ $t('exportAugment.title') }}</label>
    </div>
    <div v-if="!modelValue.enabled" class="form-text mt-1">{{ $t('exportAugment.off') }}</div>

    <template v-else>
      <div class="d-flex align-items-center gap-2 mt-2">
        <label class="small mb-0" for="exportAugmentCopies">{{ $t(splitOn && modelValue.scope !== 'all' ? 'exportAugment.copies' : 'exportAugment.copiesAll') }}</label>
        <select
          id="exportAugmentCopies"
          class="form-select form-select-sm w-auto"
          :value="modelValue.copies"
          @change="set({ copies: Number($event.target.value) })"
        >
          <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
        </select>
        <span class="small text-muted">{{ $t('exportAugment.copiesHint') }}</span>
      </div>

      <div class="ops mt-2">
        <div v-for="op in OPS" :key="op.key" class="op">
          <div class="form-check d-flex align-items-center gap-2 ps-0 mb-0">
            <input
              :id="'aug-' + op.key"
              type="checkbox"
              class="form-check-input m-0"
              :checked="!!modelValue.ops[op.key]"
              @change="toggle(op, $event.target.checked)"
            />
            <label class="form-check-label mb-0" :for="'aug-' + op.key">
              <i class="fa me-1" :class="op.icon" />{{ $t('exportAugment.op.' + op.key) }}
            </label>
            <template v-if="op.param && modelValue.ops[op.key]">
              <select
                class="form-select form-select-sm w-auto ms-1 py-0"
                :value="modelValue.ops[op.key]"
                @change="setOp(op.key, Number($event.target.value))"
              >
                <option v-for="v in op.choices" :key="v" :value="v">{{ op.label(v) }}</option>
              </select>
            </template>
          </div>
          <div class="small text-muted hint">{{ $t('exportAugment.hint.' + op.key) }}</div>
          <div v-if="yolo && op.yolo" class="small hint yolo-hint" :class="op.yolo === 'default' ? 'text-warning-emphasis' : 'text-info-emphasis'">
            <template v-if="op.yolo === 'default'"><i class="fa fa-info-circle" /> {{ $t('exportAugment.yoloDefault') }}</template>
            <template v-else><i class="fa fa-lightbulb-o" /> {{ $t('exportAugment.yoloArg') }} <code>{{ op.yolo }}</code></template>
          </div>
        </div>
      </div>

      <div v-if="splitOn" class="form-check d-flex align-items-center gap-2 ps-0 mt-3">
        <input
          id="exportAugmentAll"
          type="checkbox"
          class="form-check-input m-0"
          :checked="modelValue.scope === 'all'"
          @change="set({ scope: $event.target.checked ? 'all' : 'train' })"
        />
        <label class="form-check-label mb-0" for="exportAugmentAll">{{ $t('exportAugment.alsoValTest') }}</label>
      </div>
      <div v-if="splitOn && modelValue.scope === 'all'" class="small text-warning-emphasis ms-4">
        <i class="fa fa-exclamation-triangle" /> {{ $t('exportAugment.alsoValTestWarning') }}
      </div>

      <div v-if="!chosen" class="small mt-2 text-danger">{{ $t('exportAugment.pickOne') }}</div>
      <div v-else-if="splitOn" class="small mt-2">
        <div v-for="k in ['train', 'val', 'test']" v-show="counts[k].orig" :key="k">
          <b class="me-1">{{ $t('exportSplit.' + k) }}</b>
          <template v-if="counts[k].extra">
            {{ $t('exportAugment.partWith', { orig: counts[k].orig, extra: counts[k].extra, total: counts[k].orig + counts[k].extra }) }}
          </template>
          <template v-else>{{ $t('exportAugment.partOriginal', { orig: counts[k].orig }) }}</template>
        </div>
      </div>
      <template v-else>
        <div class="small mt-2">
          {{ $t('exportAugment.partWith', { orig: imageCount || 0, extra: (imageCount || 0) * modelValue.copies, total: (imageCount || 0) * (modelValue.copies + 1) }) }}
        </div>
        <div class="small text-warning-emphasis mt-1">
          <i class="fa fa-exclamation-triangle" /> {{ $t('exportAugment.noSplitWarning') }}
        </div>
      </template>
      <div class="form-text mt-1">{{ $t('exportAugment.withImages') }}</div>
    </template>
  </div>
</template>

<script>
/** Options for augmenting the training images of an export. */
/**
 * ``yolo``: "default" when Ultralytics already does it while training (an
 * exported copy adds little), or the training argument that turns it on.
 */
export const OPS = [
  { key: "hflip", icon: "fa-arrows-h", yolo: "default" },
  { key: "vflip", icon: "fa-arrows-v", yolo: "flipud=0.5" },
  { key: "rot90", icon: "fa-repeat" },
  { key: "rotate", icon: "fa-rotate-right", param: 15, choices: [5, 10, 15, 20, 30, 45], label: v => `±${v}°`, yolo: "degrees=10" },
  { key: "scale", icon: "fa-search-plus", param: 0.8, choices: [0.9, 0.8, 0.7, 0.6, 0.5], label: v => `${Math.round(v * 100)}%–100%`, yolo: "default" },
  { key: "color", icon: "fa-adjust", yolo: "default" },
  { key: "exposure", icon: "fa-sun-o" },
  { key: "gray", icon: "fa-circle-o" },
  { key: "cutout", icon: "fa-th-large" },
  { key: "motion", icon: "fa-angle-double-right" },
  { key: "blur", icon: "fa-tint" },
  { key: "noise", icon: "fa-braille" },
  { key: "jpeg", icon: "fa-file-image-o" }
];

export function defaultAugment() {
  return { enabled: false, copies: 2, ops: { hflip: true, color: true }, scope: "train" };
}

/**
 * Originals and augmented images per part: {train: {orig, extra}, ...}.
 * ``sizes`` are the originals per part (the split comes first).
 */
export function augmentedCounts(sizes, value) {
  const payload = augmentPayload(value);
  const out = {};
  ["train", "val", "test"].forEach(k => {
    const orig = (sizes && sizes[k]) || 0;
    const augmented = payload && (payload.scope === "all" || k === "train");
    out[k] = { orig, extra: augmented ? orig * payload.copies : 0 };
  });
  return out;
}

/** What the server gets (null when off or nothing chosen). */
export function augmentPayload(value) {
  if (!value || !value.enabled) return null;
  const ops = Object.fromEntries(Object.entries(value.ops).filter(([, v]) => v));
  return Object.keys(ops).length ? { copies: value.copies, ops, scope: value.scope === "all" ? "all" : "train" } : null;
}

export default {
  name: "ExportAugment",
  props: {
    modelValue: { type: Object, required: true },
    imageCount: { type: Number, default: null },
    // a YOLO export: say which options Ultralytics already does while training
    yolo: { type: Boolean, default: false },
    // the split (it comes first): originals per part
    splitOn: { type: Boolean, default: false },
    splitSizes: { type: Object, default: () => ({}) }
  },
  emits: ["update:modelValue"],
  data() {
    return { OPS };
  },
  computed: {
    chosen() {
      return Object.values(this.modelValue.ops).some(Boolean);
    },
    counts() {
      return augmentedCounts(this.splitSizes, this.modelValue);
    }
  },
  methods: {
    set(change) {
      this.$emit("update:modelValue", { ...this.modelValue, ...change });
    },
    setOp(key, value) {
      this.set({ ops: { ...this.modelValue.ops, [key]: value } });
    },
    toggle(op, on) {
      this.setOp(op.key, on ? op.param || true : false);
    }
  }
};
</script>

<style scoped>
.ops {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 8px 16px;
}
.yolo-hint code {
  font-size: 0.75rem;
}
.op .hint {
  padding-left: 1.6rem;
  line-height: 1.3;
}
</style>
