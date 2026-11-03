<template>
  <div v-if="groups.length" class="parent-chips d-flex flex-wrap align-items-center gap-1">
    <span class="small text-muted me-1"><i class="fa fa-folder-open-o" /> {{ $t('parents.quick') }}</span>
    <button
      v-for="g in groups"
      :key="g.parent"
      type="button"
      class="btn btn-sm parent-chip"
      :class="[g.state === 'all' ? 'btn-primary' : g.state === 'some' ? 'btn-outline-primary partial' : 'btn-outline-secondary', { sub: g.depth > 0 }]"
      :title="g.label + '：' + g.items.map(c => c.name).join('、')"
      @click="toggle(g)"
    >
      <i class="fa" :class="g.state === 'all' ? 'fa-check-square-o' : g.state === 'some' ? 'fa-minus-square-o' : 'fa-square-o'" />
      {{ g.depth > 0 ? '› ' + g.name : g.name }}
      <span class="small opacity-75">{{ g.chosen }}/{{ g.items.length }}</span>
    </button>
  </div>
</template>

<script>
import { buildTree, pathLabel } from "@/libs/parents";

/**
 * One button per parent category: adds all its categories to the selection
 * (or removes them when they are all selected already).
 */
export default {
  name: "ParentChips",
  props: {
    categories: { type: Array, required: true },
    selected: { type: Array, required: true },
    /** what the selection holds for a category (its id, or its name) */
    keyOf: { type: Function, default: c => c.id }
  },
  emits: ["update:selected"],
  computed: {
    groups() {
      // every folder of the tree (a folder, then the ones inside ...): picks all below it
      const chosen = new Set(this.selected);
      const out = [];
      const walk = (node, depth) => node.children.forEach(child => {
        const n = child.all.filter(c => chosen.has(this.keyOf(c))).length;
        out.push({ parent: child.path, name: child.name, label: pathLabel(child.path), depth, items: child.all,
          chosen: n, state: n === 0 ? "none" : n === child.all.length ? "all" : "some" });
        walk(child, depth + 1);
      });
      walk(buildTree(this.categories), 0);
      return out;
    }
  },
  methods: {
    toggle(group) {
      const keys = group.items.map(this.keyOf);
      if (group.state === "all") {
        this.$emit("update:selected", this.selected.filter(k => !keys.includes(k)));
      } else {
        this.$emit("update:selected", [...this.selected, ...keys.filter(k => !this.selected.includes(k))]);
      }
    }
  }
};
</script>

<style scoped>
.parent-chip {
  padding: 0 8px;
  font-size: 0.8rem;
  border-radius: 999px;
}
.parent-chip.sub {
  font-size: 0.75rem;
}
</style>
