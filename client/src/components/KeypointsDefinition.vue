<template>
  <div class="kp-def">
    <div class="kp-head">
      <span class="title">{{ title || $t('keypointsDefinition.title') }}</span>
      <span v-if="keypoints.length" class="kp-count">{{ keypoints.length }}</span>
      <span v-if="keypoints.length" class="text-muted small d-none d-sm-inline">
        {{ keyTitle || $t('keypointsDefinition.label') }} → {{ valueTitle || $t('keypointsDefinition.connectsTo') }}
      </span>
      <button type="button" class="btn btn-sm btn-success ms-auto kp-add" @click="addKeypoint">
        <i class="fa fa-plus" /> {{ $t('keypointsDefinition.add') }}
      </button>
    </div>

    <div class="kp-layout" :class="{ empty: !keypoints.length }">
      <div ref="grid" class="kp-grid" :style="{ '--kp-label-w': labelWidth + 'px' }">
        <div v-if="keypoints.length == 0" class="kp-empty">
          <i class="fa fa-street-view" />
          <span>{{ $t('keypointsDefinition.noKeypoints') }}</span>
        </div>
        <div
          v-for="(object, index) in keypoints"
          :key="index"
          class="kp-row"
          :class="{ hl: hover === index, invalid: object.label_error.length !== 0 }"
          :style="{ '--kp': object.color || '#adb5bd' }"
          @mouseenter="hover = index"
          @mouseleave="hover = null"
        >
          <span class="kp-index">{{ index + 1 }}</span>
          <label class="kp-swatch" :title="$t('keypointsDefinition.color')">
            <input :value="object.color" type="color" @input="colorUpdated(index, $event.target.value)" />
          </label>
          <input
            :value="object.label"
            type="text"
            class="form-control form-control-sm kp-label"
            :class="{ 'is-invalid': object.label_error.length !== 0 }"
            :title="object.label_error || ''"
            :required="object.edges.length !== 0"
            :placeholder="keyTitle || $t('keypointsDefinition.label')"
            @input="keypointLabelUpdated(index, $event.target.value)"
          />
          <TagsInput
            :value="object.edges"
            :placeholder="object.edges.length ? ' ' : $t('keypointsDefinition.addConnectedLabel')"
            class="kp-edges"
            :class="{ none: !object.edges.length }"
            @click="focusEdges"
            :elementId="`index${index}`"
            :existing-tags="otherKeypointLabels(object.label)"
            :onlyExistingTags="true"
            :typeahead="true"
            :typeahead-activation-threshold="0"
            :badge-style="edgeStyle"
            @update:value="keypointEdgesUpdated(index, $event)"
          ></TagsInput>
          <button
            type="button"
            class="btn btn-sm btn-link kp-remove"
            :title="$t('keypointsDefinition.remove')"
            :aria-label="$t('keypointsDefinition.remove')"
            @click="removeKeypoint(index)"
          >
            <i class="fa fa-trash" />
          </button>
        </div>
      </div>

      <KeypointsPreview
        v-if="keypoints.length"
        class="kp-side"
        :keypoints="keypoints"
        :highlight="hover"
        @hover="hover = $event"
        @toggle="toggleEdge"
      />
    </div>
  </div>
</template>

