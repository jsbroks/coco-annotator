<template>
  <div v-show="select.isActive">
    <PanelToggle :name="$t('selectPanel.showHoverText')" v-model:value="select.hover.showText" />
  </div>
</template>

<script>
import PanelToggle from "@/components/PanelToggle.vue";

export default {
  name: "SelectPanel",
  components: { PanelToggle },
  props: {
    select: {
      type: Object,
      required: true
    }
  }
};
</script>
