<template>
  <div class="image-class">
    <div class="d-flex align-items-center mb-1">
      <a v-if="collapsible" href="#" class="title me-auto toggle" @click.prevent="toggle">
        <i class="fa fa-fw" :class="open ? 'fa-caret-down' : 'fa-caret-right'" />{{ $t('imageClass.title') }}
        <span v-if="!open && currentName" class="current">：{{ currentName }}</span>
      </a>
      <span v-else class="title me-auto">{{ $t('imageClass.title') }}</span>
      <span v-if="saving" class="small"><i class="fa fa-spinner fa-spin" /></span>
    </div>
    <template v-if="open">
    <div class="d-flex flex-wrap gap-1 pills">
      <button
        v-for="category in categories"
        :key="category.id"
        type="button"
        class="btn btn-sm class-pill"
        :class="{ selected: value === category.id }"
        :style="pillStyle(category)"
        :disabled="!canEdit || saving"
        :title="value === category.id ? $t('imageClass.clear') : $t('imageClass.set', { name: category.name })"
        @click="choose(category.id)"
      >
        <i v-if="value === category.id" class="fa fa-check" /> {{ category.name }}
      </button>
      <span v-if="!categories.length" class="small hint">{{ $t('imageClass.noCategories') }}</span>
    </div>
    <div class="form-check form-switch mt-1 small">
      <input id="imageClassNext" v-model="autoNext" class="form-check-input" type="checkbox" />
      <label class="form-check-label hint" for="imageClassNext">{{ $t('imageClass.autoNext') }}</label>
    </div>
    </template>
  </div>
</template>

<script>
import axios from "axios";
import { textColorFor } from "@/libs/colors";

const AUTO_NEXT_KEY = "imageClass/autoNext";
const OPEN_KEY = "imageClass/open";

export default {
  name: "ImageClassPicker",
  props: {
    imageId: { type: Number, required: true },
    value: { type: Number, default: null },
    categories: { type: Array, default: () => [] },
    canEdit: { type: Boolean, default: false },
    nextImageId: { type: Number, default: null },
    /** folded by default (datasets that are not for classification) */
    collapsible: { type: Boolean, default: false }
  },
  emits: ["update:value", "navigate"],
  data() {
    let autoNext = false;
    try {
      autoNext = localStorage.getItem(AUTO_NEXT_KEY) === "true";
    } catch {
      // storage unavailable
    }
    let open = true;
    if (this.collapsible) {
      try {
        open = localStorage.getItem(OPEN_KEY) === "true";
      } catch {
        open = false;
      }
    }
    return { saving: false, autoNext, open };
  },
  computed: {
    currentName() {
      const c = this.categories.find(x => x.id === this.value);
      return c ? c.name : "";
    }
  },
  watch: {
    autoNext(value) {
      try {
        localStorage.setItem(AUTO_NEXT_KEY, String(value));
      } catch {
        // ignore
      }
    }
  },
  methods: {
    toggle() {
      this.open = !this.open;
      try {
        localStorage.setItem(OPEN_KEY, String(this.open));
      } catch {
        // not remembered
      }
    },
    pillStyle(category) {
      const color = category.color || "#6c757d";
      return this.value === category.id
        ? { backgroundColor: color, borderColor: color, color: textColorFor(color) }
        : { borderColor: color, color: "#e9ecef" };
    },
    async choose(id) {
      const next = this.value === id ? null : id;
      this.saving = true;
      try {
        await axios.post(`/api/image/${this.imageId}/class`, { category_id: next });
        this.$emit("update:value", next);
        if (next != null && this.autoNext && this.nextImageId) this.$emit("navigate", this.nextImageId);
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.saving = false;
      }
    }
  }
};
</script>

<style scoped>
.image-class {
  padding: 4px 10px 6px;
  color: #e9ecef;
  font-size: 13px;
}
.title {
  font-weight: 600;
}
.toggle {
  color: #e9ecef;
  text-decoration: none;
}
.current {
  font-weight: 400;
  color: #9ec5fe;
}
.pills {
  max-height: 120px;
  overflow-y: auto;
}
.hint {
  color: #ced4da;
}
.class-pill {
  border: 1px solid;
  background: transparent;
  padding: 1px 8px;
  font-size: 12px;
}
.class-pill.selected {
  font-weight: 600;
}
</style>
