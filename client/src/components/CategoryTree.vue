<template>
  <ul class="cat-tree list-unstyled mb-0">
    <li v-for="node in nodes" :key="node.path">
      <div
        class="tree-row d-flex align-items-center"
        :class="{ active: node.path === selected }"
        :style="{ paddingLeft: 6 + depth * 14 + 'px' }"
        role="treeitem"
        :aria-expanded="node.children.length ? isOpen(node) : undefined"
        :aria-selected="node.path === selected"
        @click="$emit('select', node.path)"
      >
        <button
          type="button"
          class="twisty btn btn-link p-0"
          :class="{ invisible: !node.children.length }"
          :aria-label="isOpen(node) ? $t('tree.collapse') : $t('tree.expand')"
          @click.stop="$emit('toggle', node.path)"
        >
          <i class="fa" :class="isOpen(node) ? 'fa-caret-down' : 'fa-caret-right'" />
        </button>
        <i class="fa fa-fw folder" :class="node.path === selected || isOpen(node) ? 'fa-folder-open' : 'fa-folder'" />
        <span class="name text-truncate" :title="node.path">{{ node.name }}</span>
        <span class="count">{{ node.all.length }}</span>
      </div>
      <CategoryTree
        v-if="node.children.length && isOpen(node)"
        :nodes="node.children"
        :selected="selected"
        :open="open"
        :depth="depth + 1"
        @select="p => $emit('select', p)"
        @toggle="p => $emit('toggle', p)"
      />
    </li>
  </ul>
</template>

<script>
/** Folders of parent categories (a › b › ...), any depth */
export default {
  name: "CategoryTree",
  props: {
    nodes: { type: Array, required: true },
    selected: { type: String, default: null },
    /** paths that are expanded */
    open: { type: Object, required: true },
    depth: { type: Number, default: 0 }
  },
  emits: ["select", "toggle"],
  methods: {
    isOpen(node) {
      return this.open.has(node.path);
    }
  }
};
</script>

<style scoped>
.tree-row {
  gap: 4px;
  padding: 4px 8px 4px 6px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #343a40;
}
.tree-row:hover {
  background: #eef1f5;
}
.tree-row.active {
  background: #2a78d6;
  color: #fff;
}
.tree-row.active .count {
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.2);
}
.twisty {
  width: 14px;
  color: inherit;
  text-decoration: none;
  line-height: 1;
}
.folder {
  color: #e0a526;
}
.tree-row.active .folder {
  color: #fff;
}
.name {
  flex: 1;
  min-width: 0;
}
.count {
  font-size: 0.72rem;
  color: #868e96;
  background: #e9ecef;
  border-radius: 999px;
  padding: 0 7px;
}
</style>
