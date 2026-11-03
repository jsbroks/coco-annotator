<template>
  <div class="help-panel text-start">
    <!-- questions about this image -->
    <div v-for="q in requests" :key="q.id" class="question" :class="[q.status, { focus: q.id === focusId }]">
      <div class="d-flex align-items-center gap-1 small head">
        <i class="fa fa-question-circle" />
        <strong>{{ q.mine ? $t('help.myQuestion') : q.user_name }}</strong>
        <span class="text-muted">· {{ ago(q.created_at) }}</span>
        <span v-if="q.status === 'resolved'" class="badge text-bg-success ms-auto">{{ $t('help.resolved') }}</span>
        <span v-else class="badge text-bg-warning ms-auto">{{ $t('help.waiting') }}</span>
      </div>
      <div v-if="q.message" class="text">{{ q.message }}</div>
      <div v-else class="text text-muted">{{ $t('help.noNote') }}</div>
      <div class="d-flex flex-wrap gap-2 mt-1">
        <button v-if="q.region" type="button" class="btn btn-sm btn-warning py-0" @click="$emit('show-region', q.region)">
          <i class="fa fa-search-plus" /> {{ $t('help.showRegion') }}
        </button>
        <a v-if="q.annotation_id" href="#" class="small" @click.prevent="$emit('show-annotation', q.annotation_id)">
          <i class="fa fa-crosshairs" /> {{ $t('help.showAnnotation', { id: q.annotation_id }) }}
        </a>
      </div>
      <div v-for="(r, i) in q.replies" :key="i" class="reply small">
        <strong>{{ r.name }}</strong> <span class="text-muted">{{ ago(r.at) }}</span>
        <div class="text">{{ r.message }}</div>
      </div>
      <div v-if="q.status === 'resolved' && q.mine" class="mt-1">
        <button type="button" class="btn btn-sm btn-success py-0" :disabled="busy" @click="dismiss(q)">
          <i class="fa fa-check" /> {{ $t('help.gotIt') }}
        </button>
      </div>
      <div v-if="q.status === 'open' && (q.can_answer || q.mine)" class="mt-1">
        <textarea
          v-model="drafts[q.id]"
          class="form-control form-control-sm"
          rows="2"
          :placeholder="q.mine ? $t('help.addMore') : $t('help.answerOptional')"
          @keydown.stop
        />
        <div class="d-flex flex-wrap gap-1 mt-1">
          <button v-if="!q.mine" type="button" class="btn btn-sm btn-success" :disabled="busy" @click="reply(q, true)">
            <i class="fa fa-check" /> {{ $t('help.handled') }}
          </button>
          <button type="button" class="btn btn-sm btn-outline-light" :disabled="!(drafts[q.id] || '').trim() || busy" @click="reply(q, false)">
            <i class="fa fa-reply" /> {{ $t('help.send') }}
          </button>
          <button v-if="q.mine" type="button" class="btn btn-sm btn-success" :disabled="busy" @click="reply(q, true)">
            <i class="fa fa-check" /> {{ $t('help.markSolved') }}
          </button>
          <button v-if="q.mine" type="button" class="btn btn-sm btn-link text-muted ms-auto" :disabled="busy" @click="cancel(q)">
            {{ $t('help.withdraw') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ask -->
    <button v-if="!asking" type="button" class="btn btn-sm btn-outline-warning w-100 ask-btn" @click="startAsk">
      <i class="fa fa-life-ring" /> {{ $t('help.ask') }}
    </button>
    <div v-else class="ask-box">
      <div class="zoom-tip small mb-2"><i class="fa fa-search-plus" /> {{ $t('help.zoomFirst') }}</div>
      <div class="small fw-semibold mb-1">{{ $t('help.askWho') }}</div>
      <div v-if="!helpers.length" class="small text-muted">{{ loadingHelpers ? '…' : $t('help.nobody') }}</div>
      <label v-for="h in helpers" :key="h.username" class="helper d-flex align-items-center gap-2">
        <input v-model="to" type="checkbox" class="form-check-input m-0" :value="h.username" />
        <span class="dot" :class="{ on: h.online }" :title="h.online ? $t('help.online') : $t('help.offline')" />
        <span class="text-truncate">{{ h.name }}</span>
        <span class="role small text-muted">{{ $t('help.role.' + h.role) }}</span>
        <span class="small ms-auto" :class="h.online ? 'text-success' : 'text-muted'">
          {{ h.online ? $t('help.online') : lastSeen(h) }}
        </span>
      </label>
      <div v-if="helpers.length && !anyOnline" class="small text-muted mt-1">{{ $t('help.noneOnline') }}</div>
      <textarea
        ref="message"
        v-model="message"
        class="form-control form-control-sm mt-2"
        rows="2"
        :placeholder="$t('help.noteOptional')"
        @keydown.stop
      />
      <label v-if="selectedAnnotationId" class="form-check small mt-1">
        <input v-model="attach" type="checkbox" class="form-check-input" />
        <span class="form-check-label">{{ $t('help.attachAnnotation', { id: selectedAnnotationId }) }}</span>
      </label>
      <div class="d-flex gap-1 mt-2">
        <button type="button" class="btn btn-sm btn-warning" :disabled="!to.length || busy" @click="send">
          <i class="fa fa-paper-plane" /> {{ $t('help.sendQuestion') }}
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="asking = false">{{ $t('help.cancel') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import Help, { ago } from "@/models/help";

/** Right side of the annotator: ask the creator / reviewers, see and answer questions. */
export default {
  name: "HelpPanel",
  props: {
    imageId: { type: Number, required: true },
    /** annotation id currently selected (to attach to a question) */
    selectedAnnotationId: { type: Number, default: null },
    /** () => { x, y, w, h } of the image part on screen now */
    getRegion: { type: Function, default: null },
    focusId: { type: Number, default: null }
  },
  emits: ["show-annotation", "show-region"],
  data() {
    return {
      requests: [], helpers: [], loadingHelpers: false, asking: false, to: [], message: "",
      attach: true, busy: false, drafts: {}, shownFocus: false
    };
  },
  computed: {
    anyOnline() {
      return this.helpers.some(h => h.online);
    }
  },
  watch: {
    imageId() {
      this.shownFocus = false;
      this.load();
    }
  },
  methods: {
    ago(iso) {
      return ago(iso, this.$t);
    },
    lastSeen(h) {
      return h.last_seen ? this.$t("help.seen", { t: ago(h.last_seen, this.$t) }) : this.$t("help.offline");
    },
    load() {
      Help.forImage(this.imageId).then(r => {
        this.requests = r.data.requests || [];
        // opened from a question: go to the place it is about (once)
        const q = this.requests.find(x => x.id === this.focusId);
        if (q && q.region && !this.shownFocus) {
          this.shownFocus = true;
          this.$emit("show-region", q.region);
        }
        // nothing open with a place any more: take the mark away
        if (!this.requests.some(x => x.status === "open" && x.region)) this.$emit("show-region", null);
      }).catch(() => {});
    },
    startAsk() {
      this.asking = true;
      this.loadingHelpers = true;
      Help.helpers(this.imageId)
        .then(r => {
          this.helpers = r.data.helpers || [];
          // the ones online by default (or everyone when nobody is)
          const online = this.helpers.filter(h => h.online).map(h => h.username);
          this.to = online.length ? online : this.helpers.map(h => h.username);
        })
        .finally(() => (this.loadingHelpers = false));
      this.$nextTick(() => this.$refs.message && this.$refs.message.focus());
    },
    send() {
      this.busy = true;
      Help.ask({
        image_id: this.imageId,
        message: this.message,
        to: this.to,
        annotation_id: this.attach ? this.selectedAnnotationId : null,
        region: this.getRegion ? this.getRegion() : null
      })
        .then(() => {
          this.$toastr.success(this.$t("help.sent"));
          this.asking = false;
          this.message = "";
          this.load();
        })
        .catch(e => this.$toastr.error((e.response && e.response.data.message) || String(e)))
        .finally(() => (this.busy = false));
    },
    reply(q, resolve) {
      this.busy = true;
      Help.reply(q.id, this.drafts[q.id] || "", resolve)
        .then(() => {
          this.drafts[q.id] = "";
          this.load();
          window.dispatchEvent(new Event("help-changed"));
        })
        .catch(e => this.$toastr.error((e.response && e.response.data.message) || String(e)))
        .finally(() => (this.busy = false));
    },
    /** the asker has read the answer: it goes away */
    dismiss(q) {
      this.busy = true;
      Help.seen(q.id)
        .then(() => {
          this.load();
          window.dispatchEvent(new Event("help-changed"));
        })
        .finally(() => (this.busy = false));
    },
    cancel(q) {
      this.busy = true;
      Help.cancel(q.id)
        .then(() => {
          this.load();
          window.dispatchEvent(new Event("help-changed"));
        })
        .finally(() => (this.busy = false));
    }
  },
  sockets: {
    helpRequest(q) {
      if (q.image_id === this.imageId) this.load();
    },
    helpReply(q) {
      if (q.image_id === this.imageId) this.load();
    }
  },
  created() {
    this.load();
  }
};
</script>

<style scoped>
.help-panel {
  padding: 4px 8px;
  color: #e9ecef;
}
.question {
  background: rgba(255, 193, 7, 0.12);
  border: 1px solid rgba(255, 193, 7, 0.45);
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 6px;
}
.question.resolved {
  background: rgba(25, 135, 84, 0.12);
  border-color: rgba(25, 135, 84, 0.45);
}
.question.focus {
  box-shadow: 0 0 0 2px #ffc107;
}
.question .head .fa {
  color: #ffc107;
}
.text {
  white-space: pre-wrap;
  font-size: 0.85rem;
}
.reply {
  border-left: 2px solid rgba(255, 255, 255, 0.3);
  padding-left: 6px;
  margin-top: 4px;
}
.text-muted {
  color: #adb5bd !important;
}
.text-success {
  color: #4ade80 !important;
}
.zoom-tip {
  background: rgba(255, 193, 7, 0.15);
  border-radius: 4px;
  padding: 4px 6px;
  color: #ffe08a;
}
.ask-box {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 8px;
}
.helper {
  font-size: 0.85rem;
  padding: 2px 0;
  cursor: pointer;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #6c757d;
  flex-shrink: 0;
}
.dot.on {
  background: #2ecc71;
  box-shadow: 0 0 0 2px rgba(46, 204, 113, 0.3);
}
.role {
  flex-shrink: 0;
}
</style>
