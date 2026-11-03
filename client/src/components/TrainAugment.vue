<template>
  <div class="train-augment small">
    <!-- done once when exporting: the images are in the zip -->
    <div class="aug-block">
      <div class="aug-head">
        <i class="fa fa-file-archive-o" /> {{ $t('trainAug.export') }}
        <span class="text-muted fw-normal">{{ $t('trainAug.exportWhat') }}</span>
      </div>
      <div v-if="exportOps.length">
        <span class="text-muted">{{ $t(exportAugment.scope === 'all' ? 'trainAug.exportCopiesAll' : 'trainAug.exportCopies', { n: exportAugment.copies }) }}</span>
        <span v-for="op in exportOps" :key="op.key" class="chip on">{{ op.label }}</span>
        <span v-if="exportAugment.images" class="text-muted">{{ $t('trainAug.exportImages', { n: exportAugment.images }) }}</span>
      </div>
      <div v-else class="text-muted">{{ $t('trainAug.exportNone') }}</div>
    </div>

    <!-- done by Ultralytics while training, at random each epoch -->
    <div class="aug-block">
      <div class="aug-head">
        <i class="fa fa-random" /> {{ $t('trainAug.train') }}
        <span class="text-muted fw-normal">{{ $t('trainAug.trainWhat') }}</span>
      </div>
      <div>
        <component
          :is="editable ? 'button' : 'span'"
          v-for="a in active"
          :key="a.key"
          :type="editable ? 'button' : undefined"
          class="chip on"
          :class="{ custom: a.custom, btnchip: editable }"
          :title="`${a.key}=${a.raw}` + (a.custom ? ' (' + $t('trainAug.custom') + ')' : '') + (editable ? ' · ' + $t('trainAug.clickToEdit') : '')"
          @click="editable && $emit('edit', a.key, a.raw)"
        >
          {{ a.label }} <b>{{ a.text }}</b>
        </component>
      </div>
      <div v-if="inactive.length" class="text-muted mt-1">
        {{ $t('trainAug.off') }}
        <component
          :is="editable ? 'button' : 'span'"
          v-for="a in inactive"
          :key="a.key"
          :type="editable ? 'button' : undefined"
          class="chip off"
          :class="{ custom: a.custom, btnchip: editable }"
          :title="`${a.key}=${a.raw}` + (editable ? ' · ' + $t('trainAug.clickToEdit') : '')"
          @click="editable && $emit('edit', a.key, a.raw)"
        >{{ a.label }}</component>
      </div>
      <div v-if="closeMosaic" class="text-muted mt-1">{{ closeMosaic }}</div>
      <div v-if="!hasDefaults" class="text-muted">{{ $t('trainAug.unknown') }}</div>
    </div>

    <div v-if="overlap.length" class="text-muted">
      <i class="fa fa-info-circle" /> {{ $t('trainAug.overlap', { list: overlap.join('、') }) }}
    </div>
  </div>
</template>

<script>
import { OPS as EXPORT_OPS } from "@/components/ExportAugment.vue";
import { showValue } from "@/libs/trainArgs";

// Ultralytics training augmentations: how to show each value
//   pct: a probability, range: ± a fraction, deg: ± degrees, gain: a fraction
export const TRAIN_AUGS = [
  { key: "mosaic", kind: "pct", tasks: "box" },
  { key: "mixup", kind: "pct", tasks: "box" },
  { key: "cutmix", kind: "pct", tasks: "box" },
  { key: "copy_paste", kind: "pct", tasks: ["segment"] },
  { key: "fliplr", kind: "pct" },
  { key: "flipud", kind: "pct" },
  { key: "degrees", kind: "deg", tasks: "box" },
  { key: "translate", kind: "range", tasks: "box" },
  { key: "scale", kind: "range" },
  { key: "shear", kind: "deg", tasks: "box" },
  { key: "perspective", kind: "gain", tasks: "box" },
  { key: "hsv_h", kind: "range" },
  { key: "hsv_s", kind: "range" },
  { key: "hsv_v", kind: "range" },
  { key: "bgr", kind: "pct", tasks: "box" },
  { key: "auto_augment", kind: "text", tasks: ["classify"] },
  { key: "erasing", kind: "pct", tasks: ["classify"] }
];

