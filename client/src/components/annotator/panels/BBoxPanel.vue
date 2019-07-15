<template>
  <div v-show="bbox.isActive">
    <PanelButton name="Delete BBox" @click="bbox.deleteBbox" />
    <PanelToggle name="Auto Select Color" v-model="bbox.color.auto" />
    <PanelToggle
      v-show="bbox.color.auto"
      name="Only Black or White"
      v-model="bbox.color.blackOrWhite"
    />
    <PanelInputString
      name="Stroke Color"
      v-model="bbox.polygon.pathOptions.strokeColor"
    />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton";
import PanelToggle from "@/components/PanelToggle";
import PanelInputString from "@/components/PanelInputString";
import PanelInputNumber from "@/components/PanelInputNumber";

export default {
  name: "BBoxPanel",
  components: { PanelButton, PanelToggle, PanelInputString, PanelInputNumber },
  props: {
    bbox: {
      type: Object,
      required: true
    }
  }
};
</script>
