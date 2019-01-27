<template>
  <div>
    <i
      class="fa fa-plus"
      style="float: right; margin: 0 4px; color: green"
      @click="createMetadata"
    />

    <p class="title" style="margin: 0">{{ title }}</p>

    <div class="row">
      <div class="col-sm">
        <p class="subtitle">{{ keyTitle }}</p>
      </div>
      <div class="col-sm">
        <p class="subtitle">{{ valueTitle }}</p>
      </div>
    </div>

    <ul class="list-group" style="height: 50%;">
      <li v-if="metadataList.length == 0" class="list-group-item meta-item">
        <i class="subtitle">No items in metadata.</i>
      </li>
      <li
        v-for="(object, index) in metadataList"
        :key="index"
        class="list-group-item meta-item"
      >
        <div class="row" style="cell">
          <div class="col-sm">
            <input
              v-model="object.key"
              type="text"
              class="meta-input"
              :placeholder="keyTitle"
            />
          </div>

          <div class="col-sm">
            <input
              v-model="object.value"
              type="text"
              class="meta-input"
              :placeholder="valueTitle"
            />
          </div>
        </div>
      </li>
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
      default: "Keys"
    },
    valueTitle: {
      type: String,
      default: "Values"
    },
    exclude: {
      type: String,
      default: ""
    }
  },
  data() {
    return {
      metadataList: []
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
    }
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
  height: 30px;
  border: none;
}

.subtitle {
  margin: 0;
  font-size: 10px;
}
</style>
