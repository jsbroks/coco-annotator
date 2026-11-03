<template>
  <div class="export-categories">
    <div class="d-flex align-items-center flex-wrap gap-1 mb-1">
      <span class="fw-semibold me-auto">
        {{ $t('exportCategories.title') }}
        <span class="text-muted fw-normal small">
          {{ $t('exportCategories.selected', { n: selected.length, total: categories.length }) }}
        </span>
      </span>
      <button type="button" class="btn btn-outline-secondary btn-sm py-0" @click="select(all)">
        {{ $t('exportCategories.all') }}
      </button>
      <button type="button" class="btn btn-outline-secondary btn-sm py-0" @click="select([])">
        {{ $t('exportCategories.none') }}
      </button>
      <button
        type="button"
        class="btn btn-outline-secondary btn-sm py-0"
        :disabled="!counts"
        @click="select(all.filter(id => usable(id) > 0))"
      >
        {{ $t('exportCategories.withAnnotations') }}
      </button>
    </div>

    <ParentChips class="mb-1" :categories="categories" :selected="selected" @update:selected="select" />

    <input
      v-if="categories.length > 8"
      v-model="filter"
      class="form-control form-control-sm mb-1"
      :placeholder="$t('exportCategories.search')"
    />

    <ul class="list-group category-list">
      <li
        v-for="(category, position) in visibleRows"
        :key="category.id"
        class="list-group-item d-flex align-items-center gap-2 py-1 px-2"
        :class="{ 'text-muted': !isSelected(category.id) }"
      >
        <input
          :id="'exportCat' + category.id"
          type="checkbox"
          class="form-check-input m-0 flex-shrink-0"
          :checked="isSelected(category.id)"
          @change="toggle(category.id)"
        />
        <span
          v-if="yolo"
          class="badge class-index"
          :class="isSelected(category.id) ? 'text-bg-primary' : 'text-bg-light text-muted'"
          :title="$t('exportCategories.classIndex')"
        >{{ isSelected(category.id) ? classIndex(category.id) : '–' }}</span>
        <span class="color-dot flex-shrink-0" :style="{ backgroundColor: category.color || '#999' }" />
        <label :for="'exportCat' + category.id" class="flex-grow-1 mb-0 text-truncate" :title="category.name">
          {{ category.name }}
          <span v-if="parentsOf(category).length" class="parent-hint">{{ parentsOf(category).map(p => pathLabel(p)).join('、') }}</span>
          <span v-if="category.hint" class="merge-hint">{{ category.hint }}</span>
        </label>
        <span class="small text-nowrap" :class="usable(category.id) ? 'text-muted' : 'text-warning-emphasis'">
          <template v-if="!counts"><i class="fa fa-spinner fa-spin" /></template>
          <template v-else>
            {{ countText(category.id) }}
          </template>
        </span>
        <span v-if="!filter" class="btn-group btn-group-sm flex-shrink-0">
          <button
            type="button"
            class="btn btn-link btn-sm p-0 px-1"
            :disabled="position === 0"
            :title="$t('exportCategories.moveUp')"
            @click="move(category.id, -1)"
          ><i class="fa fa-chevron-up" /></button>
          <button
            type="button"
            class="btn btn-link btn-sm p-0 px-1"
            :disabled="position === visibleRows.length - 1"
            :title="$t('exportCategories.moveDown')"
            @click="move(category.id, 1)"
          ><i class="fa fa-chevron-down" /></button>
        </span>
      </li>
      <li v-if="!visibleRows.length" class="list-group-item small text-muted">
        {{ categories.length ? $t('exportCategories.noMatch') : $t('exportCategories.empty') }}
      </li>
    </ul>

    <div class="d-flex flex-wrap gap-2 small mt-1">
      <span v-if="counts && yoloTask !== 'classify'" :class="totalAnnotations ? 'text-muted' : 'text-danger'">
        {{ $t('exportCategories.total', { n: totalAnnotations }) }}
      </span>
      <span v-else-if="counts" class="text-muted">{{ $t('exportCategories.classifyHint') }}</span>
      <a v-if="!filter && categories.length > 1" href="#" class="ms-auto" @click.prevent="sortByName">
        {{ $t('exportCategories.sortByName') }}
      </a>
    </div>
    <div v-if="yolo" class="form-text mt-0">{{ $t('exportCategories.yoloOrder') }}</div>
    <div v-if="!selected.length" class="small text-danger">{{ $t('exportCategories.pickOne') }}</div>
  </div>