const BOX_TASKS = ["detect", "segment", "obb", "pose"];

// the same change made at export and again while training
const OVERLAP = [
  ["hflip", "fliplr"],
  ["vflip", "flipud"],
  ["rotate", "degrees"],
  ["scale", "scale"],
  ["color", "hsv_v"]
];

/** Which augmentations a training uses: those already in the export, and
 *  those Ultralytics applies while training (defaults or own arguments). */
export default {
  name: "TrainAugment",
  props: {
    exportAugment: { type: Object, default: null },
    // the training arguments' defaults (catalog)
    defaults: { type: Object, default: () => ({}) },
    // own arguments of this training (typed values)
    extra: { type: Object, default: () => ({}) },
    task: { type: String, default: "detect" },
    // chips can be clicked to change the value
    editable: { type: Boolean, default: false }
  },
  emits: ["edit"],
  computed: {
    hasDefaults() {
      return Object.keys(this.defaults || {}).length > 0 || Object.keys(this.extra || {}).length > 0;
    },
    exportOps() {
      const ops = (this.exportAugment && this.exportAugment.ops) || {};
      return EXPORT_OPS.filter(o => ops[o.key]).map(o => {
        let label = this.$t("exportAugment.op." + o.key);
        if (o.key === "rotate" && typeof ops.rotate === "number") label += ` ±${ops.rotate}°`;
        if (o.key === "scale" && typeof ops.scale === "number") label += ` ≥${Math.round(ops.scale * 100)}%`;
        return { key: o.key, label };
      });
    },
    items() {
      if (!this.hasDefaults) return [];
      const extra = this.extra || {};
      return TRAIN_AUGS.filter(a => {
        if (!a.tasks) return true;
        if (a.tasks === "box") return BOX_TASKS.includes(this.task);
        return a.tasks.includes(this.task);
      })
        .filter(a => a.key in extra || a.key in this.defaults)
        .map(a => {
          const custom = a.key in extra;
          const value = custom ? extra[a.key] : this.defaults[a.key];
          return { ...a, custom, value, raw: showValue(value), label: this.$t("trainAug.arg." + a.key), text: this.fmt(a, value), on: this.isOn(a, value) };
        });
    },
    active() {
      return this.items.filter(a => a.on);
    },
    inactive() {
      return this.items.filter(a => !a.on);
    },
    closeMosaic() {
      const mosaic = this.items.find(a => a.key === "mosaic");
      if (!mosaic || !mosaic.on) return "";
      const extra = this.extra || {};
      const n = "close_mosaic" in extra ? extra.close_mosaic : this.defaults.close_mosaic;
      return n ? this.$t("trainAug.closeMosaic", { n }) : "";
    },
    overlap() {
      const ops = (this.exportAugment && this.exportAugment.ops) || {};
      return OVERLAP.filter(([op, arg]) => ops[op] && this.active.some(a => a.key === arg)).map(([op]) => this.$t("exportAugment.op." + op));
    }
  },
  methods: {
    isOn(a, v) {
      if (a.kind === "text") return !!v && !/^(none|false)$/i.test(String(v));
      return Number(v) > 0;
    },
    fmt(a, v) {
      if (a.kind === "text") return String(v);
      const n = Number(v);
      const pct = Math.round(n * 1000) / 10;
      if (a.kind === "pct") return `${pct}%`;
      if (a.kind === "range") return `±${pct}%`;
      if (a.kind === "deg") return `±${n}°`;
      return String(n);
    }
  }
};
</script>

<style scoped>
.aug-block {
  margin-bottom: 6px;
}
.aug-head {
  font-weight: 600;
  margin-bottom: 2px;
}
.chip {
  display: inline-block;
  border-radius: 999px;
  padding: 0 8px;
  margin: 1px 2px;
  font-size: 0.75rem;
  line-height: 1.5;
  border: 1px solid transparent;
}
.chip.on {
  background: #e7f1ff;
  color: #084298;
}
.chip.off {
  background: #f1f3f5;
  color: #868e96;
  text-decoration: line-through;
}
.chip.custom {
  border-color: #0d6efd;
}
.btnchip {
  cursor: pointer;
}
.btnchip:hover {
  filter: brightness(0.95);
}
</style>
