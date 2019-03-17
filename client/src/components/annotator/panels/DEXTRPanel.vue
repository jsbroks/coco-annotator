<template>
  <div v-show="dextr.isActive">
    <PanelInputNumber
      name="Padding"
      min="0"
      max="1000"
      step="2"
      v-model="dextr.settings.padding"
    />
    <PanelInputNumber
      name="Threshold"
      min="0"
      max="100"
      step="5"
      v-model="dextr.settings.threshold"
    />
  </div>
</template>

<script>
import PanelInputNumber from "@/components/PanelInputNumber";

export default {
  name: "DEXTRPanel",
  components: { PanelInputNumber },
  props: {
    dextr: {
      type: Object,
      required: true
    }
  }
};
</script>
