<template>
  <div>
    <i
      class="fa fa-plus"
      style="float: right; margin: 0 4px; color: green"
      @click="createKeypoints"
    />

    <p class="title" style="margin: 0">{{ title }}</p>

    <div class="row">
      <div class="col-sm-4">
        <p class="subtitle">{{ keyTitle }}:</p>
      </div>
      <div class="col-sm-8">
        <p class="subtitle">{{ valueTitle }}:</p>
      </div>
    </div>

    <ul class="list-group" style="height: 50%;">
      <li v-if="keypoints.length == 0" class="list-group-item keypoint-item">
        <i class="subtitle">No keypoints.</i>
      </li>
      <li v-for="(object, index) in keypoints" :key="index" class="list-group-item keypoint-item">
        <div class="row" style="cell">
          <div class="col-sm-4">
            <input
              :value="object.label"
              type="text"
              class="keypoint-input"
              :placeholder="keyTitle"
              @input="keypointLabelUpdated(index, $event.target.value)"
            />
          </div>

          <div class="col-sm-8">
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
  </div>
</template>

<script>
import TagsInput from "@/components/TagsInput";

export default {
  name: "Keypoints",
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
  computed: {},
  data() {
    return {
      keypoints: [],
      hiddenValue: { edges: [], labels: [] }
    };
  },
  created() {
    this.keypoints = this.keypointsFromProp();
    this.$emit("initialized");
  },
  methods: {
    export() {
      let keypoints = [];

      this.value.labels.forEach(label => {
        keypoints.push({ label, edges: [] });
      });
      this.value.edges.forEach(edge => {
        let label0 = edge[0] - 1;
        let label1 = edge[0] - 1;
        keypoints[label0].edges.push(this.value.labels[label1]);
        keypoints[label1].edges.push(this.value.labels[label0]);
      });

      return keypoints;
    },
    createKeypoints() {
      this.keypoints.push({ label: "", edges: [] });
    },
    keypointsFromProp() {
      let keypoints = [];
      if (
        this.value != null &&
        this.value.labels != null &&
        this.value.labels.length
      ) {
        keypoints = this.value.labels.map(k => {
          return { label: k, edges: [] };
        });

        this.value.edges.forEach(edge => {
          let label0 = edge[0] - 1;
          let label1 = edge[1] - 1;
          keypoints[label0].edges.push(this.value.labels[label1]);
          keypoints[label1].edges.push(this.value.labels[label0]);
        });
      }
      return keypoints;
    },
    keypointLabelUpdated(index, label) {
      this.keypoints[index].label = label;
      this.hiddenValue = this.propFomKeypoints();
      this.$emit("input", this.hiddenValue);
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
            kp.edges = [...kp_edges];
          } else if (new_edges.has(kp.label) && !kp_edges.has(current_kp.label)) {
            kp_edges.add(current_kp.label);
            kp.edges = [...kp_edges];
          }
        }
      });

      this.keypoints[index].edges = edges;
      this.hiddenValue = this.propFomKeypoints();
      this.$emit("input", this.hiddenValue);
    },
    propFomKeypoints() {
      let labels = [];
      let edge_labels = {};
      this.keypoints.forEach(kp => {
        labels.push(kp.label);
      });
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
      return { labels, edges };
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
}

.subtitle {
  margin: 0;
  font-size: 10px;
}
</style>
