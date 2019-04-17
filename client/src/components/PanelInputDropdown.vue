<template>
  <div class="input-group tool-input-group">
    <div class="input-group-prepend tool-option-pre">
      <span class="input-group-text tool-option-font">{{ name }}</span>
    </div>
    <select v-model="localValue" class="form-control tool-option-input">
      <option :key="option.key" v-for="option in options" :value="option.key" :selected="option.selected">{{ option.value }}</option>
    </select>
  </div>
</template>

<script>
export default {
  name: "PanelInputDropdown",
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
      type: [Number, Array, Object, String],
      required: true
    },
    values: {
      type: Object,
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
  },
  computed: {
    options() {
      let array = [];
      Object.keys(this.values).forEach(k => {
        array.push({
          key: k,
          value: this.values[k],
          selected: this.value == k
        });
      });
      return array;
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
