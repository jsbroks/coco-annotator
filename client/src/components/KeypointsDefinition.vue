<template>
  <div>
    <i
      class="fa fa-plus"
      style="float: right; margin: 0 4px; color: green"
      @click="createKeypoints"
    />

    <p class="title" style="margin: 0">{{ title }}</p>

    <div class="row">
      <div class="col-sm-5">
        <p class="subtitle">{{ keyTitle }}:</p>
      </div>
      <div class="col-sm-7">
        <p class="subtitle">{{ valueTitle }}:</p>
      </div>
    </div>

    <form>
      <ul class="list-group" style="height: 50%;">
        <li v-if="keypoints.length == 0" class="list-group-item keypoint-item">
          <i class="subtitle">No keypoints.</i>
        </li>
        <li v-for="(object, index) in keypoints" :key="index" class="list-group-item keypoint-item">
          <div class="row form-group" style="cell">
            <!-- :class="{'was-validated': object.label_error.length === 0 }" -->
            <div class="col-sm-5" style="padding-right: 5px;">
              <input
                :value="object.label"
                type="text"
                class="keypoint-input form-control"
                :class="{'is-invalid': object.label_error.length !== 0}"
                :required="object.edges.length !== 0"
                :placeholder="keyTitle"
                @input="keypointLabelUpdated(index, $event.target.value)"
              />
              <div class="invalid-feedback">{{ object.label_error }}</div>
            </div>

            <div class="col-sm-1 keypoint-color">
              <!-- <input v-model="object.color" type="color" class="form-control" /> -->
              <input :value="object.color" @input="colorUpdated(index, $event.target.value)" type="color" class="form-control" />
            </div>

            <div class="col-sm-6" style="padding-left: 5px;">
              <TagsInput
                :value="object.edges"
                placeholder="Add connected label"
                class="keypoint-input"
                :elementId="`index${index}`"
                :existing-tags="otherKeypointLabels(object.label)"
                :onlyExistingTags="true"
                :typeahead="true"
                :typeahead-activation-threshold="0"
                @input="keypointEdgesUpdated(index, $event)"
              ></TagsInput>
            </div>
          </div>
        </li>
      </ul>
    </form>
  </div>
</template>

<script>
import TagsInput from "@/components/TagsInput";

const DISTINCT_COLORS = [
  "#bf5c4d",
  "#d99100",
  "#4d8068",
  "#0d2b80",
  "#9c73bf",
  "#ff1a38",
  "#bf3300",
  "#736322",
  "#33fff1",
  "#3369ff",
  "#9d13bf",
  "#733941",
  "#ffb499",
  "#d0d957",
  "#0b5e73",
  "#0000ff",
  "#730b5e",
  "#ff8533",
  "#518c0e",
  "#82c7d9",
  "#0000d9",
  "#ff1ab3",
  "#733c17",
  "#7cff4d",
  "#1ab3ff",
  "#0000cc",
  "#cc0052",
  "#cc9c66",
  "#8ae6a2",
  "#335280",
  "#0000bf",
  "#e673a1"
];

