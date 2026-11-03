<template>
  <!-- compact: a select (for small dialogs); otherwise cards with a description -->
  <select v-if="compact" class="form-select" :value="modelValue" :disabled="disabled" @change="$emit('update:modelValue', $event.target.value)">
    <option v-for="t in TASKS" :key="t" :value="t">{{ $t('datasetTask.' + (t || 'none') + '.name') }}</option>
  </select>
  <div v-else class="row g-2">
    <div v-for="t in TASKS" :key="t" class="col-6 col-md-4">
      <label class="task-card" :class="{ selected: modelValue === t, disabled }">
        <input
          type="radio"
          class="d-none"
          :name="name"
          :value="t"
          :checked="modelValue === t"
          :disabled="disabled"
          @change="$emit('update:modelValue', t)"
        />
        <span class="d-flex align-items-center gap-2">
          <i class="fa fa-fw" :class="ICONS[t]" :style="t === 'obb' ? { transform: 'rotate(-30deg)' } : null" />
          <span class="fw-semibold">{{ $t('datasetTask.' + (t || 'none') + '.name') }}</span>
        </span>
        <span class="small text-muted">{{ $t('datasetTask.' + (t || 'none') + '.desc') }}</span>
      </label>
    </div>
  </div>
</template>

<script>
export const TASKS = ["", "detect", "segment", "obb", "pose", "classify", "semantic"];

/** The drawing tool that fits each task (annotator default) */
export const TASK_TOOLS = {
  detect: "BBox",
  segment: "Polygon",
  obb: "Rotated BBox",
  pose: "Keypoints",
  semantic: "Polygon"
};

export const TASK_ICONS = {
  "": "fa-th-large",
  detect: "fa-square-o",
  segment: "fa-pencil",
  obb: "fa-square-o", // tilted, like the rotated box tool
  pose: "fa-child",
  classify: "fa-tags",
  semantic: "fa-paint-brush"
};

export default {
  name: "TaskPicker",
  props: {
    modelValue: { type: String, default: "" },
    compact: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    name: { type: String, default: "datasetTask" }
  },
  emits: ["update:modelValue"],
  data() {
    return { TASKS, ICONS: TASK_ICONS };
  }
};
</script>

<style scoped>
.task-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  height: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  cursor: pointer;
  margin: 0;
  text-align: left;
}
.task-card:hover {
  border-color: #86b7fe;
}
.task-card.selected {
  border-color: #0d6efd;
  box-shadow: 0 0 0 1px #0d6efd;
  background: rgba(13, 110, 253, 0.05);
}
.task-card.disabled {
  cursor: default;
  opacity: 0.7;
}
</style>
