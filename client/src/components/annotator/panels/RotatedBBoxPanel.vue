<template>
  <div v-show="rbbox.isActive">
    <PanelText :name="rbbox.hint" />
    <PanelText v-if="rbbox.box && !rbbox.drawing" :name="$t('rotatedBBoxPanel.arrowKeysMove1Px')" />
    <PanelButton :name="$t('rotatedBBoxPanel.rotate5')" @click="rbbox.rotateBy(-5)" />
    <PanelButton :name="$t('rotatedBBoxPanel.rotate52')" @click="rbbox.rotateBy(5)" />
    <PanelButton :name="$t('rotatedBBoxPanel.swapHeading90')" @click="rbbox.swapHeading()" />
    <PanelButton :name="$t('rotatedBBoxPanel.fromShape')" @click="rbbox.convertCurrent()" />
    <PanelButton :name="$t('rotatedBBoxPanel.fromAllShapes')" @click="rbbox.convertAll()" />
    <PanelInputNumber
      :name="$t('rotatedBBoxPanel.shiftSnap')"
      min="0"
      max="90"
      step="5"
      v-model:value="rbbox.settings.snap"
    />
    <PanelInputString :name="$t('rotatedBBoxPanel.handleColor')" v-model:value="rbbox.settings.strokeColor" />
  </div>
</template>

<script>
import PanelButton from "@/components/PanelButton.vue";
import PanelText from "@/components/PanelText.vue";
import PanelInputNumber from "@/components/PanelInputNumber.vue";
import PanelInputString from "@/components/PanelInputString.vue";

export default {
  name: "RotatedBBoxPanel",
  components: { PanelButton, PanelText, PanelInputNumber, PanelInputString },
  props: {
    rbbox: {
      type: Object,
      required: true
    }
  }
};
</script>