export default {
  name: "KeypointsDefinition",
  components: { TagsInput },
  props: {
    value: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: "Keypoints"
    },
    keyTitle: {
      type: String,
      default: "Label"
    },
    valueTitle: {
      type: String,
      default: "Connects to"
    },
    exclude: {
      type: String,
      default: ""
    }
  },
  computed: {
    valid() {
      if (!this.isMounted) {
        return false;
      }
      for (let i = 0; i < this.keypoints.length; ++i) {
        if (this.keypoints[i].label_error.length !== 0) {
          return false;
        }
      }
      return true;
    }
  },
  data() {
    return {
      keypoints: [],
      hiddenValue: { edges: [], labels: [], colors: [] },
      isMounted: false,
      nextDistinct: -1,
    };
  },
  created() {
    this.keypoints = this.keypointsFromProp();
    this.$emit("initialized");
  },
  mounted() {
    this.isMounted = true;
  },
  methods: {
    export() {
      let keypoints = [];

      for (let i=0; i < this.value.labels.length; ++i) {
        keypoints.push({
          label: this.value.labels[i],
          edges: [],
          label_error: "",
          color: this.value.colors[i],
        });
      }
      this.value.edges.forEach(edge => {
        let label0 = edge[0] - 1;
        let label1 = edge[0] - 1;
        keypoints[label0].edges.push(this.value.labels[label1]);
        keypoints[label1].edges.push(this.value.labels[label0]);
      });

      return keypoints;
    },
    createKeypoints() {
      this.keypoints.push({
        label: "",
        label_error: "",
        edges: [],
        color: this.nextDistinctColor(),
      });
    },
    keypointsFromProp() {
      let keypoints = [];
      if (
        this.value != null &&
        this.value.labels != null &&
        this.value.labels.length
      ) {
        for (let i=0; i < this.value.labels.length; ++i) {
          let label = this.value.labels[i];
          if (label.length > 0) {
            keypoints.push({
              label,
              label_error: "",
              edges: [],
              color: this.value.colors[i] || "#000",
            });
          }
        }

        this.value.edges.forEach(edge => {
          let label0 = edge[0] - 1;
          let label1 = edge[1] - 1;
          if (label0 < keypoints.length && label1 < keypoints.length) {
            keypoints[label0].edges.push(this.value.labels[label1]);
            keypoints[label1].edges.push(this.value.labels[label0]);
          }
        });
      }
      return keypoints;
    },
    colorUpdated(index, color) {
      this.keypoints[index].color = color;
      this.hiddenValue = this.propFomKeypoints();
      this.$emit("input", this.hiddenValue);
    },
    keypointLabelUpdated(index, label) {
      let current_kp = this.keypoints[index];
      let previous_label = current_kp.label;

      current_kp.label_error = "";
      if (label !== "") {
        for (let i = 0; i < this.keypoints.length; ++i) {
          if (i !== index) {
            let kp = this.keypoints[i];
            if (label === kp.label) {
              current_kp.label_error = "Duplicate keypoint label";
              kp.label_error = current_kp.label_error;
            } else if (
              previous_label === kp.label &&
              kp.label_error.length !== 0
            ) {
              kp.label_error = "";
            }
          }
        }
      } else if (current_kp.edges.length !== 0) {
        current_kp.label_error = "Label is required";
      }

      current_kp.label = label;
      if (current_kp.label_error === "") {
        if (label !== "") {
          for (let i = 0; i < this.keypoints.length; ++i) {
            if (i !== index) {
              let kp = this.keypoints[i];
              kp.edges = kp.edges.map(edge => {
                return edge === previous_label ? label : edge;
              });
            }
          }
        }
        this.hiddenValue = this.propFomKeypoints();
        this.$emit("input", this.hiddenValue);
      } else if (label !== "") {
        for (let i = 0; i < this.keypoints.length; ++i) {
          if (i !== index) {
            let kp = this.keypoints[i];
            kp.edges = kp.edges.filter(edge => {
              return edge != previous_label;
            });
          }
        }
      }
    },
    keypointEdgesUpdated(index, edges) {
      let new_edges = new Set(edges);
      let current_kp = this.keypoints[index];
      // need to update the keypoints on the other end of the edges
      this.keypoints.forEach(kp => {
        if (kp.label !== current_kp.label) {
          // edges go both ways; sync other end
          let kp_edges = new Set(kp.edges);
          if (!new_edges.has(kp.label) && kp_edges.has(current_kp.label)) {
            kp_edges.delete(current_kp.label);
            kp.edges = Array.from(kp_edges);
          } else if (
            new_edges.has(kp.label) &&
            !kp_edges.has(current_kp.label)
          ) {
            kp_edges.add(current_kp.label);
            kp.edges = Array.from(kp_edges);
          }
          if (kp.edges.length === 0 && kp.label.length === 0 && kp.label_error) {
            kp.label_error = "";
          }
        }
      });

      this.keypoints[index].edges = edges;
      this.hiddenValue = this.propFomKeypoints();
      this.$emit("input", this.hiddenValue);
    },
    propFomKeypoints() {
      let edge_labels = {};
      let labels = [];
      let colors = [];
      this.keypoints.forEach(kp => {
        if (kp.label.length > 0) {
          labels.push(kp.label);
          colors.push(kp.color);
        }
      })
      this.keypoints.forEach(kp => {
        kp.edges.forEach(edge => {
          if (edge in edge_labels) {
            edge_labels[edge].add(kp.label);
          } else {
            edge_labels[kp.label] = edge_labels[kp.label] || new Set();
            edge_labels[kp.label].add(edge);
          }
        });
      });
      let edges = [];
      for (const label in edge_labels) {
        let label_index = labels.indexOf(label) + 1;
        edge_labels[label].forEach(edge => {
          let edge_index = labels.indexOf(edge) + 1;
          edges.push([label_index, edge_index]);
        });
      }
      return { labels, edges, colors };
    },
    otherKeypointLabels(current_label) {
      let labels = {};
      if (this.keypoints != null) {
        this.keypoints.forEach(keypoint => {
          if (keypoint.label !== "" && keypoint.label !== current_label) {
            labels[keypoint.label] = keypoint.label;
          }
        });
      }
      return labels;
    },
    clearKeypoints() {
      this.keypoints.splice(0, this.keypoints.length);
    },
    nextDistinctColor() {
      return DISTINCT_COLORS[++this.nextDistinct];
    }
  },
  watch: {
    value() {
      if (this.hiddenValue !== this.value) {
        this.hiddenValue = this.value;
        this.keypoints = this.keypointsFromProp();
      }
    }
  }
};
</script>

<style scoped>
.keypoint-input {
  padding: 3px;
  background-color: inherit;
  width: 100%;
  height: 100%;
  border: none;
}

.keypoint-item {
  background-color: inherit;
  margin-bottom: -20px;
  border: none;
  padding-bottom: 0;
}

.keypoint-color {
  padding-left: 0;
  padding-right: 0;
  line-height: 1.25;
  height: 100%;
  padding-top: 15px;
  padding-bottom: 15px;
}

.keypoint-color input[type="color"] {
  padding: 4px;
}

.subtitle {
  margin: 0;
  font-size: 10px;
}
</style>
