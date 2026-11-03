<template>
  <div v-show="polygon.isActive">
    <PanelButton :name="$t('polygonPanel.closePolygon')" @click="polygon.complete" />
    <PanelButton :name="$t('polygonPanel.deletePolygon')" @click="polygon.deletePolygon" />
    <PanelToggle :name="$t('polygonPanel.guidance')" v-model:value="polygon.polygon.guidance" />
    <PanelToggle :name="$t('polygonPanel.autoSelectColor')" v-model:value="polygon.color.auto" />
    <PanelToggle
      v-show="polygon.color.auto"
      :name="$t('polygonPanel.onlyBlackOrWhite')"
      v-model:value="polygon.color.blackOrWhite"
    />
    <PanelInputString
      :name="$t('polygonPanel.strokeColor')"
      v-model:value="polygon.polygon.pathOptions.strokeColor"
    />
    <PanelInputNumber
      :name="$t('polygonPanel.autoCompleteDistance')"
      min="0"
      max="1000"
      step="5"
      v-model:value="polygon.polygon.completeDistance"
    />
    <PanelInputNumber
      :name="$t('polygonPanel.minDistance')"
      min="0"
      max="500"
      step="2"
      v-model:value="polygon.polygon.minDistance"
    />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton.vue";
import PanelToggle from "@/components/PanelToggle.vue";
import PanelInputString from "@/components/PanelInputString.vue";
import PanelInputNumber from "@/components/PanelInputNumber.vue";

export default {
  name: "PolygonPanel",
  components: { PanelButton, PanelToggle, PanelInputString, PanelInputNumber },
  props: {
    polygon: {
      type: Object,
      required: true
    }
  }
};
</script>
