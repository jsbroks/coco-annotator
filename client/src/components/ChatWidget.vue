<template>
  <div class="chat-widget" :class="'side-' + side">
    <!-- a short preview of a new message while the chat is closed -->
    <transition name="chat-fade">
      <button v-if="!open && preview" type="button" class="chat-preview shadow" @click="toggle(true)">
        <b>{{ preview.name }}</b>：{{ preview.text || ((preview.photos || []).length ? '📷 ' + $t('chat.photo') : '') || (preview.file_name ? '🖼 ' + preview.file_name : '') }}
      </button>
    </transition>

    <button
      v-show="!open"
      type="button"
      class="chat-fab shadow"
      :title="$t('chat.open')"
      :aria-label="$t('chat.open')"
      @click="toggle(true)"
    >
      <i class="fa fa-comments" />
      <span v-if="unread" class="chat-badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>

    <section
      v-if="open"
      class="chat-panel shadow-lg"
      :class="{ dropping }"
      role="dialog"
      :aria-label="$t('chat.title')"
      @keydown.stop
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @drop.prevent="onDrop"
    >
      <div v-if="dropping" class="chat-drop"><i class="fa fa-picture-o" /> {{ $t('chat.dropHere') }}</div>
      <header class="chat-head">
        <i class="fa fa-comments me-2" />
        <span class="text-truncate flex-grow-1">
          <b>{{ $t('chat.title') }}</b>
          <span v-if="datasetName" class="chat-room ms-1">· {{ datasetName }}</span>
        </span>
        <button type="button" class="btn-close btn-close-white" :aria-label="$t('chat.close')" @click="toggle(false)" />
      </header>

      <div ref="list" class="chat-list" @scroll="onScroll">
        <div v-if="more" class="text-center my-1">
          <button type="button" class="btn btn-link btn-sm p-0" :disabled="loadingOlder" @click="loadOlder">
            <i v-if="loadingOlder" class="fa fa-spinner fa-spin" /> {{ $t('chat.older') }}
          </button>
        </div>
        <div v-if="loaded && !messages.length" class="chat-empty">{{ $t('chat.empty') }}</div>

        <template v-for="(m, i) in messages" :key="m.id">
          <div v-if="dayChanged(i)" class="chat-day">{{ dayLabel(m.created_at) }}</div>
          <div v-if="m.id === firstUnreadId" class="chat-new-line"><span>{{ $t('chat.newMessages') }}</span></div>
          <div class="chat-msg" :class="{ mine: m.user === me, cont: grouped(i) }">
            <div v-if="!grouped(i)" class="chat-meta">
              <span class="chat-name">{{ m.user === me ? $t('chat.you') : m.name }}</span>
              <span class="chat-time">{{ timeLabel(m.created_at) }}</span>
            </div>
            <div class="chat-bubble" :class="{ 'only-photos': !m.text && !m.image_id && (m.photos || []).length }" :title="fullTime(m.created_at)">
              <div v-if="(m.photos || []).length" class="chat-photos" :class="'n' + Math.min(m.photos.length, 4)">
                <button
                  v-for="ph in m.photos"
                  :key="ph.id"
                  type="button"
                  class="chat-photo"
                  :aria-label="$t('chat.viewPhoto')"
                  @click="viewing = ph"
                >
                  <img
                    :src="`/api/chat/photo/${ph.id}?thumb=1`"
                    :alt="$t('chat.photo')"
                    loading="lazy"
                    :style="m.photos.length === 1 && ph.w && ph.h ? { aspectRatio: ph.w + ' / ' + ph.h } : null"
                    @load="onPhotoLoad"
                  />
                </button>
              </div>
              <span v-if="m.text" class="chat-text">{{ m.text }}</span>
              <a
                v-if="m.image_id"
                href="#"
                class="chat-image"
                :class="{ current: m.image_id === imageId }"
                :title="m.image_id === imageId ? $t('chat.thisImage') : $t('chat.openImage')"
                @click.prevent="openImage(m)"
              >
                <i class="fa fa-picture-o" /> {{ m.file_name || ('#' + m.image_id) }}
              </a>
            </div>
          </div>
        </template>
      </div>

      <button v-if="!atBottom && newBelow" type="button" class="chat-jump" @click="scrollToBottom(true)">
        <i class="fa fa-arrow-down" /> {{ $t('chat.newBelow', { n: newBelow }) }}
      </button>

      <footer class="chat-input">
        <div v-if="pending.length" class="chat-pending">
          <div v-for="p in pending" :key="p.key" class="pending" :class="{ failed: p.error }" :title="p.error || p.name">
            <img :src="p.url" alt="" />
            <span v-if="p.id == null && !p.error" class="pending-progress">{{ p.progress }}%</span>
            <span v-if="p.error" class="pending-progress"><i class="fa fa-exclamation-triangle" /></span>
            <button type="button" class="pending-remove" :aria-label="$t('chat.removePhoto')" @click="removePending(p)">×</button>
          </div>
        </div>
        <div v-if="emojiOpen" class="chat-emoji">
          <div class="emoji-tabs">
            <button
              v-for="g in emojiGroups"
              :key="g.key"
              type="button"
              class="emoji-tab"
              :class="{ on: emojiGroup === g.key }"
              :title="$t('chat.emoji.' + g.key)"
              @click="emojiGroup = g.key"
            >{{ g.icon }}</button>
          </div>
          <div class="emoji-grid">
            <button v-for="e in emojiShown" :key="e" type="button" class="emoji" @click="insertEmoji(e)">{{ e }}</button>
            <div v-if="!emojiShown.length" class="small text-muted p-2">{{ $t('chat.emoji.noneRecent') }}</div>
          </div>
        </div>
        <div v-if="attach && imageId" class="chat-attach">
          <i class="fa fa-picture-o" /> <span class="text-truncate">{{ imageName || ('#' + imageId) }}</span>
          <button type="button" class="btn-close btn-sm ms-auto" :aria-label="$t('chat.detach')" @click="attach = false" />
        </div>
        <div class="d-flex align-items-end gap-1">
          <button
            v-if="imageId"
            type="button"
            class="btn btn-sm chat-attach-btn"
            :class="attach ? 'btn-primary' : 'btn-outline-secondary'"
            :title="$t('chat.attach')"
            :aria-label="$t('chat.attach')"
            :aria-pressed="attach"
            @click="attach = !attach"
          >
            <i class="fa fa-picture-o" />
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary chat-tool"
            :title="$t('chat.addPhotos')"
            :aria-label="$t('chat.addPhotos')"
            @click="$refs.photoInput.click()"
          >
            <i class="fa fa-paperclip" />
          </button>
          <input ref="photoInput" type="file" accept="image/*" multiple class="d-none" @change="onPickPhotos" />
          <button
            type="button"
            class="btn btn-sm chat-tool"
            :class="emojiOpen ? 'btn-secondary' : 'btn-outline-secondary'"
            :title="$t('chat.emoji.title')"
            :aria-label="$t('chat.emoji.title')"
            :aria-pressed="emojiOpen"
            @click="toggleEmoji"
          >
            <i class="fa fa-smile-o" />
          </button>
          <textarea
            ref="input"
            v-model="text"
            class="form-control form-control-sm"
            rows="1"
            :maxlength="MAX"
            :placeholder="$t('chat.placeholder')"
            :title="$t('chat.keysHint')"
            @keydown.enter="onEnter"
            @input="autosize"
            @paste="onPaste"
          />
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="sending || uploading || (!text.trim() && !(attach && imageId) && !readyPhotos.length)"
            :aria-label="$t('chat.send')"
            :title="$t('chat.send')"
            @click="send"
          >
            <i class="fa" :class="sending ? 'fa-spinner fa-spin' : 'fa-paper-plane'" />
          </button>
        </div>
      </footer>
    </section>

    <!-- a photo, big -->
    <div v-if="viewing" class="chat-viewer" role="dialog" :aria-label="$t('chat.photo')" @click.self="viewing = null" @keydown.esc="viewing = null">
      <img :src="`/api/chat/photo/${viewing.id}`" :alt="$t('chat.photo')" />
      <div class="viewer-actions">
        <a class="btn btn-sm btn-light" :href="`/api/chat/photo/${viewing.id}`" target="_blank" rel="noopener"><i class="fa fa-external-link" /> {{ $t('chat.openOriginal') }}</a>
        <button ref="viewerClose" type="button" class="btn btn-sm btn-light" @click="viewing = null"><i class="fa fa-times" /> {{ $t('chat.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { EMOJI_GROUPS, recentEmoji, rememberEmoji } from "@/libs/emoji";

const MAX = 1000;
const MAX_PHOTOS = 6;
let photoKey = 0;

function readOpen() {
  try {
    return localStorage.getItem("chat/open") === "1";
  } catch {
    return false;
  }
}

/** The dataset's chat room: a button in the corner and a small panel. */
export default {
  name: "ChatWidget",
  props: {
    datasetId: { type: Number, default: null },
    datasetName: { type: String, default: "" },
    // on the annotator: the image open there (can be attached to a message)
    imageId: { type: Number, default: null },
    imageName: { type: String, default: "" },
    side: { type: String, default: "right" }
  },
  data() {
    return {
      MAX,
      open: readOpen(),
      messages: [],
      me: null,
      more: false,
      loaded: false,
      loadingOlder: false,
      unread: 0,
      lastRead: 0,
      firstUnreadId: null,
      text: "",
      attach: false,
      sending: false,
      atBottom: true,
      newBelow: 0,
      preview: null,
      previewTimer: null,
      readTimer: null,
      // photos to send: {key, name, url, id (once uploaded), progress, error}
      pending: [],
      dropping: false,
      viewing: null,
      emojiOpen: false,
      emojiGroup: "smileys",
      recent: recentEmoji()
    };
  },
  computed: {
    readyPhotos() {
      return this.pending.filter(p => p.id != null);
    },
    uploading() {
      return this.pending.some(p => p.id == null && !p.error);
    },
    emojiGroups() {
      return [{ key: "recent", icon: "🕘", list: this.recent }, ...EMOJI_GROUPS];
    },
    emojiShown() {
      const g = this.emojiGroups.find(x => x.key === this.emojiGroup);
      return g ? g.list : [];
    }
  },
  watch: {
    viewing(v) {
      if (v) this.$nextTick(() => this.$refs.viewerClose && this.$refs.viewerClose.focus());
    },
    datasetId: {
      immediate: true,
      handler(id, old) {
        this.clearPending();
        if (old != null) this.$socket.emit("watch_chat", { dataset_id: null, leave: old });
        this.messages = [];
        this.loaded = false;
        this.unread = 0;
        if (id != null) {
          this.watch();
          this.load();
        }
      }
    },
    imageId() {
      this.attach = false;
    }
  },
  beforeUnmount() {
    this.clearPending();
    clearTimeout(this.previewTimer);
    clearTimeout(this.readTimer);
    if (this.datasetId != null) this.$socket.emit("watch_chat", { dataset_id: null, leave: this.datasetId });
  },
  methods: {
    watch() {
      this.$socket.emit("watch_chat", { dataset_id: this.datasetId });
    },
    async load() {
      const id = this.datasetId;
      try {
        const r = await axios.get(`/api/chat/dataset/${id}`);
        if (id !== this.datasetId) return;
        this.messages = r.data.messages;
        this.more = r.data.more;
        this.me = r.data.me;
        this.lastRead = r.data.last_read;
        this.unread = r.data.unread;
        this.markFirstUnread();
        this.loaded = true;
        if (this.open) {
          this.scrollToBottom(true);
          this.markRead();
        }
      } catch {
        // the chat is extra: the page works without it
      }
    },
    markFirstUnread() {
      const m = this.messages.find(m => m.id > this.lastRead && m.user !== this.me);
      this.firstUnreadId = m ? m.id : null;
    },
    async loadOlder() {
      if (!this.messages.length || this.loadingOlder) return;
      this.loadingOlder = true;
      const list = this.$refs.list;
      const before = list ? list.scrollHeight - list.scrollTop : 0;
      try {
        const r = await axios.get(`/api/chat/dataset/${this.datasetId}`, { params: { before: this.messages[0].id } });
        this.messages = [...r.data.messages, ...this.messages];
        this.more = r.data.more;
        this.$nextTick(() => {
          // keep the messages that were on screen where they were
          if (list) list.scrollTop = list.scrollHeight - before;
        });
      } finally {
        this.loadingOlder = false;
      }
    },
    toggle(open) {
      this.open = open;
      try {
        localStorage.setItem("chat/open", open ? "1" : "0");
      } catch {
        // not remembered
      }
      if (open) {
        this.preview = null;
        this.markFirstUnread();
        this.$nextTick(() => {
          this.scrollToBottom(true);
          if (this.$refs.input) this.$refs.input.focus();
        });
        this.markRead();
      }
    },
    markRead() {
      const last = this.messages[this.messages.length - 1];
      if (!last || last.id <= this.lastRead) {
        this.unread = 0;
        return;
      }
      this.lastRead = last.id;
      this.unread = 0;
      clearTimeout(this.readTimer);
      this.readTimer = setTimeout(() => {
        axios.post(`/api/chat/dataset/${this.datasetId}/read`, { last_id: last.id }).catch(() => {});
      }, 300);
    },
    onEnter(e) {
      // Enter sends, Shift+Enter is a new line; not while picking characters (IME)
      if (e.shiftKey || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      this.send();
    },
    autosize() {
      const el = this.$refs.input;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 110) + "px";
    },
    async send() {
      const text = this.text.trim();
      const imageId = this.attach && this.imageId ? this.imageId : null;
      const photos = this.readyPhotos.map(p => p.id);
      if ((!text && !imageId && !photos.length) || this.sending || this.uploading) return;
      this.sending = true;
      try {
        const r = await axios.post(`/api/chat/dataset/${this.datasetId}`, { text, image_id: imageId, photos });
        this.add(r.data);
        this.text = "";
        this.attach = false;
        this.clearPending();
        this.emojiOpen = false;
        this.$nextTick(() => {
          this.autosize();
          this.scrollToBottom(true);
        });
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || this.$t("chat.failed"));
      } finally {
        this.sending = false;
      }
    },
    /* ---------- photos ---------- */
    onPickPhotos(e) {
      this.addPhotos([...e.target.files]);
      e.target.value = "";
    },
    onPaste(e) {
      const files = [...((e.clipboardData && e.clipboardData.items) || [])]
        .filter(i => i.kind === "file" && i.type.startsWith("image/"))
        .map(i => i.getAsFile())
        .filter(Boolean);
      if (files.length) {
        e.preventDefault();
        this.addPhotos(files);
      }
    },
    onDragOver(e) {
      if ([...(e.dataTransfer.types || [])].includes("Files")) this.dropping = true;
    },
    onDragLeave(e) {
      if (!e.currentTarget.contains(e.relatedTarget)) this.dropping = false;
    },
    onDrop(e) {
      this.dropping = false;
      this.addPhotos([...(e.dataTransfer.files || [])]);
    },
    addPhotos(files) {
      const images = files.filter(f => f.type.startsWith("image/"));
      if (images.length < files.length) this.$toastr.info(this.$t("chat.onlyPhotos"));
      const room = MAX_PHOTOS - this.pending.length;
      if (images.length > room) this.$toastr.info(this.$t("chat.maxPhotos", { n: MAX_PHOTOS }));
      images.slice(0, Math.max(0, room)).forEach(file => {
        const p = { key: ++photoKey, name: file.name, url: URL.createObjectURL(file), id: null, progress: 0, error: "" };
        this.pending.push(p);
        this.uploadPhoto(this.pending[this.pending.length - 1], file);
      });
      this.$nextTick(() => this.$refs.input && this.$refs.input.focus());
    },
    async uploadPhoto(p, file) {
      const data = new FormData();
      data.append("file", file);
      try {
        const r = await axios.post(`/api/chat/dataset/${this.datasetId}/photo`, data, {
          onUploadProgress: e => (p.progress = e.total ? Math.round((100 * e.loaded) / e.total) : 0)
        });
        p.id = r.data.id;
      } catch (error) {
        const d = (error.response && error.response.data) || {};
        p.error = d.message || this.$t("chat.photoFailed");
      }
    },
    removePending(p) {
      URL.revokeObjectURL(p.url);
      this.pending = this.pending.filter(x => x !== p);
    },
    clearPending() {
      (this.pending || []).forEach(p => URL.revokeObjectURL(p.url));
      this.pending = [];
    },
    onPhotoLoad() {
      if (this.atBottom) this.$nextTick(() => this.scrollToBottom(true));
    },
    /* ---------- emoji ---------- */
    toggleEmoji() {
      this.emojiOpen = !this.emojiOpen;
      if (this.emojiOpen && !this.recent.length && this.emojiGroup === "recent") this.emojiGroup = "smileys";
    },
    insertEmoji(e) {
      const el = this.$refs.input;
      const start = el ? el.selectionStart : this.text.length;
      const end = el ? el.selectionEnd : this.text.length;
      if (this.text.length + e.length > MAX) return;
      this.text = this.text.slice(0, start) + e + this.text.slice(end);
      this.recent = rememberEmoji(e);
      this.$nextTick(() => {
        if (!el) return;
        el.focus();
        el.selectionStart = el.selectionEnd = start + e.length;
        this.autosize();
      });
    },
    /** a message (ours from the reply, anyone's from the socket), once */
    add(m) {
      if (this.messages.some(x => x.id === m.id)) return false;
      this.messages.push(m);
      return true;
    },
    onScroll() {
      const el = this.$refs.list;
      if (!el) return;
      this.atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      if (this.atBottom) this.newBelow = 0;
    },
    scrollToBottom(force) {
      const el = this.$refs.list;
      if (!el || (!force && !this.atBottom)) return;
      el.scrollTop = el.scrollHeight;
      this.atBottom = true;
      this.newBelow = 0;
    },
    openImage(m) {
      if (m.image_id === this.imageId) return;
      this.$router.push({ name: "annotate", params: { identifier: m.image_id } });
    },
    when(iso) {
      return iso ? new Date(iso) : null;
    },
    timeLabel(iso) {
      const d = this.when(iso);
      return d ? d.toLocaleTimeString(this.$i18n.locale, { hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    },
    fullTime(iso) {
      const d = this.when(iso);
      return d ? d.toLocaleString(this.$i18n.locale, { hour12: false }) : "";
    },
    dayLabel(iso) {
      const d = this.when(iso);
      if (!d) return "";
      const today = new Date();
      const yesterday = new Date(today.getTime() - 86400000);
      if (d.toDateString() === today.toDateString()) return this.$t("chat.today");
      if (d.toDateString() === yesterday.toDateString()) return this.$t("chat.yesterday");
      return d.toLocaleDateString(this.$i18n.locale);
    },
    dayChanged(i) {
      if (i === 0) return true;
      const a = this.when(this.messages[i - 1].created_at);
      const b = this.when(this.messages[i].created_at);
      return !a || !b || a.toDateString() !== b.toDateString();
    },
    /** the same person again within 5 minutes: no name / time line */
    grouped(i) {
      if (i === 0 || this.dayChanged(i)) return false;
      const prev = this.messages[i - 1];
      const m = this.messages[i];
      if (prev.user !== m.user || m.id === this.firstUnreadId) return false;
      return this.when(m.created_at) - this.when(prev.created_at) < 5 * 60 * 1000;
    }
  },
  sockets: {
    connect() {
      // a new connection starts without rooms; catch up on what was missed
      if (this.datasetId != null) {
        this.watch();
        if (this.loaded) this.load();
      }
    },
    chat(m) {
      if (!m || m.dataset_id !== this.datasetId) return;
      if (!this.add(m)) return;
      if (m.user === this.me) return;
      if (this.open && !document.hidden) {
        if (this.atBottom) this.$nextTick(() => this.scrollToBottom(true));
        else this.newBelow += 1;
        this.markRead();
      } else {
        this.unread += 1;
        if (!this.open) {
          this.preview = m;
          clearTimeout(this.previewTimer);
          this.previewTimer = setTimeout(() => (this.preview = null), 5000);
        }
      }
    }
  },
  mounted() {
    this.onVisible = () => {
      if (!document.hidden && this.open && this.unread) this.markRead();
    };
    document.addEventListener("visibilitychange", this.onVisible);
  },
  unmounted() {
    document.removeEventListener("visibilitychange", this.onVisible);
  }
};
</script>

<style scoped>
.chat-widget {
  position: fixed;
  bottom: 18px;
  z-index: 1040;
}
.chat-widget.side-right {
  right: 18px;
}
/* the annotator: right of its tool bar */
.chat-widget.side-left {
  left: 54px;
}
.chat-fab {
  position: relative;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 0;
  background: #2563eb;
  color: #fff;
  font-size: 1.35rem;
  transition: transform 0.15s, background 0.15s;
}
.chat-fab:hover {
  background: #1d4ed8;
  transform: translateY(-2px);
}
.chat-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 11px;
  background: #dc3545;
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 22px;
  border: 2px solid #fff;
}
.chat-preview {
  position: absolute;
  bottom: 60px;
  max-width: 260px;
  width: max-content;
  padding: 8px 12px;
  border: 0;
  border-radius: 12px;
  background: #fff;
  color: #212529;
  font-size: 0.85rem;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-right .chat-preview {
  right: 0;
}
.side-left .chat-preview {
  left: 0;
}
.chat-panel {
  position: relative;
  width: 340px;
  max-width: calc(100vw - 36px);
  height: 480px;
  max-height: calc(var(--vh) - 36px);
  display: flex;
  flex-direction: column;
  background: #fff;
  color: #212529;
  border-radius: 12px;
  overflow: hidden;
  text-align: left;
}
.chat-head {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: #2563eb;
  color: #fff;
  font-size: 0.95rem;
}
.chat-room {
  font-weight: 400;
  opacity: 0.85;
}
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  background: #f5f7fb;
  scrollbar-width: thin;
}
.chat-empty {
  margin-top: 40%;
  text-align: center;
  color: #6c757d;
  font-size: 0.85rem;
}
.chat-day {
  margin: 10px 0 6px;
  text-align: center;
  font-size: 0.72rem;
  color: #6c757d;
}
.chat-new-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 4px;
  color: #dc3545;
  font-size: 0.72rem;
}
.chat-new-line::before,
.chat-new-line::after {
  content: "";
  flex: 1;
  border-top: 1px solid rgba(220, 53, 69, 0.5);
}
.chat-msg {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: 8px;
}
.chat-msg.cont {
  margin-top: 2px;
}
.chat-msg.mine {
  align-items: flex-end;
}
.chat-meta {
  font-size: 0.72rem;
  color: #6c757d;
  margin: 0 4px 2px;
}
.chat-name {
  font-weight: 600;
  color: #495057;
  margin-right: 6px;
}
.chat-bubble {
  max-width: 85%;
  padding: 6px 10px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e3e7ee;
  font-size: 0.875rem;
  line-height: 1.4;
}
.chat-msg.mine .chat-bubble {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.chat-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.chat-image {
  display: block;
  margin-top: 2px;
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}
.chat-text + .chat-image {
  margin-top: 4px;
}
.chat-msg.mine .chat-image {
  color: #dbe7ff;
}
.chat-image.current {
  cursor: default;
  text-decoration: none;
  opacity: 0.8;
}
.chat-jump {
  position: absolute;
  bottom: 70px;
  left: 50%;
  transform: translateX(-50%);
  border: 0;
  border-radius: 999px;
  padding: 3px 12px;
  background: #212529;
  color: #fff;
  font-size: 0.75rem;
  opacity: 0.85;
}
.chat-input {
  padding: 8px;
  border-top: 1px solid #e3e7ee;
  background: #fff;
}
.chat-tool {
  flex: none;
  padding: 0.15rem 0.45rem;
}
.chat-pending {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.pending {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  background: #f1f3f5;
}
.pending img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.pending.failed img {
  opacity: 0.35;
}
.pending-progress {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
  background: rgba(0, 0, 0, 0.35);
}
.pending.failed .pending-progress {
  color: #dc3545;
  background: rgba(255, 255, 255, 0.4);
}
.pending-remove {
  position: absolute;
  top: 1px;
  right: 1px;
  width: 18px;
  height: 18px;
  line-height: 15px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 14px;
}
.chat-emoji {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  margin-bottom: 6px;
  background: #fff;
}
.emoji-tabs {
  display: flex;
  border-bottom: 1px solid #e9ecef;
}
.emoji-tab {
  flex: 1;
  border: 0;
  background: none;
  padding: 3px 0;
  font-size: 1.1rem;
  opacity: 0.55;
}
.emoji-tab.on {
  opacity: 1;
  box-shadow: inset 0 -2px 0 #2563eb;
}
.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  max-height: 160px;
  overflow-y: auto;
  padding: 4px;
}
.emoji {
  border: 0;
  background: none;
  font-size: 1.3rem;
  line-height: 1.6;
  border-radius: 6px;
  padding: 0;
}
.emoji:hover {
  background: #f1f3f5;
}
.chat-photos {
  display: grid;
  gap: 3px;
  margin: -2px -4px 4px;
  max-width: 230px;
}
.chat-bubble.only-photos .chat-photos {
  margin-bottom: -2px;
}
.chat-photos.n1 {
  grid-template-columns: 1fr;
}
.chat-photos.n2,
.chat-photos.n4 {
  grid-template-columns: 1fr 1fr;
}
.chat-photos.n3 {
  grid-template-columns: 1fr 1fr 1fr;
}
.chat-photo {
  border: 0;
  padding: 0;
  background: #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  cursor: zoom-in;
}
.chat-photo img {
  display: block;
  width: 100%;
  max-height: 260px;
  object-fit: cover;
}
.chat-photos:not(.n1) .chat-photo img {
  aspect-ratio: 1;
}
.chat-panel.dropping {
  outline: 2px dashed #2563eb;
  outline-offset: -6px;
}
.chat-drop {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-weight: 600;
  pointer-events: none;
}
.chat-viewer {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px 64px;
}
.chat-viewer img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
.viewer-actions {
  position: absolute;
  bottom: 16px;
  display: flex;
  gap: 8px;
}
.chat-input textarea {
  resize: none;
  max-height: 110px;
}
.chat-attach {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  background: #e7f1ff;
  color: #0a58ca;
  font-size: 0.8rem;
}
.chat-attach-btn {
  flex: none;
}
.chat-fade-enter-active,
.chat-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.chat-fade-enter-from,
.chat-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
