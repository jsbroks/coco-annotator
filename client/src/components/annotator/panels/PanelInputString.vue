<template>
  <div class="input-group tool-input-group">
    <div class="input-group-prepend tool-option-pre">
      <span class="input-group-text tool-option-font">{{ name }}</span>
    </div>
    <input v-model="localValue" class="form-control tool-option-input">
  </div>
</template>

<script>
export default {
  name: "PanelInputString",
  model: {
    prop: "value",
    event: "update"
  },
  props: {
    name: {
      type: String,
      required: true
    },
    value: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      localValue: this.value
    };
  },
  watch: {
    localValue() {
      this.$emit("update", this.localValue);
    },
    value(newValue) {
      this.localValue = newValue;
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
  height: 20px;
}
.tool-option-font {
  border-color: #4b5162;
  background-color: #383c4a;
  color: white;
  font-size: 12px;
}
.tool-option-input {
  border-color: #4b5162;
  color: white;
  padding: 0 0 0 3px;
  background-color: #383c4a;
  height: 20px;
  font-size: 12px;
  width: 100%;
}
</style>
