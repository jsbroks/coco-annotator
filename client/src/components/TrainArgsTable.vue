<template>
  <div class="train-args">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
      <div class="input-group input-group-sm search">
        <span class="input-group-text"><i class="fa fa-search" /></span>
        <input v-model.trim="query" class="form-control" :placeholder="$t('trainArgs.search')" autocapitalize="off" spellcheck="false" />
      </div>
      <div class="form-check form-switch mb-0 small">
        <input id="argsChangedOnly" v-model="changedOnly" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="argsChangedOnly">{{ $t('trainArgs.changedOnly', { n: changedCount }) }}</label>
      </div>
      <button v-if="changedCount" type="button" class="btn btn-sm btn-link text-danger p-0 ms-auto" @click="resetAll">
        <i class="fa fa-undo" /> {{ $t('trainArgs.resetAll') }}
      </button>
    </div>

    <div v-for="g in shownGroups" :key="g.key" class="group">
      <button type="button" class="group-head" @click="toggle(g.key)">
        <i class="fa" :class="isOpen(g.key) ? 'fa-caret-down' : 'fa-caret-right'" />
        <b>{{ $t('trainArgs.group.' + g.key) }}</b>
        <span class="text-muted small">{{ g.rows.length }}</span>
        <span v-if="g.changed" class="badge text-bg-primary">{{ $t('trainArgs.changed', { n: g.changed }) }}</span>
      </button>
      <div v-show="isOpen(g.key)" class="rows">
        <div v-for="row in g.rows" :key="row.key" class="arg" :class="{ changed: isChanged(row.key) }">
          <label class="name" :for="'arg-' + row.key">
            <code>{{ row.key }}</code>
            <span v-if="$te('trainArgs.hint.' + row.key)" class="hint">{{ $t('trainArgs.hint.' + row.key) }}</span>
          </label>
          <div class="value">
            <select
              v-if="row.kind === 'bool'"
              :id="'arg-' + row.key"
              class="form-select form-select-sm"
              :value="modelValue[row.key] || ''"
              @change="set(row.key, $event.target.value)"
            >
              <option value="">{{ $t('trainArgs.default', { v: show(row.default) }) }}</option>
              <option value="True">True</option>
              <option value="False">False</option>
            </select>
            <template v-else>
              <input
                :id="'arg-' + row.key"
                class="form-control form-control-sm"
                :value="modelValue[row.key] || ''"
                :placeholder="show(row.default)"
                :inputmode="row.kind === 'number' ? 'decimal' : 'text'"
                :list="row.choices ? 'argChoices-' + row.key : null"
                autocapitalize="off"
                spellcheck="false"
                @input="set(row.key, $event.target.value)"
              />
              <datalist v-if="row.choices" :id="'argChoices-' + row.key">
                <option v-for="c in row.choices" :key="c" :value="c" />
              </datalist>
            </template>
            <button
              type="button"
              class="btn btn-sm btn-link reset"
              :class="{ invisible: !isChanged(row.key) }"
              :title="$t('trainArgs.reset', { v: show(row.default) })"
              @click="set(row.key, '')"
            >
              <i class="fa fa-undo" />
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!shownGroups.length" class="text-muted small">{{ $t('trainArgs.none') }}</div>
  </div>
</template>

<script>
import { showValue } from "@/libs/trainArgs";

// which group each argument belongs to; the rest go to "other"
const GROUPS = [
  ["optim", ["optimizer", "lr0", "lrf", "cos_lr", "momentum", "weight_decay", "warmup_epochs", "warmup_momentum", "warmup_bias_lr", "nbs", "dropout"]],
  ["augment", ["hsv_h", "hsv_s", "hsv_v", "degrees", "translate", "scale", "shear", "perspective", "flipud", "fliplr", "bgr", "mosaic", "close_mosaic", "mixup", "cutmix", "copy_paste", "copy_paste_mode", "auto_augment", "erasing", "multi_scale"]],
  ["loss", ["box", "cls", "cls_pw", "dfl", "pose", "kobj", "rle", "angle", "dis", "dlog", "dgrad", "dlam", "overlap_mask", "mask_ratio"]],
  ["data", ["cache", "workers", "fraction", "rect", "single_cls", "cls_remap", "freeze"]],
  ["run", ["device", "time", "seed", "deterministic", "amp", "compile", "channels_last", "val", "split", "iou", "max_det", "save", "save_period", "save_json", "plots", "profile", "verbose"]]
];

