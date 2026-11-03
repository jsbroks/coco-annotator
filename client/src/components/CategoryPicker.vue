<template>
  <div class="category-picker">
    <!-- add new categories (several at once) -->
    <div class="input-group input-group-sm mb-2">
      <input
        v-model="newText"
        class="form-control"
        :placeholder="$t('categoryPicker.addPlaceholder')"
        @keydown.enter.prevent="addNew"
        @paste="onPaste"
      />
      <button type="button" class="btn btn-outline-primary" :disabled="!newText.trim()" @click="addNew">
        <i class="fa fa-plus" /> {{ $t('categoryPicker.add') }}
      </button>
    </div>

    <div class="d-flex align-items-center flex-wrap gap-1 mb-1">
      <span class="small text-muted me-auto">
        {{ $t('categoryPicker.selected', { n: modelValue.length, total: rows.length }) }}
      </span>
      <button type="button" class="btn btn-outline-secondary btn-sm py-0" :disabled="!rows.length" @click="select(rows.map(r => r.key))">
        {{ $t('exportCategories.all') }}
      </button>
      <button type="button" class="btn btn-outline-secondary btn-sm py-0" :disabled="!modelValue.length" @click="select([])">
        {{ $t('exportCategories.none') }}
      </button>
    </div>

    <ParentChips
      class="mb-1"
      :categories="categories"
      :selected="modelValue"
      @update:selected="select"
    />

    <input
      v-if="rows.length > 8"
      v-model="filter"
      class="form-control form-control-sm mb-1"
      :placeholder="$t('exportCategories.search')"
    />

    <ul class="list-group picker-list">
      <template v-for="section in sections" :key="section.key">
        <li v-if="section.label" class="list-group-item group-header py-0 px-2 small">
          <i class="fa" :class="section.key === 'selected' ? 'fa-check' : section.parent ? 'fa-folder-o' : 'fa-file-o'" />
          {{ section.label }}
          <span class="text-muted">({{ section.rows.length }})</span>
        </li>
        <li
          v-for="row in section.rows"
          :key="section.key + '/' + row.key"
          class="list-group-item d-flex align-items-center gap-2 py-1 px-2"
          :class="{ 'text-muted': !isSelected(row.key) }"
        >
          <input
            :id="'catpick-' + section.key + '-' + row.key"
            type="checkbox"
            class="form-check-input m-0 flex-shrink-0"
            :checked="isSelected(row.key)"
            @change="toggle(row.key)"
          />
          <span
            class="badge class-index"
            :class="isSelected(row.key) ? 'text-bg-primary' : 'text-bg-light text-muted'"
            :title="$t('categoryPicker.order')"
          >{{ isSelected(row.key) ? modelValue.indexOf(row.key) : '–' }}</span>
          <span class="color-dot flex-shrink-0" :style="{ backgroundColor: row.color || '#adb5bd' }" />
          <label :for="'catpick-' + section.key + '-' + row.key" class="flex-grow-1 mb-0 text-truncate" :title="row.name">
            {{ row.name }}
            <span v-if="section.key === 'selected' || filter" class="parent-hint">{{ row.parents.map(p => pathLabel(p)).join('、') }}</span>
          </label>
          <span v-if="row.isNew" class="badge text-bg-success">{{ $t('categoryPicker.new') }}</span>
          <span v-if="isSelected(row.key) && !filter" class="btn-group btn-group-sm flex-shrink-0">
            <button
              type="button"
              class="btn btn-link btn-sm p-0 px-1"
              :disabled="modelValue.indexOf(row.key) === 0"
              :title="$t('exportCategories.moveUp')"
              @click="move(row.key, -1)"
            ><i class="fa fa-chevron-up" /></button>
            <button
              type="button"
              class="btn btn-link btn-sm p-0 px-1"
              :disabled="modelValue.indexOf(row.key) === modelValue.length - 1"
              :title="$t('exportCategories.moveDown')"
              @click="move(row.key, 1)"
            ><i class="fa fa-chevron-down" /></button>
          </span>
          <button
            v-if="row.isNew"
            type="button"
            class="btn btn-link btn-sm p-0 text-danger"
            :title="$t('categoryPicker.remove')"
            @click="removeNew(row.key)"
          ><i class="fa fa-times" /></button>
        </li>
      </template>
      <li v-if="!sections.length" class="list-group-item small text-muted">
        {{ rows.length ? $t('exportCategories.noMatch') : $t('categoryPicker.empty') }}
      </li>
    </ul>
    <div class="form-text">{{ $t('categoryPicker.hint') }}</div>
  </div>
</template>

<script>
/**
 * Pick the categories of a new dataset: tick existing ones, add new names
 * (comma / line separated, pasting a list works), set their order.
 * v-model is the ordered list of selected names.
 */
import ParentChips from "@/components/ParentChips.vue";
import { groupByParent, matchesSearch, parentsOf, pathLabel } from "@/libs/parents";