</template>

<script>
/**
 * Category list for the export dialog: tick the categories to export and
 * set their order (the order is the YOLO class index and the order of
 * "categories" in COCO). Counts come from /api/dataset/<id>/category_counts.
 */
import ParentChips from "@/components/ParentChips.vue";
import { matchesSearch, parentsOf, pathLabel } from "@/libs/parents";

export default {
  name: "ExportCategories",
  components: { ParentChips },
  props: {
    categories: { type: Array, required: true },
    /** { [categoryId]: { annotations, images, boxes, rotated, polygons, keypoints } } or null while loading */
    counts: { type: Object, default: null },
    /** null for COCO, else detect | segment | obb | pose */
    yoloTask: { type: String, default: null },
    order: { type: Array, required: true },
    selected: { type: Array, required: true }
  },
  emits: ["update:order", "update:selected"],
  data() {
    return { filter: "" };
  },
  computed: {
    /** Class index badges and reordering only matter where the order is the class id */
    yolo() {
      return !!this.yoloTask && this.yoloTask !== "classify";
    },
    all() {
      return this.rows.map(c => c.id);
    },
    rows() {
      const byId = new Map(this.categories.map(c => [c.id, c]));
      return this.order.filter(id => byId.has(id)).map(id => byId.get(id));
    },
    visibleRows() {
      const q = this.filter.trim().toLowerCase();
      return q ? this.rows.filter(c => matchesSearch(c, q)) : this.rows;
    },
    selectedInOrder() {
      const chosen = new Set(this.selected);
      return this.all.filter(id => chosen.has(id));
    },
    totalAnnotations() {
      return this.selectedInOrder.reduce((n, id) => n + this.usable(id), 0);
    }
  },
  methods: {
    parentsOf,
    pathLabel,
    isSelected(id) {
      return this.selected.includes(id);
    },
    classIndex(id) {
      return this.selectedInOrder.indexOf(id);
    },
    stat(id) {
      return (this.counts && this.counts[id]) || { annotations: 0, images: 0, keypoints: 0 };
    },
    /** Annotations of this category that the chosen format can export */
    usable(id) {
      const s = this.stat(id);
      if (this.yoloTask === "pose") return s.keypoints;
      if (this.yoloTask === "classify") return (s.classified || 0) + (s.images || 0);
      // semantic masks need a shape (box, rotated box or polygon)
      if (this.yoloTask === "semantic") return (s.boxes || 0) + (s.rotated || 0) + (s.polygons || 0);
      return s.annotations;
    },
    countText(id) {
      const s = this.stat(id);
      if (this.yoloTask === "pose") {
        return s.keypoints
          ? this.$t("exportCategories.keypointCount", { n: s.keypoints })
          : this.$t("exportCategories.noKeypoints");
      }
      if (this.yoloTask === "classify") {
        if (!s.classified && !s.images) return this.$t("exportCategories.noAnnotations");
        return this.$t("exportCategories.classifyCount", { classified: s.classified || 0, images: s.images || 0 });
      }
      if (!s.annotations) return this.$t("exportCategories.noAnnotations");
      if (this.yoloTask === "semantic" && !this.usable(id)) return this.$t("exportCategories.noShapes");
      return this.$t("exportCategories.count", { n: s.annotations, images: s.images });
    },
    select(ids) {
      this.$emit("update:selected", [...ids]);
    },
    toggle(id) {
      this.select(this.isSelected(id) ? this.selected.filter(x => x !== id) : [...this.selected, id]);
    },
    move(id, step) {
      const order = [...this.all];
      const from = order.indexOf(id);
      const to = from + step;
      if (to < 0 || to >= order.length) return;
      [order[from], order[to]] = [order[to], order[from]];
      this.$emit("update:order", order);
    },
    sortByName() {
      const sorted = [...this.rows].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
      this.$emit("update:order", sorted.map(c => c.id));
    }
  }
};
</script>

<style scoped>
.merge-hint {
  margin-left: 6px;
  font-size: 0.75rem;
  color: #b35c00;
}
.parent-hint {
  font-size: 0.75rem;
  color: #6c757d;
  margin-left: 4px;
}
.category-list {
  max-height: 260px;
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
</style>