// suggested values
const CHOICES = {
  optimizer: ["auto", "SGD", "AdamW", "Adam", "NAdam", "RAdam", "RMSProp"],
  cache: ["False", "ram", "disk"],
  device: ["0", "0,1", "cpu"],
  copy_paste_mode: ["flip", "mixup"],
  auto_augment: ["randaugment", "autoaugment", "augmix"],
  split: ["val", "test"]
};

/** Every training argument with its default; a value typed in replaces the
 *  default (empty: the default). v-model: {name: text}. */
export default {
  name: "TrainArgsTable",
  props: {
    defaults: { type: Object, required: true },
    modelValue: { type: Object, required: true },
    // set elsewhere on the page
    exclude: { type: Array, default: () => [] }
  },
  emits: ["update:modelValue"],
  data() {
    return { query: "", changedOnly: false, open: { optim: true } };
  },
  computed: {
    groups() {
      const keys = Object.keys(this.defaults || {}).filter(k => !this.exclude.includes(k));
      const used = new Set();
      const out = GROUPS.map(([key, names]) => {
        const rows = names.filter(n => keys.includes(n)).map(n => this.row(n));
        rows.forEach(r => used.add(r.key));
        return { key, rows };
      });
      out.push({ key: "other", rows: keys.filter(k => !used.has(k)).map(k => this.row(k)) });
      return out.filter(g => g.rows.length);
    },
    shownGroups() {
      const q = this.query.toLowerCase();
      return this.groups
        .map(g => {
          const rows = g.rows.filter(r => {
            if (this.changedOnly && !this.isChanged(r.key)) return false;
            if (!q) return true;
            const hint = this.$te("trainArgs.hint." + r.key) ? this.$t("trainArgs.hint." + r.key).toLowerCase() : "";
            return r.key.includes(q) || hint.includes(q);
          });
          return { ...g, rows, changed: rows.filter(r => this.isChanged(r.key)).length };
        })
        .filter(g => g.rows.length);
    },
    changedCount() {
      return Object.keys(this.modelValue).filter(k => this.isChanged(k)).length;
    }
  },
  methods: {
    row(key) {
      const d = this.defaults[key];
      const kind = typeof d === "boolean" ? "bool" : typeof d === "number" ? "number" : "text";
      return { key, default: d, kind, choices: CHOICES[key] || null };
    },
    show(v) {
      return showValue(v);
    },
    isChanged(key) {
      const v = this.modelValue[key];
      return v != null && String(v).trim() !== "";
    },
    set(key, value) {
      const next = { ...this.modelValue };
      if (value == null || String(value).trim() === "") delete next[key];
      else next[key] = value;
      this.$emit("update:modelValue", next);
    },
    resetAll() {
      this.$emit("update:modelValue", {});
    },
    // searching or showing only the changed ones opens every group
    isOpen(key) {
      return !!(this.query || this.changedOnly || this.open[key]);
    },
    toggle(key) {
      this.open = { ...this.open, [key]: !this.open[key] };
    },
    /** open an argument's group and put the cursor in it */
    focus(key) {
      const group = this.groups.find(g => g.rows.some(r => r.key === key));
      if (group) this.open = { ...this.open, [group.key]: true };
      this.query = "";
      this.changedOnly = false;
      this.$nextTick(() => {
        const el = document.getElementById("arg-" + key);
        if (!el) return;
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        el.focus();
        if (el.select) el.select();
      });
    }
  }
};
</script>

<style scoped>
.search {
  max-width: 280px;
}
.group {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  margin-bottom: 6px;
  background: #fff;
}
.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: none;
  padding: 6px 10px;
  text-align: left;
}
.rows {
  border-top: 1px solid #f1f3f5;
  padding: 4px 10px 6px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2px 18px;
}
.arg {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 4px;
  border-radius: 6px;
  min-width: 0;
}
.arg.changed {
  background: #e7f1ff;
}
.name {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.name code {
  color: #212529;
  font-size: 0.8rem;
}
.arg.changed .name code {
  color: #0a58ca;
  font-weight: 600;
}
.hint {
  font-size: 0.72rem;
  color: #868e96;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.value {
  display: flex;
  align-items: center;
  flex: none;
  width: 150px;
}
.value .form-control,
.value .form-select {
  font-family: Menlo, Consolas, monospace;
  font-size: 0.8rem;
}
.reset {
  padding: 0 0 0 4px;
  color: #6c757d;
}
@media (max-width: 575.98px) {
  .rows {
    grid-template-columns: 1fr;
  }
  .value {
    width: 130px;
  }
}
</style>
