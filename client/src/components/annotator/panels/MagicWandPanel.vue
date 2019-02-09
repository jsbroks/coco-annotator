<template>
  <div v-show="magicwand.isActive">
    <PanelInputNumber
      name="Threshold"
      min="0"
      max="1000"
      step="5"
      v-model="magicwand.wand.threshold"
    />
    <PanelInputNumber
      name="Blur"
      min="0"
      max="1000"
      step="5"
      v-model="magicwand.wand.blur"
    />
  </div>
</template>

<script>
import PanelInputNumber from "@/components/PanelInputNumber";

export default {
  name: "MagicWandPanel",
  components: { PanelInputNumber },
  props: {
    magicwand: {
      type: Object,
      required: true
    }
  }
};
</script>
