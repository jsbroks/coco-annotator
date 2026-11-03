<template>
  <div class="tool-option-input tool-option-font">
    <p style="margin: 0 0 2px 0">{{ name }}</p>
  </div>
</template>

<script>
export default {
  name: "PanelButton",
  props: {
    name: {
      type: String,
      required: true
    }
  }
};
</script>

<style scoped>
.tool-option-font {
  border-color: #4b5162;
  background-color: #383c4a;
  color: white;
  font-size: 12px;
  min-height: 20px;
  padding: 2px 4px 0 4px;
}
</style>