export default {
  name: "CategoryPicker",
  components: { ParentChips },
  props: {
    /** existing categories [{ name, color }] */
    categories: { type: Array, default: () => [] },
    modelValue: { type: Array, default: () => [] }
  },
  emits: ["update:modelValue"],
  data() {
    return { newText: "", filter: "", added: [] };
  },
  computed: {
    /**
     * selected first (in their order), then the rest by name. A row's key is
     * the category id, or the typed name for a new one (the same name can
     * exist under several parents).
     */
    rows() {
      const all = [
        ...this.added.map(name => ({ key: name, name, isNew: true, parents: [] })),
        ...this.categories.map(c => ({ key: c.id, name: c.name, color: c.color, isNew: false, parents: parentsOf(c),
          supercategories: parentsOf(c) }))
      ];
      const byKey = new Map(all.map(r => [r.key, r]));
      const selected = this.modelValue.filter(k => byKey.has(k)).map(k => byKey.get(k));
      const rest = all.filter(r => !this.modelValue.includes(r.key))
        .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
      return [...selected, ...rest];
    },
    visibleRows() {
      const q = this.filter.trim().toLowerCase();
      return q ? this.rows.filter(r => matchesSearch(r, q)) : this.rows;
    },
    /** the selected ones (in order) first, then the rest grouped by parent */
    sections() {
      const rows = this.visibleRows;
      const selected = rows.filter(r => this.isSelected(r.key));
      const rest = rows.filter(r => !this.isSelected(r.key));
      const groups = groupByParent(rest);
      const grouped = groups.some(g => g.parent !== null);
      const out = [];
      if (selected.length) {
        out.push({ key: "selected", label: grouped || rest.length ? this.$t("parents.selectedInOrder") : "", rows: selected });
      }
      groups.forEach(g => out.push({
        key: "p:" + (g.parent || ""),
        parent: g.parent,
        label: grouped ? (g.parent ? pathLabel(g.parent) : this.$t("parents.none")) : (selected.length ? this.$t("parents.others") : ""),
        rows: g.items
      }));
      return out;
    }
  },
  methods: {
    pathLabel,
    isSelected(key) {
      return this.modelValue.includes(key);
    },
    select(keys) {
      this.$emit("update:modelValue", [...keys]);
    },
    toggle(key) {
      this.select(this.isSelected(key) ? this.modelValue.filter(k => k !== key) : [...this.modelValue, key]);
    },
    /** what the dataset summary shows for a key */
    labelOf(key) {
      const row = this.rows.find(r => r.key === key);
      if (!row) return String(key);
      return row.parents.length ? `${row.name}（${pathLabel(row.parents[0])}）` : row.name;
    },
    move(key, step) {
      const order = [...this.modelValue];
      const from = order.indexOf(key);
      const to = from + step;
      if (to < 0 || to >= order.length) return;
      [order[from], order[to]] = [order[to], order[from]];
      this.select(order);
    },
    /** "a, b、c" or one per line -> names (trimmed, unique) */
    parse(text) {
      return [...new Set(String(text).split(/[\n\r,，、;；\t]+/).map(s => s.trim()).filter(Boolean))];
    },
    addNew() {
      const names = this.parse(this.newText);
      if (!names.length) return;
      // a typed name picks the existing category without a parent, or the only
      // one of that name; otherwise it is a new category
      const canCreate = this.$store.getters["user/can"]("create_categories");
      const denied = [];
      const keys = names.map(n => {
        const same = this.categories.filter(c => c.name === n);
        const pick = same.find(c => !parentsOf(c).length) || (same.length === 1 ? same[0] : null);
        if (pick) return pick.id;
        // a new category: only for a role that may make them
        if (!canCreate) {
          denied.push(n);
          return null;
        }
        if (!this.added.includes(n)) this.added.push(n);
        return n;
      }).filter(k => k != null);
      if (denied.length) this.$toastr.warning(this.$t("categoryPicker.noCreate", { names: denied.join("、") }));
      this.select([...this.modelValue, ...keys.filter(k => !this.modelValue.includes(k))]);
      this.newText = "";
    },
    onPaste(event) {
      // a pasted list (several lines) is added straight away
      const text = (event.clipboardData || window.clipboardData).getData("text");
      if (/[\n\r]/.test(text)) {
        event.preventDefault();
        this.newText = text;
        this.addNew();
      }
    },
    removeNew(name) {
      this.added = this.added.filter(n => n !== name);
      this.select(this.modelValue.filter(n => n !== name));
    },
    reset() {
      this.added = [];
      this.newText = "";
      this.filter = "";
    }
  }
};
</script>

<style scoped>
.picker-list {
  max-height: 300px;
  overflow-y: auto;
}
.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.class-index {
  min-width: 26px;
}
.group-header {
  background: #f1f3f5;
  font-weight: 600;
  color: #495057;
  position: sticky;
  top: 0;
  z-index: 1;
}
.parent-hint {
  font-size: 0.75rem;
  color: #6c757d;
  margin-left: 4px;
}
</style>
