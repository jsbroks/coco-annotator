<template>
  <div v-show="keypoint.isActive">
    <PanelText name="Settings for next Keypoint" />
    <PanelInputDropdown name="Label" v-model="label" :values="notUsedLabels" />
    <PanelInputDropdown name="Visibility" v-model="visibility" :values="visibilityOptions" />
  </div>
</template>

<script>
import PanelText from "@/components/PanelText";

import PanelInputDropdown from "@/components/PanelInputDropdown";

export default {
  name: "PolygonPanel",
  components: { PanelText, PanelInputDropdown },
  props: {
    keypoint: {
      type: Object,
      required: true
    },
    currentAnnotation: {
      required: true,
      validator: prop => typeof prop === "object" || prop === undefined
    }
  },
  data() {
    return {
      visibility: 0,
      label: -1,
      visibilityOptions: {
        0: "NOT LABELLED",
        1: "LABELED NOT VISIBLE",
        2: "LABELED VISIBLE"
      }
    }
  },
  watch: {
    notUsedLabels(notUsedLabels) {
      if (!notUsedLabels) return;
      let values =  Object.keys(notUsedLabels)
      if (values.length !== 0) {
        this.label = values[0];
      }
    },
    label(label) {
      this.$parent.currentAnnotation.keypoint.next.label = label;
    },
    visibility(visibility) {
      this.$parent.currentAnnotation.keypoint.next.visibility = visibility;
    }
  },
  computed: {
    notUsedLabels() {
      if (!this.currentAnnotation) return { };
      return this.currentAnnotation.notUsedKeypointLabels;
    }
  }
};
</script>
