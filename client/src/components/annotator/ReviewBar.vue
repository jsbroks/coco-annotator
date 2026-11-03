<template>
  <div class="review-bar">
    <div class="d-flex align-items-center gap-2 flex-wrap">
      <span class="badge" :class="statusClass(status)">{{ $t('review.status.' + status) }}</span>
      <span v-if="review.assignee" class="small review-sub" :title="$t('review.assignee')">
        <i class="fa fa-user-o" /> {{ review.assignee }}
      </span>
    </div>

    <div v-if="status === 'rejected' && review.review_note" class="review-note mt-1">
      <i class="fa fa-commenting-o" /> {{ review.review_note }}
      <span v-if="review.reviewed_by" class="review-sub">— {{ review.reviewed_by }}</span>
    </div>
    <button
      v-if="status === 'rejected' && regions.length"
      type="button"
      class="btn btn-sm btn-outline-warning mt-1 py-0"
      @click="$emit('show-regions')"
    >
      <i class="fa fa-crosshairs" /> {{ $t('review.showRegions', { n: regions.length }) }}
    </button>
    <div v-else-if="status === 'labeled' && review.labeled_by" class="small review-sub mt-1">
      {{ $t('review.submittedBy', { name: review.labeled_by }) }}
    </div>
    <div v-else-if="status === 'approved' && review.reviewed_by" class="small review-sub mt-1">
      {{ $t('review.approvedBy', { name: review.reviewed_by }) }}
    </div>

    <div class="d-flex flex-wrap gap-1 mt-2">
      <button
        v-if="canEdit && (status === 'unlabeled' || status === 'rejected')"
        type="button"
        class="btn btn-sm btn-primary"
        :disabled="busy"
        @click="act('submit')"
      >
        <i class="fa" :class="canReview ? 'fa-check' : 'fa-paper-plane'" />
        {{ canReview ? $t('review.submitApprove') : $t('review.submit') }}
      </button>
      <template v-if="canReview && status !== 'unlabeled'">
        <button
          v-if="status !== 'approved'"
          type="button"
          class="btn btn-sm btn-success"
          :disabled="busy"
          @click="act('approve')"
        >
          <i class="fa fa-check" /> {{ $t('review.approve') }}
        </button>
        <button
          v-if="status !== 'rejected'"
          type="button"
          class="btn btn-sm btn-outline-danger"
          :disabled="busy"
          @click="rejecting = !rejecting"
        >
          <i class="fa fa-undo" /> {{ $t('review.reject') }}
        </button>
      </template>
      <button
        v-if="(status === 'labeled' && canEdit) || (status === 'approved' && canReview)"
        type="button"
        class="btn btn-sm btn-outline-secondary"
        :disabled="busy"
        @click="act('reopen')"
      >
        {{ $t('review.reopen') }}
      </button>
    </div>

    <div v-if="rejecting" class="mt-2">
      <textarea
        ref="note"
        v-model="note"
        class="form-control form-control-sm"
        rows="2"
        :placeholder="$t('review.notePlaceholder')"
        @keydown.enter.ctrl.prevent="act('reject', note)"
        @keydown.esc.prevent="rejecting = false"
        @keydown.exact="onNoteKey"
      />
      <RejectReasons ref="reasons" class="mt-1" :note="note" @pick="pickReason" />
      <div v-if="getRegion" class="form-check small mt-1" :title="$t('review.attachViewHint')">
        <input id="reviewAttachView" v-model="attachView" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="reviewAttachView">{{ $t('review.attachView') }}</label>
      </div>
      <div class="d-flex gap-1 mt-1">
        <button type="button" class="btn btn-sm btn-danger" :disabled="busy" @click="act('reject', note)">
          {{ $t('review.rejectConfirm') }}
        </button>
        <button type="button" class="btn btn-sm btn-link text-light" @click="rejecting = false">
          {{ $t('review.cancel') }}
        </button>
      </div>
    </div>

    <div v-if="canEdit" class="form-check form-switch mt-2 small">
      <input id="reviewSubmitOnNext" v-model="submitOnNext" class="form-check-input" type="checkbox" />
      <label class="form-check-label" for="reviewSubmitOnNext" :title="$t('review.submitOnNextHint')">
        {{ $t('review.submitOnNext') }}
      </label>
    </div>

    <!-- submitting an image without annotations: is it really empty? -->
    <Teleport to="body">
      <div v-if="emptyAsk" class="empty-ask-backdrop" @mousedown.self="answerEmpty('stay')">
        <div class="empty-ask shadow-lg" role="dialog" aria-modal="true" :aria-label="$t('review.emptyTitle')">
          <h6 class="mb-2"><i class="fa fa-question-circle text-warning me-1" /> {{ $t('review.emptyTitle') }}</h6>
          <p class="small mb-3">{{ $t('review.emptyText', { name: filename }) }}</p>
          <div class="d-flex flex-wrap gap-2">
            <button ref="emptyYes" type="button" class="btn btn-sm btn-primary" @click="answerEmpty('yes')">
              {{ $t('review.emptyYes') }} <kbd>Enter</kbd>
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" @click="answerEmpty('stay')">
              {{ $t('review.emptyStay') }} <kbd>Esc</kbd>
            </button>
            <button v-if="emptyAsk.canSkip" type="button" class="btn btn-sm btn-link ms-auto" @click="answerEmpty('skip')">
              {{ $t('review.emptySkip') }} <kbd>N</kbd>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import axios from "axios";
