<template>
  <div v-show="polygon.isActive">
    <PanelButton name="Close Polygon" @click="polygon.complete" />
    <PanelButton name="Delete Polygon" @click="polygon.deletePolygon" />
    <PanelToggle name="Guidance" v-model="polygon.polygon.guidance" />
    <PanelToggle name="Auto Select Color" v-model="polygon.color.auto" />
    <PanelToggle
      v-show="polygon.color.auto"
      name="Only Black or White"
      v-model="polygon.color.blackOrWhite"
    />
    <PanelInputString
      name="Stroke Color"
      v-model="polygon.polygon.pathOptions.strokeColor"
    />
    <PanelInputNumber
      name="Auto Complete Distance"
      min="0"
      max="1000"
      step="5"
      v-model="polygon.polygon.completeDistance"
    />
    <PanelInputNumber
      name="Min Distance"
      min="0"
      max="500"
      step="2"
      v-model="polygon.polygon.minDistance"
    />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton";
import PanelToggle from "@/components/PanelToggle";
import PanelInputString from "@/components/PanelInputString";
import PanelInputNumber from "@/components/PanelInputNumber";

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
