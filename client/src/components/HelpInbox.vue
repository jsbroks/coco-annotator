<template>
  <div class="help-inbox dropdown">
    <button
      type="button"
      class="btn btn-sm bell"
      :class="incoming.length ? 'btn-warning' : 'btn-outline-light'"
      data-bs-toggle="dropdown"
      data-bs-auto-close="outside"
      aria-expanded="false"
      :title="$t('help.inboxTitle')"
      @click="load"
    >
      <i class="fa fa-life-ring" />
      <span v-if="incoming.length" class="badge rounded-pill text-bg-danger">{{ incoming.length }}</span>
    </button>
    <div class="dropdown-menu dropdown-menu-end p-0 shadow help-menu text-start">
      <div class="px-3 py-2 border-bottom fw-semibold small d-flex align-items-center">
        <i class="fa fa-life-ring me-1" /> {{ $t('help.inboxTitle') }}
      </div>
      <div class="help-list">
        <div v-if="!incoming.length && !answered.length" class="text-center text-muted small py-4">
          {{ $t('help.inboxEmpty') }}
        </div>
        <template v-if="incoming.length">
          <div class="section small text-muted px-3 pt-2">{{ $t('help.askedToMe') }}</div>
          <a v-for="q in incoming" :key="'i' + q.id" href="#" class="item d-block px-3 py-2" @click.prevent="open(q)">
            <div class="d-flex align-items-center gap-1 small">
              <strong>{{ q.user_name }}</strong>
              <span class="text-muted text-truncate">· {{ q.dataset_name }} / {{ q.file_name }}</span>
              <span class="ms-auto text-muted flex-shrink-0">{{ ago(q.created_at) }}</span>
            </div>
            <div class="msg">{{ q.message || $t('help.noNote') }}</div>
            <div v-if="q.replies.length" class="small text-success"><i class="fa fa-reply" /> {{ $t('help.repliesN', { n: q.replies.length }) }}</div>
          </a>
        </template>
        <template v-if="answered.length">
          <div class="section small text-muted px-3 pt-2">{{ $t('help.myQuestions') }}</div>
          <a v-for="q in answered" :key="'m' + q.id" href="#" class="item d-block px-3 py-2" @click.prevent="openMine(q)">
            <div class="d-flex align-items-center gap-1 small">
              <span class="badge" :class="q.status === 'resolved' ? 'text-bg-success' : 'text-bg-primary'">
                {{ q.status === 'resolved' ? $t('help.resolved') : $t('help.replied') }}
              </span>
              <span class="text-muted text-truncate">{{ q.dataset_name }} / {{ q.file_name }}</span>
              <span class="ms-auto text-muted flex-shrink-0">{{ ago(q.updated_at) }}</span>
            </div>
            <div class="msg text-muted">{{ q.message || $t('help.noNote') }}</div>
            <div class="msg"><i class="fa fa-reply" /> {{ lastReply(q) }}</div>
          </a>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import Help, { ago } from "@/models/help";

/** Bell in the top bar: questions asked to me, answers to mine; pushed live. */
export default {
  name: "HelpInbox",
  data() {
    return { incoming: [], mine: [], seen: new Set() };
  },
  computed: {
    /** my questions that got an answer */
    answered() {
      return this.mine.filter(q => q.replies.some(r => r.user !== q.user) || (q.status === "resolved" && q.resolved_by !== q.user));
    }
  },
  methods: {
    ago(iso) {
      return ago(iso, this.$t);
    },
    lastReply(q) {
      const r = [...q.replies].reverse().find(x => x.user !== q.user);
      if (r) return `${r.name}：${r.message}`;
      return q.status === "resolved" ? this.$t("help.handledBy", { name: q.resolved_by || "" }) : "";
    },
    load() {
      Help.inbox().then(r => {
        this.incoming = r.data.incoming || [];
        this.mine = r.data.mine || [];
      }).catch(() => {});
    },
    /** my answered question: read it (it leaves the list) */
    openMine(q) {
      if (q.status === "resolved") Help.seen(q.id).then(this.load);
      this.open(q);
    },
    open(q) {
      this.$router.push({ name: "annotate", params: { identifier: q.image_id }, query: { help: q.id } });
    },
    /** goes away by itself (the bell keeps the list); a click opens the image */
    toastOptions(q, { mine = false, long = false } = {}) {
      return {
        timeOut: long ? 15000 : 8000,
        extendedTimeOut: 3000,
        closeButton: true,
        tapToDismiss: true,
        positionClass: "toast-bottom-right",
        onclick: () => (mine ? this.openMine(q) : this.open(q))
      };
    }
  },
  sockets: {
    helpRequest(q) {
      this.load();
      this.$toastr.warning(
        `${q.dataset_name} / ${q.file_name}${q.message ? "：" + q.message : ""}（${this.$t("help.clickToGo")}）`,
        this.$t("help.someoneAsks", { name: q.user_name }),
        this.toastOptions(q, { long: true })
      );
    },
    helpReply(q) {
      this.load();
      const me = this.$store.state.user.user;
      if (!me || q.status === "cancelled") return;
      const last = q.replies[q.replies.length - 1];
      if (q.user === me.username && q.status === "resolved" && q.resolved_by && q.resolved_by !== me.username) {
        this.$toastr.success(
          `${q.file_name}${last && last.user !== me.username ? "：" + last.message : ""}（${this.$t("help.clickToGo")}）`,
          this.$t("help.handledToast", { name: q.resolved_by }),
          this.toastOptions(q, { mine: true })
        );
      } else if (q.user === me.username && last && last.user !== me.username) {
        this.$toastr.success(
          `${q.file_name}：${last.message}（${this.$t("help.clickToGo")}）`,
          this.$t("help.gotAnswer", { name: last.name || last.user }),
          this.toastOptions(q, { mine: true })
        );
      } else if (q.user !== me.username && last && last.user === q.user) {
        this.$toastr.info(`${q.file_name}：${last.message}`, this.$t("help.followUp", { name: q.user_name }), this.toastOptions(q));
      }
    },
    connect() {
      this.load();
    }
  },
  created() {
    this.load();
    window.addEventListener("help-changed", this.load);
  },
  beforeUnmount() {
    window.removeEventListener("help-changed", this.load);
  }
};
</script>

<style scoped>
.bell {
  position: relative;
  padding: 2px 8px;
}
.bell .badge {
  position: absolute;
  top: -6px;
  right: -6px;
  font-size: 0.65rem;
}
.help-menu {
  width: 360px;
}
.help-list {
  max-height: 420px;
  overflow-y: auto;
}
.item {
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid #f1f3f5;
}
.item:hover {
  background: #f6f8fb;
}
.msg {
  font-size: 0.85rem;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
