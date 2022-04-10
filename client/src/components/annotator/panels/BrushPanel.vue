<template>
  <div v-show="brush.isActive">
    <PanelInputNumber
      name="Radius"
      min="0"
      max="1000"
      step="5"
      v-model="brush.brush.pathOptions.radius"
    />
    <PanelInputString
      name="Stroke Color"
      v-model="brush.brush.pathOptions.strokeColor"
    />
        <PanelInputNumber
      name="Maximum Error"
      min="0"
      max="5"
      step="0.1"
      v-model="brush.brush.simplify"
    />
  </div>
</template>

<script>
import PanelInputString from "@/components/PanelInputString";
import PanelInputNumber from "@/components/PanelInputNumber";

export default {
  name: "BrushPanel",
  components: { PanelInputString, PanelInputNumber },
  props: {
    brush: {
      type: Object,
      required: true
    }
  }
};
</script>
