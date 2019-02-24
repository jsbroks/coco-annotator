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
      visibility: 2,
      label: -1,
      visibilityOptions: {
        0: "NOT LABELLED",
        1: "LABELED NOT VISIBLE",
        2: "LABELED VISIBLE"
      }
    };
  },
  watch: {
    notUsedLabels(notUsedLabels) {
      if (!notUsedLabels) return;
      let values = Object.keys(notUsedLabels);

      if (values.length !== 0) {
        this.label = values[0];
      }
    },
    label(label) {
      if (!this.currentAnnotation) return;
      this.currentAnnotation.keypoint.next.label = label;
    },
    visibility(visibility) {
      if (!this.currentAnnotation) return;
      this.currentAnnotation.keypoint.next.visibility = visibility;
    }
  },
  computed: {
    notUsedLabels() {
      if (!this.currentAnnotation) return {};
      return this.currentAnnotation.notUsedKeypointLabels;
    }
  }
};
</script>
