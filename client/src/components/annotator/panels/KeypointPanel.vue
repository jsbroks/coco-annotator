<template>
  <div v-show="keypoint.isActive">
    <PanelText name="Settings for next Keypoint" />
    <div class="input-group tool-input-group">
      <div class="input-group-prepend tool-option-pre">
        <span class="input-group-text tool-option-font">Label</span>
      </div>
      <div class="form-control tool-option-input text-left">
        {{ keypointLabel }}
      </div>
    </div>
    <PanelInputDropdown name="Visibility" v-model="visibility" :values="visibilityOptions" />
  </div>
</template>
<script>
import PanelText from "@/components/PanelText";
import PanelInputDropdown from "@/components/PanelInputDropdown";
import { VisibilityOptions } from "@/libs/keypoints";
export default {
  name: "KeypointPanel",
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
      visibilityOptions: VisibilityOptions,
    };
  },
  computed: {
    keypointLabel() {
      if (!this.currentAnnotation) return {};
      let labelIndex = this.currentAnnotation.keypoint.next.label;
      let labels = this.currentAnnotation.notUsedKeypointLabels;
      let labelKeys = Object.keys(labels);
      if ((labelIndex < 0 || labelIndex > labels) && labelKeys.length > 0) {
        return labels[labelKeys[0]];
      }
      return labels[labelIndex];
    }
  }
};
</script>
<style scoped>
.tool-input-group {
  padding-top: 3px;
}
.tool-option-pre {
  background-color: #383c4a;
}
.tool-option-font {
  border-color: #4b5162;
  background-color: #383c4a;
  color: white;
  font-size: 12px;
  height: 20px;
}
.tool-option-input {
  display: table-cell;
  border-color: #4b5162;
  color: white;
  padding: 0 0 0 3px;
  background-color: #383c4a;
  font-size: 12px;
  height: 20px;
}
</style>