<template>
  <ol class="wizard-steps">
    <li
      v-for="(label, i) in labels"
      :key="label"
      :class="{ active: current === i + 1, done: current > i + 1, disabled: !canGo(i + 1) }"
      @click="canGo(i + 1) && $emit('go', i + 1)"
    >
      <span class="step-dot">
        <i v-if="current > i + 1" class="fa fa-check" />
        <template v-else>{{ i + 1 }}</template>
      </span>
      <span class="step-name">{{ label }}</span>
    </li>
  </ol>
</template>

<script>
/** Numbered step indicator for dialogs; steps are clickable when ``canGo(step)``. */
export default {
  name: "WizardSteps",
  props: {
    labels: { type: Array, required: true },
    current: { type: Number, required: true },
    canGo: { type: Function, default: () => true }
  },
  emits: ["go"]
};
</script>

<style scoped>
.wizard-steps {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}
.wizard-steps li {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  position: relative;
  cursor: pointer;
  color: #6c757d;
  font-size: 0.85rem;
}
.wizard-steps li.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.wizard-steps li:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 15px;
  left: calc(50% + 20px);
  right: calc(-50% + 20px);
  height: 2px;
  background: #dee2e6;
}
.wizard-steps li.done:not(:last-child)::after {
  background: #198754;
}
.step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #ced4da;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
.wizard-steps li.active {
  color: #0d6efd;
  font-weight: 600;
}
.wizard-steps li.active .step-dot {
  border-color: #0d6efd;
  background: #0d6efd;
  color: #fff;
}
.wizard-steps li.done .step-dot {
  border-color: #198754;
  background: #198754;
  color: #fff;
}
</style>
