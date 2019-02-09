<template>
  <button
    class="btn btn-outline-light tool-input-button"
    :class="{ active: value }"
    @click="$emit('update', !value)"
  >
    {{ name }}
  </button>
</template>

<script>
export default {
  name: "ToggleButton",
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
      type: Boolean,
      required: true
    }
  }
};
</script>

<style scoped>
.tool-input-button {
  height: 20px;
  border-color: #4b5162;
  padding: 0 0 0 11px;
  font-size: 12px;
  width: 100%;
}

.tool-input-button:hover {
  background-color: transparent;
  color: white;
}
</style>
