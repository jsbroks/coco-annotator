<template>
  <div class="parent-input">
    <!-- existing parents as a tree: click to pick / unpick -->
    <div v-if="options.length" class="parent-options mb-1">
      <button
        v-for="p in shownOptions"
        :key="p"
        type="button"
        class="opt"
        :class="{ picked: isPicked(p) }"
        :style="{ paddingLeft: 6 + (filtering ? 0 : depth(p) * 16) + 'px' }"
        :aria-pressed="isPicked(p)"
        :title="label(p)"
        @click="toggle(p)"
      >
        <i class="fa fa-fw" :class="isPicked(p) ? 'fa-check-square' : 'fa-square-o'" />
        <i class="fa fa-folder folder" />
        <span class="text-truncate">{{ filtering ? label(p) : pathName(p) }}</span>
      </button>
      <span v-if="!shownOptions.length" class="small text-muted px-2">{{ $t('parents.noMatch') }}</span>
    </div>

    <!-- filter the list, or type a new one ("Vehicles/Land" makes levels) -->
    <div class="input-group input-group-sm">
      <span class="input-group-text"><i class="fa" :class="options.length ? 'fa-search' : 'fa-folder-o'" /></span>
      <input
        v-model="text"
        class="form-control"
        :placeholder="options.length ? $t('parents.findOrNew') : $t('parents.firstOne')"
        @keydown.enter.prevent="onEnter"
      />
      <button
        v-if="newName"
        type="button"
        class="btn btn-outline-primary"
        @click="addNew"
      >
        <i class="fa fa-plus" /> {{ $t('parents.addNew', { name: label(newName) }) }}
      </button>
    </div>
    <div v-if="modelValue.length" class="small text-muted mt-1">
      {{ $t('parents.picked', { names: modelValue.map(label).join('、') }) }}
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { allParents, byName, normalizePath, parseParents, pathLabel, pathName, pathParts } from "@/libs/parents";

// parents of all the user's categories, fetched once per page (annotator)
let everyParent = null;
function loadEveryParent() {
  if (!everyParent) {
    everyParent = axios.get("/api/category/").then(r => allParents(r.data || [])).catch(() => []);
  }
  return everyParent;
}

/**
 * Pick parent categories from the ones already in use (click to toggle);
 * typing filters them, and offers to add a new one only when it does not exist.
 */
export default {
  name: "ParentInput",
  props: {
    modelValue: { type: Array, default: () => [] },
    /** parent names already in use */
    known: { type: Array, default: () => [] },
    /** also offer the parents of all the user's categories (fetched once) */
    fetchKnown: { type: Boolean, default: false }
  },
  emits: ["update:modelValue"],
  data() {
    return { text: "", fetched: [] };
  },
  created() {
    if (this.fetchKnown) loadEveryParent().then(list => (this.fetched = list));
  },
  computed: {
    /** every level of every known path, in tree order */
    options() {
      return allParents(parseParents([...this.known, ...this.fetched, ...this.modelValue]).map(p => ({ supercategories: [p] })))
        .sort((a, b) => {
          const pa = pathParts(a), pb = pathParts(b);
          for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
            if (pa[i] !== pb[i]) return byName(pa[i], pb[i]);
          }
          return pa.length - pb.length;
        });
    },
    filtering() {
      return !!this.text.trim();
    },
    shownOptions() {
      const q = this.text.trim().toLowerCase();
      return q ? this.options.filter(p => p.toLowerCase().includes(q) || pathLabel(p).toLowerCase().includes(q)) : this.options;
    },
    /** the typed path, if it does not exist yet */
    newName() {
      const name = normalizePath(this.text);
      if (!name) return "";
      return this.options.some(p => p.toLowerCase() === name.toLowerCase()) ? "" : name;
    }
  },
  methods: {
    pathName,
    label(p) {
      return pathLabel(p);
    },
    depth(p) {
      return pathParts(p).length - 1;
    },
    isPicked(p) {
      return this.modelValue.includes(p);
    },
    toggle(p) {
      this.$emit("update:modelValue", this.isPicked(p) ? this.modelValue.filter(x => x !== p) : [...this.modelValue, p]);
    },
    addNew() {
      const names = parseParents(this.newName);
      this.text = "";
      if (names.length) this.$emit("update:modelValue", parseParents([...this.modelValue, ...names]));
    },
    onEnter() {
      if (this.newName) return this.addNew();
      // Enter on a filtered list with one match picks it
      if (this.shownOptions.length === 1) {
        if (!this.isPicked(this.shownOptions[0])) this.toggle(this.shownOptions[0]);
        this.text = "";
      }
    }
  }
};
</script>

<style scoped>
.parent-options {
  max-height: 190px;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 3px;
  background: #fff;
}
.opt {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  border: 0;
  background: transparent;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
  text-align: left;
  color: #343a40;
}
.opt:hover {
  background: #f1f3f5;
}
.opt.picked {
  background: #e8f0fb;
  color: #1d5fae;
  font-weight: 600;
}
.opt .fa-check-square {
  color: #2a78d6;
}
.folder {
  color: #e0a526;
}
</style>
