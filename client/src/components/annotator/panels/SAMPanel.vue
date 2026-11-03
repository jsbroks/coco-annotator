<template>
  <div v-show="sam.isActive">
    <div class="sam-output" :class="sam.output">
      <label class="d-flex align-items-center gap-2 mb-0">
        <span>{{ $t('sam.outputLabel') }}</span>
        <select v-model="sam.output" class="form-select form-select-sm">
          <option v-for="o in ['outline', 'box', 'rbox']" :key="o" :value="o">{{ $t('sam.output.' + o) }}</option>
        </select>
      </label>
    </div>
    <PanelText :name="sam.statusText" />
    <PanelButton :name="$t('sAMPanel.applyEnter')" @click="sam.apply()" />
    <PanelButton :name="$t('sAMPanel.undoLastPrompt')" @click="sam.undoPoint()" />
    <PanelButton :name="$t('sAMPanel.clearPrompts')" @click="sam.reset()" />
    <PanelToggle :name="$t('sAMPanel.replaceAnnotation')" v-model:value="sam.settings.replace" />
    <PanelInputNumber
      v-if="sam.boxMode"
      :name="$t('sAMPanel.boxPad')"
      min="0"
      max="50"
      step="1"
      v-model:value="sam.settings.obbPad"
    />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton.vue";
import PanelText from "@/components/PanelText.vue";
import PanelToggle from "@/components/PanelToggle.vue";
import PanelInputNumber from "@/components/PanelInputNumber.vue";

export default {
  name: "SAMPanel",
  components: { PanelButton, PanelText, PanelToggle, PanelInputNumber },
  props: {
    sam: {
      type: Object,
      required: true
    }
  }
};
</script>

<style scoped>
.sam-output {
  margin: 4px 6px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}
.sam-output.box,
.sam-output.rbox {
  background: rgba(0, 229, 255, 0.18);
  border: 1px solid #00e5ff;
  color: #9ff3ff;
}
.sam-output.outline {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid #adb5bd;
  color: #e9ecef;
}
.sam-output select {
  flex: 1;
}
</style>