<script>
import TagsInput from "@/components/TagsInput.vue";
import KeypointsPreview from "@/components/KeypointsPreview.vue";

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
  emits: ["initialized", "update:value", "rows"],
  components: { TagsInput, KeypointsPreview },
  props: {
    value: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: ""
    },
    keyTitle: {
      type: String,
      default: ""
    },
    valueTitle: {
      type: String,
      default: ""
    },
    exclude: {
      type: String,
      default: ""
    }
  },
  computed: {
    // wide enough for the longest name (within reason)
    labelWidth() {
      const longest = this.keypoints.reduce((m, kp) => Math.max(m, (kp.label || "").length), 0);
      return Math.max(112, Math.min(180, Math.round(longest * 7.6 + 22)));
    },
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
      // a keypoint pointed at, in the list or the preview
      hover: null
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
        let label1 = edge[1] - 1;
        keypoints[label0].edges.push(this.value.labels[label1]);
        keypoints[label1].edges.push(this.value.labels[label0]);
      });

      return keypoints;
    },
    /** connect two keypoints, or take their connection away (the preview) */
    toggleEdge(a, b) {
      const from = this.keypoints[a];
      const to = this.keypoints[b];
      if (!from || !to || !from.label || !to.label) return;
      const edges = from.edges.includes(to.label) ? from.edges.filter(e => e !== to.label) : [...from.edges, to.label];
      this.keypointEdgesUpdated(a, edges);
    },
    /** a click anywhere in the connections field is for typing in it */
    focusEdges(e) {
      const input = e.currentTarget && e.currentTarget.querySelector("input[type=text]");
      if (input && e.target !== input && !e.target.closest(".tags-input-remove, .tags-input-typeahead")) input.focus();
    },
    /** a connection's tag in the colour of the keypoint it goes to */
    edgeStyle(label) {
      const kp = this.keypoints.find(k => k.label === label);
      const c = kp && /^#[0-9a-f]{6}$/i.test(kp.color) ? kp.color : "#adb5bd";
      const r = parseInt(c.slice(1, 3), 16);
      const g = parseInt(c.slice(3, 5), 16);
      const b = parseInt(c.slice(5, 7), 16);
      return { background: `rgba(${r}, ${g}, ${b}, 0.14)`, boxShadow: `inset 3px 0 0 ${c}` };
    },
    /** a keypoint goes, with every connection to it */
    removeKeypoint(index) {
      const gone = this.keypoints[index];
      // keypoints are stored by position: one taken from the middle shifts
      // the ones after it in shapes already annotated
      if (gone && gone.label && index < this.keypoints.length - 1 && !confirm(this.$t("keypointsDefinition.removeConfirm", { name: gone.label }))) {
        return;
      }
      this.keypoints.splice(index, 1);
      if (gone && gone.label) {
        this.keypoints.forEach(kp => {
          kp.edges = kp.edges.filter(e => e !== gone.label);
        });
      }
      this.hiddenValue = this.propFomKeypoints();
      this.$emit("update:value", this.hiddenValue);
    },
    /** a new keypoint, ready to type its name */
    addKeypoint() {
      this.createKeypoints();
      this.$nextTick(() => {
        const grid = this.$refs.grid;
        const inputs = grid ? grid.querySelectorAll(".kp-label") : [];
        const last = inputs[inputs.length - 1];
        if (last) {
          last.scrollIntoView({ block: "nearest" });
          last.focus();
        }
      });
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
      this.$emit("update:value", this.hiddenValue);
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
              current_kp.label_error = this.$t("keypointsDefinition.duplicateLabel");
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
        current_kp.label_error = this.$t("keypointsDefinition.labelRequired");
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
        this.$emit("update:value", this.hiddenValue);
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
      if (!Array.isArray(edges)) return;
      // the tags field hands over its own list (and keeps changing it): a copy
      edges = [...edges];
      const before = this.keypoints[index] ? this.keypoints[index].edges : [];
      if (before.length === edges.length && before.every((e, i) => e === edges[i])) return;
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
      this.$emit("update:value", this.hiddenValue);
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
    // how many keypoints are listed (the dialog widens for several)
    "keypoints.length": {
      immediate: true,
      handler(n) {
        this.$emit("rows", n);
      }
    },
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
.kp-def {
  container-type: inline-size;
}
.kp-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.kp-head .title {
  font-weight: 600;
}
.kp-count {
  font-size: 0.72rem;
  font-weight: 600;
  color: #495057;
  background: #e9ecef;
  border-radius: 10px;
  padding: 1px 8px;
}
.kp-add {
  padding: 2px 10px;
  border-radius: 14px;
}
.kp-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
}
/* the preview beside the list when there is room */
@container (min-width: 700px) {
  .kp-layout:not(.empty) {
    grid-template-columns: minmax(0, 1fr) 300px;
  }
  .kp-side {
    position: sticky;
    top: 0;
    align-self: start;
  }
}
/* several keypoints a row, so a long list fits without scrolling the page */
.kp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(calc(var(--kp-label-w) + 220px), 1fr));
  gap: 6px 10px;
  align-content: start;
}
.kp-empty {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border: 1px dashed #ced4da;
  border-radius: 10px;
  color: #868e96;
  font-size: 0.85rem;
}
.kp-empty .fa {
  font-size: 1.4rem;
  color: #ced4da;
}
.kp-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
  padding: 5px 4px 5px 8px;
  border: 1px solid #e9ecef;
  border-left: 4px solid var(--kp);
  border-radius: 8px;
  background: #fff;
  transition: box-shadow 0.15s, border-color 0.15s, background 0.15s;
}
.kp-row:hover,
.kp-row.hl {
  background: #f8fbff;
  border-color: #cfe2ff;
  border-left-color: var(--kp);
  box-shadow: 0 1px 4px rgba(13, 110, 253, 0.12);
}
.kp-row.invalid {
  border-color: #f1aeb5;
  border-left-color: var(--kp);
}
.kp-index {
  flex: none;
  width: 1.5em;
  padding-top: 6px;
  text-align: right;
  font-size: 0.72rem;
  font-weight: 600;
  color: #adb5bd;
  font-variant-numeric: tabular-nums;
}
.kp-swatch {
  flex: none;
  position: relative;
  width: 22px;
  height: 22px;
  margin: 4px 0 0;
  border-radius: 50%;
  background: var(--kp);
  box-shadow: 0 0 0 2px #fff, 0 0 0 3px #dee2e6;
  cursor: pointer;
  overflow: hidden;
}
.kp-swatch input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.kp-label {
  flex: none;
  width: var(--kp-label-w);
  font-weight: 500;
}
.kp-edges {
  flex: 1 1 auto;
  min-width: 0;
}
.kp-remove {
  flex: none;
  padding: 4px 4px 0;
  color: #adb5bd;
  opacity: 0.6;
}
.kp-row:hover .kp-remove,
.kp-remove:focus {
  opacity: 1;
  color: #dc3545;
}
/* the connections field: one line while it fits */
.kp-edges :deep(.tags-input) {
  padding: 2px 4px;
  min-height: 31px;
  row-gap: 3px;
}
/* the typing spot: only a sliver after the tags (no empty line under them)
   until it is used */
.kp-edges {
  cursor: text;
}
.kp-edges :deep(.tags-input input[type="text"]) {
  flex: 1 1 0;
  min-width: 0;
  width: 0;
  font-size: 0.8rem;
  padding: 2px;
}
.kp-edges :deep(.tags-input input[type="text"]:focus),
.kp-edges.none :deep(.tags-input input[type="text"]) {
  min-width: 90px;
}
.kp-edges :deep(.tags-input-badge) {
  font-size: 0.72rem;
  font-weight: 600;
  margin: 1px 3px 1px 0;
  padding: 0.3em 0.6em 0.3em 0.75em;
}
</style>
