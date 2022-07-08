<template>
  <div>
    <i
      class="fa fa-plus"
      style="float: right; margin: 5px 5px 0 -5px; color: green; cursor: pointer;"
      @click="createMetadata"
    />

    <p class="title mb-2">{{ title }}</p>

    <!--
    <div class="row">
      <div class="col-sm">
        <p class="subtitle">{{ keyTitle }}</p>
      </div>
      <div class="col-sm">
        <p class="subtitle">{{ valueTitle }}</p>
      </div>
    </div>
    -->

    <ul class="list-group" style="height: 50%;">
      <li v-if="metadataList.length == 0" class="list-group-item meta-item">
        <i class="subtitle">{{ emptyMessage }}</i>
      </li>
      <li
        v-for="(object, index) in metadataList"
        :key="index"
        class="list-group-item meta-item"
      >
        <div class="row d-flex justify-content-between" style="cell">
          <div class="col-xs">
            <input
              v-model="object.key"
              type="text"
              class="meta-input"
              :placeholder="keyTitle"
              @input="validateKeys()"
            />
          </div>

          <div class="col-xs">
            <input
              v-model="object.value"
              type="text"
              class="meta-input"
              :placeholder="valueTitle"
            />
          </div>

          <div class="col-xs d-flex align-items-center">
            <i
              class="fa fa-minus"
              style="color:red; cursor: pointer"
              @click="deleteMetadata(index)"
            />
          </div>
        </div>

        
      </li>

      <div :v-show="errorMessage" class="text-danger small">
        {{ errorMessage }}
      </div>
    </ul>
  </div>
</template>

<script>
export default {
  name: "Metadata",
  props: {
    metadata: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: "Metadata"
    },
    keyTitle: {
      type: String,
      default: "Key"
    },
    valueTitle: {
      type: String,
      default: "Value"
    },
    exclude: {
      type: String,
      default: ""
    },
    emptyMessage: {
      type: String,
      default: "No items in metadata"
    }
  },
  data() {
    return {
      metadataList: [],
      errorMessage: null, 
    };
  },
  methods: {
    export() {
      let metadata = {};

      this.metadataList.forEach(object => {
        if (object.key.length > 0) {
          if (!isNaN(object.value))
            metadata[object.key] = parseInt(object.value);
          else if (
            object.value.toLowerCase() === "true" ||
            object.value.toLowerCase() === "false"
          )
            metadata[object.key] = object.value.toLowerCase() === "true";
          else metadata[object.key] = object.value;
        }
      });

      return metadata;
    },
    createMetadata() {
      this.metadataList.push({ key: "", value: "" });
    },
    deleteMetadata(index) {
      delete this.metadataList[index];
      this.metadataList = this.metadataList.filter(metadata => metadata);
      this.validateKeys();
    },
    clearEmptyItems() {
      this.metadataList = this.metadataList.filter((metadata) => {
        return metadata.key || metadata.value;
      })
    },
    loadMetadata() {
      if (this.metadata != null) {
        for (var key in this.metadata) {
          if (!this.metadata.hasOwnProperty(key)) continue;
          if (key === this.exclude) continue;

          let value = this.metadata[key];

          if (value == null) value = "";
          else value = value.toString();

          this.metadataList.push({ key: key, value: value });
        }
      }
    },
    validateKeys() {
      const keys = this.metadataList.map(metadata => metadata.key).filter(key => key.length);
      const uniqueKeys = [...new Set(keys)];
      
      this.errorMessage = keys.length !== uniqueKeys.length
        ? "Keys must be unique"
        : null;

     this.$emit("error", !!this.errorMessage);
    },
  },
  watch: {
    metadata() {
      this.loadMetadata();
    }
  },
  created() {
    this.loadMetadata();
  }
};
</script>

<style scoped>
.meta-input {
  padding: 3px;
  background-color: inherit;
  width: 100%;
  height: 100%;
  border: none;
}

.meta-item {
  background-color: inherit;
  padding-top: 2px !important;
  padding-bottom: 2px !important;
  border: none;
}

.subtitle {
  margin: 0;
  font-size: 10px;
}
</style>
