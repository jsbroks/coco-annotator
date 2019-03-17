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
import PanelButton from "@/components/PanelButton";
import PanelToggle from "@/components/PanelToggle";
import PanelInputString from "@/components/PanelInputString";
import PanelInputNumber from "@/components/PanelInputNumber";

export default {
  name: "DEXTRPanel",
  components: { PanelButton, PanelToggle, PanelInputString, PanelInputNumber },
  props: {
    dextr: {
      type: Object,
      required: true
    }
  }
};
</script>
