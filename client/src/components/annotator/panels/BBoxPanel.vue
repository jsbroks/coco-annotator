<template>
  <div v-show="bbox.isActive">
    <PanelButton :name="$t('bBoxPanel.deleteBbox')" @click="bbox.deleteBbox" />
    <PanelToggle :name="$t('bBoxPanel.autoSelectColor')" v-model:value="bbox.color.auto" />
    <PanelToggle
      v-show="bbox.color.auto"
      :name="$t('bBoxPanel.onlyBlackOrWhite')"
      v-model:value="bbox.color.blackOrWhite"
    />
    <PanelInputString
      :name="$t('bBoxPanel.strokeColor')"
      v-model:value="bbox.polygon.pathOptions.strokeColor"
    />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton.vue";
import PanelToggle from "@/components/PanelToggle.vue";
import PanelInputString from "@/components/PanelInputString.vue";

export default {
  name: "BBoxPanel",
  components: { PanelButton, PanelToggle, PanelInputString },
  props: {
    bbox: {
      type: Object,
      required: true
    }
  }
};
</script>
