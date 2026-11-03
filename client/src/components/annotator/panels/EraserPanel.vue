<template>
  <div v-show="eraser.isActive">
    <PanelInputNumber
      :name="$t('eraserPanel.radius')"
      min="0"
      max="1000"
      step="5"
      v-model:value="eraser.eraser.pathOptions.radius"
    />
    <PanelInputString
      :name="$t('eraserPanel.strokeColor')"
      v-model:value="eraser.eraser.pathOptions.strokeColor"
    />
  </div>
</template>

<script>
import PanelInputString from "@/components/PanelInputString.vue";
import PanelInputNumber from "@/components/PanelInputNumber.vue";

export default {
  name: "EraserPanel",
  components: { PanelInputString, PanelInputNumber },
  props: {
    eraser: {
      type: Object,
      required: true
    }
  }
};
</script>