import RejectReasons from "@/components/RejectReasons.vue";
import { withReason } from "@/libs/rejectReasons";

const SUBMIT_ON_NEXT_KEY = "review/submitOnNext";

export function statusClass(status) {
  return {
    unlabeled: "text-bg-secondary",
    labeled: "text-bg-warning",
    approved: "text-bg-success",
    rejected: "text-bg-danger"
  }[status] || "text-bg-secondary";
}

export default {
  name: "ReviewBar",
  components: { RejectReasons },
  props: {
    imageId: { type: Number, required: true },
    datasetId: { type: Number, default: null },
    filename: { type: String, default: "" },
    review: { type: Object, default: () => ({}) },
    canEdit: { type: Boolean, default: false },
    canReview: { type: Boolean, default: false },
    // the zoomed-in part of the image, {x, y, w, h} (null when not zoomed)
    getRegion: { type: Function, default: null }
  },
  emits: ["updated", "before-submit", "show-regions"],
  data() {
    let submitOnNext = false;
    try {
      submitOnNext = localStorage.getItem(SUBMIT_ON_NEXT_KEY) === "true";
    } catch {
      // storage unavailable: off
    }
    // emptyAsk: {canSkip, resolve} while asking whether an image is really empty
    return { busy: false, rejecting: false, note: "", submitOnNext, attachView: true, emptyAsk: null };
  },
  computed: {
    regions() {
      return this.review.review_regions || [];
    },
    status() {
      return this.review.status || "unlabeled";
    }
  },
  watch: {
    submitOnNext(value) {
      try {
        localStorage.setItem(SUBMIT_ON_NEXT_KEY, String(value));
      } catch {
        // ignore
      }
    },
    imageId() {
      this.rejecting = false;
      this.note = "";
      if (this.emptyAsk) this.answerEmpty("stay");
    }
  },
  methods: {
    statusClass,
    async act(action, note = null) {
      if (this.busy) return;
      this.busy = true;
      try {
        // the latest edits are saved before submitting; not saved, not submitted
        if (action === "submit") {
          const saved = await Promise.race([
            new Promise(resolve => this.$emit("before-submit", resolve)),
            new Promise(resolve => setTimeout(() => resolve(false), 15000))
          ]);
          if (saved === false) {
            this.$toastr.warning(this.$t("review.notSaved"));
            return;
          }
        }
        const body = { action, note: note || "" };
        if (action === "reject" && this.attachView && this.getRegion) {
          const v = this.getRegion();
          if (v) body.regions = [[v.x, v.y, v.w, v.h]];
        }
        if (action === "submit") body.skip_empty = true;
        let r = await axios.post(`/api/review/image/${this.imageId}`, body);
        if (r.data.skipped) {
          // nothing annotated: only submitted once confirmed as empty
          if ((await this.askEmpty(false)) !== "yes") return;
          r = await axios.post(`/api/review/image/${this.imageId}`, { action, confirm_empty: true });
        }
        this.$emit("updated", r.data);
        this.rejecting = false;
        this.note = "";
        const approvedOwn = action === "submit" && r.data.status === "approved";
        this.$toastr.success(this.$t(approvedOwn ? "review.done.selfApprove" : "review.done." + action));
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    },
    /** a number key in the empty reason box picks that saved reason */
    onNoteKey(e) {
      const r = this.$refs.reasons && this.$refs.reasons.forKey(e, this.note);
      if (!r) return;
      e.preventDefault();
      this.pickReason(r);
    },
    pickReason(r) {
      this.note = withReason(this.note, r);
      this.$nextTick(() => this.$refs.note && this.$refs.note.focus());
    },
    /** Y: approve (reviewers) or "done" (annotators), whichever this image offers */
    shortcutApprove() {
      if (this.busy) return;
      if (this.canEdit && (this.status === "unlabeled" || this.status === "rejected")) this.act("submit");
      else if (this.canReview && this.status !== "unlabeled" && this.status !== "approved") this.act("approve");
      else this.$toastr.info(this.$t("review.nothingToApprove"));
    },
    /** X: open the reject box (Ctrl+Enter sends, Esc closes) */
    shortcutReject() {
      if (this.busy || !this.canReview || this.status === "unlabeled" || this.status === "rejected") {
        this.$toastr.info(this.$t("review.nothingToReject"));
        return;
      }
      this.rejecting = true;
      this.$nextTick(() => this.$refs.note && this.$refs.note.focus());
    },
    /**
     * Called when moving to the next image (N or the arrow), after saving:
     * with the switch on, an image not submitted yet is submitted. One
     * without annotations asks first whether it is really empty: yes
     * submits it, "skip" moves on without submitting, "stay" stays.
     * Returns "stay" to stop the move.
     */
    async submitBeforeNext() {
      if (!this.submitOnNext || !this.canEdit || !(this.status === "unlabeled" || this.status === "rejected")) return "next";
      try {
        let r = await axios.post(`/api/review/image/${this.imageId}`, { action: "submit", skip_empty: true });
        if (r.data.skipped) {
          const answer = await this.askEmpty(true);
          if (answer !== "yes") return answer === "stay" ? "stay" : "next";
          r = await axios.post(`/api/review/image/${this.imageId}`, { action: "submit", confirm_empty: true });
        }
        if (!r.data.skipped) {
          this.$emit("updated", r.data);
          this.$toastr.success(this.$t(r.data.status === "approved" ? "review.approvedOnNext" : "review.submittedOnNext",
            { name: this.filename }));
        }
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      }
      return "next";
    },
    /** "Is this image really empty?" resolves "yes" | "stay" | "skip" */
    askEmpty(canSkip) {
      return new Promise(resolve => {
        this.emptyAsk = { canSkip, resolve };
        window.addEventListener("keydown", this.onEmptyKey, true);
        this.$nextTick(() => this.$refs.emptyYes && this.$refs.emptyYes.focus());
      });
    },
    answerEmpty(answer) {
      const ask = this.emptyAsk;
      if (!ask) return;
      this.emptyAsk = null;
      window.removeEventListener("keydown", this.onEmptyKey, true);
      ask.resolve(answer === "skip" && !ask.canSkip ? "stay" : answer);
    },
    /** keys go to the question only (not to the annotator's shortcuts) */
    onEmptyKey(e) {
      const key = e.key.toLowerCase();
      if (key === "tab") return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.repeat) return;
      if (key === "enter" || key === "y") this.answerEmpty("yes");
      else if (key === "escape") this.answerEmpty("stay");
      else if (key === "n" && this.emptyAsk.canSkip) this.answerEmpty("skip");
    }
  },
  beforeUnmount() {
    if (this.emptyAsk) this.answerEmpty("stay");
  }
};
</script>

<style scoped>
.review-bar {
  padding: 6px 10px;
  color: #e9ecef;
  font-size: 13px;
}
.review-sub {
  color: #ced4da;
}
.empty-ask-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1060;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
}
.empty-ask {
  width: 380px;
  max-width: calc(100vw - 32px);
  padding: 16px 18px;
  border-radius: 10px;
  background: #fff;
  color: #212529;
  text-align: left;
}
.empty-ask kbd {
  font-size: 0.7rem;
  padding: 1px 4px;
  margin-left: 4px;
  opacity: 0.8;
}
.review-note {
  background: rgba(220, 53, 69, 0.15);
  border-left: 3px solid #dc3545;
  padding: 4px 6px;
  border-radius: 3px;
  white-space: pre-wrap;
}
</style>
