<template>
  <div :id="modalId" class="modal fade" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content text-start">
        <div class="modal-header">
          <h5 class="modal-title"><i class="fa fa-eraser" /> {{ $t('aiCleanup.title', { name: datasetName }) }}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" />
        </div>

        <div class="modal-body">
          <div v-if="!summary" class="text-muted"><i class="fa fa-spinner fa-spin" /></div>
          <div v-else-if="!summary.total" class="alert alert-info mb-0">{{ $t('aiCleanup.none') }}</div>
          <template v-else>
            <p class="small mb-3">{{ $t('aiCleanup.total', { n: summary.total.toLocaleString(), edited: summary.edited.toLocaleString() }) }}</p>

            <div class="mb-2">
              <label class="form-label small mb-1" :for="modalId + 'Model'">{{ $t('aiCleanup.model') }}</label>
              <select :id="modalId + 'Model'" v-model="filters.model" class="form-select form-select-sm">
                <option value="">{{ $t('aiCleanup.allModels') }}</option>
                <option v-for="m in summary.models" :key="m.name || '__none__'" :value="m.name || '__none__'">
                  {{ m.name || $t('aiCleanup.unknownModel') }} ({{ m.count.toLocaleString() }})
                </option>
              </select>
            </div>
            <div class="mb-2">
              <label class="form-label small mb-1" :for="modalId + 'Category'">{{ $t('aiCleanup.category') }}</label>
              <select :id="modalId + 'Category'" v-model="filters.category_id" class="form-select form-select-sm">
                <option value="">{{ $t('aiCleanup.allCategories') }}</option>
                <option v-for="c in summary.categories" :key="c.id" :value="c.id">{{ c.name }} ({{ c.count.toLocaleString() }})</option>
              </select>
            </div>
            <div class="form-check mb-3">
              <input :id="modalId + 'Keep'" v-model="filters.keep_edited" type="checkbox" class="form-check-input" />
              <label class="form-check-label small" :for="modalId + 'Keep'">{{ $t('aiCleanup.keepEdited') }}</label>
            </div>

            <div class="alert py-2 small mb-0" :class="summary.matching ? 'alert-warning' : 'alert-light border'">
              <i v-if="counting" class="fa fa-spinner fa-spin" />
              <template v-else-if="summary.matching">
                {{ $t('aiCleanup.matching', { n: summary.matching.toLocaleString(), images: summary.matching_images.toLocaleString() }) }}
              </template>
              <template v-else>{{ $t('aiCleanup.nothing') }}</template>
              <div v-if="summary.matching" class="text-muted mt-1">{{ $t('aiCleanup.trashHint') }}</div>
            </div>
          </template>
        </div>

        <div class="modal-footer">
          <template v-if="summary && summary.matching && summary.can_edit">
            <button v-if="!confirming" type="button" class="btn btn-danger" :disabled="counting" @click="confirming = true">
              <i class="fa fa-trash-o" /> {{ $t('aiCleanup.delete', { n: summary.matching.toLocaleString() }) }}
            </button>
            <template v-else>
              <span class="small me-auto">{{ $t('aiCleanup.sure') }}</span>
              <button type="button" class="btn btn-danger" :disabled="deleting" @click="remove">
                <i v-if="deleting" class="fa fa-spinner fa-spin" /> {{ $t('aiCleanup.yes', { n: summary.matching.toLocaleString() }) }}
              </button>
              <button type="button" class="btn btn-outline-secondary" :disabled="deleting" @click="confirming = false">{{ $t('review.cancel') }}</button>
            </template>
          </template>
          <span v-else-if="summary && summary.matching && !summary.can_edit" class="small text-muted me-auto">{{ $t('aiCleanup.noPermission') }}</span>
          <button v-if="!confirming" type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t('modelRun.close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { showModal, hideModal } from "@/libs/modal";

/** Send annotations models made to the trash, all at once (by model / category). */
export default {
  name: "AiCleanupModal",
  props: {
    modalId: { type: String, required: true },
    datasetId: { type: Number, required: true },
    datasetName: { type: String, default: "" }
  },
  emits: ["deleted"],
  data() {
    return {
      summary: null, counting: false, deleting: false, confirming: false, request: 0,
      filters: { model: "", category_id: "", keep_edited: true }
    };
  },
  watch: {
    filters: {
      deep: true,
      handler() {
        this.confirming = false;
        this.load();
      }
    }
  },
  methods: {
    open() {
      this.summary = null;
      this.confirming = false;
      showModal("#" + this.modalId);
      this.load();
    },
    load() {
      // filters can change faster than the answers come: only the latest counts
      const request = (this.request = (this.request || 0) + 1);
      this.counting = true;
      return axios
        .get(`/api/dataset/${this.datasetId}/ai`, { params: this.filters })
        .then(r => {
          if (request === this.request) this.summary = r.data;
        })
        .catch(error => this.$toastr.error(((error.response && error.response.data) || {}).message || String(error)))
        .finally(() => {
          if (request === this.request) this.counting = false;
        });
    },
    async remove() {
      this.deleting = true;
      try {
        const { data } = await axios.post(`/api/dataset/${this.datasetId}/ai/delete`, this.filters);
        this.$toastr.success(this.$t("aiCleanup.done", { n: data.deleted.toLocaleString(), images: data.images.toLocaleString() }));
        hideModal("#" + this.modalId);
        this.$emit("deleted", data);
      } catch (error) {
        this.$toastr.error(((error.response && error.response.data) || {}).message || String(error));
      } finally {
        this.deleting = false;
        this.confirming = false;
      }
    }
  }
};
</script>
