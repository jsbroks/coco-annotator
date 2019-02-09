<template>
  <div v-show="select.isActive">
    <PanelToggle name="Show Hover Text" v-model="select.hover.showText" />
  </div>
</template>

<script>
import PanelToggle from "@/components/PanelToggle";

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
