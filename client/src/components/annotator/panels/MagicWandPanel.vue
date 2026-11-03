<template>
  <div v-show="magicwand.isActive">
    <PanelInputNumber
      :name="$t('magicWandPanel.threshold')"
      min="0"
      max="1000"
      step="5"
      v-model:value="magicwand.wand.threshold"
    />
    <PanelInputNumber
      :name="$t('magicWandPanel.blur')"
      min="0"
      max="1000"
      step="5"
      v-model:value="magicwand.wand.blur"
    />
  </div>
</template>

<script>
import PanelInputNumber from "@/components/PanelInputNumber.vue";

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
