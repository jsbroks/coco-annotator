<template>
  <div class="dataset-members">
    <!-- invite (the owner) -->
    <div v-if="canManage" class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2"><b>{{ $t('dataset.inviteMembers') }}</b></h6>
      <div class="small text-muted mb-2">{{ $t('members.inviteHint') }}</div>

      <div class="position-relative invite-box">
        <div class="form-control d-flex flex-wrap align-items-center gap-1 chips-input" @click="$refs.search.focus()">
          <span v-for="name in pending" :key="name" class="chip" :class="{ bad: unknown.includes(name) }">
            {{ labelOf(name) }}
            <i class="fa fa-times" role="button" :aria-label="$t('members.removePending')" @click.stop="unpick(name)" />
          </span>
          <input
            ref="search"
            v-model="query"
            class="flex-grow-1 border-0"
            :placeholder="pending.length ? '' : $t('members.searchPlaceholder')"
            @input="onInput"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="onEnter"
            @keydown.backspace="onBackspace"
            @keydown.esc="suggestions = []"
            @paste="onPaste"
            @blur="onBlur"
          />
        </div>
        <div v-if="suggestions.length" class="suggest shadow">
          <button
            v-for="(u, k) in suggestions"
            :key="u.username"
            type="button"
            class="suggest-item"
            :class="{ active: k === index }"
            @mousedown.prevent="pick(u)"
            @mouseenter="index = k"
          >
            <span class="avatar sm">{{ initial(u) }}</span>
            <span class="fw-semibold">{{ u.name || u.username }}</span>
            <span class="text-muted small">@{{ u.username }}</span>
          </button>
        </div>
      </div>

      <div v-if="unknown.length" class="small text-danger mt-1">
        {{ $t('members.unknown', { names: unknown.join('、') }) }}
      </div>
      <div class="d-flex mt-2">
        <button type="button" class="btn btn-sm btn-primary" :disabled="!pending.length || busy" @click="invite">
          <i class="fa fa-user-plus" /> {{ $t('members.add', { n: pending.length }) }}
        </button>
      </div>
    </div>

    <!-- members -->
    <div class="card my-3 p-3 shadow-sm">
      <h6 class="border-bottom pb-2 d-flex align-items-center">
        <b class="me-auto">{{ $t('dataset.existingMembers') }}</b>
        <span class="text-muted small">{{ $t('members.count', { n: members.length }) }}</span>
      </h6>
      <div v-if="loading && !members.length" class="text-muted small"><i class="fa fa-spinner fa-spin" /></div>
      <div v-for="m in members" :key="m.username" class="member d-flex align-items-center gap-2">
        <span class="avatar" :class="'role-' + m.role">{{ initial(m) }}</span>
        <div class="flex-grow-1 min-w-0">
          <div class="text-truncate">
            <strong>{{ m.name || m.username }}</strong>
            <span class="text-muted small ms-1">@{{ m.username }}</span>
            <span v-if="m.role === 'owner'" class="badge text-bg-dark ms-1">{{ $t('review.owner') }}</span>
            <span v-else-if="m.role === 'reviewer'" class="badge text-bg-info ms-1">{{ $t('review.reviewer') }}</span>
          </div>
          <div class="small text-muted">
            {{ m.last_seen ? $t('members.lastSeen', { ago: agoText(m.last_seen) }) : $t('members.neverSeen') }}
          </div>
        </div>
        <button
          v-if="canManage && m.role !== 'owner'"
          type="button"
          class="btn btn-sm btn-outline-danger"
          :disabled="busy"
          :title="$t('members.remove')"
          @click="remove(m)"
        >
          <i class="fa fa-user-times" />
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

/** Members of a dataset: the owner invites (search or paste) and removes. */
export default {
  name: "DatasetMembers",
  props: {
    datasetId: { type: Number, required: true }
  },
  emits: ["changed"],
  data() {
    return {
      members: [],
      canManage: false,
      loading: false,
      busy: false,
      query: "",
      suggestions: [],
      index: 0,
      // usernames waiting to be added, with what we know about them
      pending: [],
      known: {},
      unknown: [],
      timer: null,
      seq: 0
    };
  },
  watch: {
    datasetId: {
      immediate: true,
      handler(id) {
        if (id) this.load();
      }
    }
  },
  beforeUnmount() {
    clearTimeout(this.timer);
  },
  methods: {
    /** "5 分鐘" since an ISO time */
    agoText(iso) {
      const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
      const units = [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60], ["second", 1]];
      const [unit, size] = units.find(([, size]) => secs >= size) || ["second", 1];
      const n = Math.floor(secs / size);
      return this.$t(`time.${unit}`, { n }, n);
    },
    initial(u) {
      return ((u.name || u.username || "?").trim()[0] || "?").toUpperCase();
    },
    labelOf(name) {
      const u = this.known[name];
      return u && u.name && u.name !== name ? `${u.name}（${name}）` : name;
    },
    async load() {
      this.loading = true;
      try {
        const r = await axios.get(`/api/dataset/${this.datasetId}/members`);
        this.members = r.data.members;
        this.canManage = !!r.data.can_manage;
      } finally {
        this.loading = false;
      }
    },
    onInput() {
      clearTimeout(this.timer);
      this.timer = setTimeout(this.search, 200);
    },
    async search() {
      const q = this.query.trim();
      const seq = ++this.seq;
      if (!q) {
        this.suggestions = [];
        return;
      }
      try {
        const r = await axios.get(`/api/dataset/${this.datasetId}/candidates`, { params: { q } });
        if (seq !== this.seq) return;
        this.suggestions = r.data.users.filter(u => !this.pending.includes(u.username)).slice(0, 8);
        this.index = 0;
      } catch {
        this.suggestions = [];
      }
    },
    move(d) {
      const n = this.suggestions.length;
      if (n) this.index = (this.index + d + n) % n;
    },
    pick(u) {
      this.known = { ...this.known, [u.username]: u };
      this.add([u.username]);
      this.query = "";
      this.suggestions = [];
      this.$nextTick(() => this.$refs.search && this.$refs.search.focus());
    },
    add(names) {
      const pending = [...this.pending];
      names.forEach(n => {
        const name = n.trim();
        if (name && !pending.includes(name) && !this.members.some(m => m.username.toLowerCase() === name.toLowerCase())) {
          pending.push(name);
        }
      });
      this.pending = pending;
    },
    unpick(name) {
      this.pending = this.pending.filter(n => n !== name);
      this.unknown = this.unknown.filter(n => n !== name);
    },
    onEnter() {
      if (this.suggestions.length) this.pick(this.suggestions[this.index]);
      else if (this.query.trim()) {
        this.add([this.query]);
        this.query = "";
      } else if (this.pending.length) this.invite();
    },
    onBackspace() {
      if (!this.query && this.pending.length) this.unpick(this.pending[this.pending.length - 1]);
    },
    /** several names at once (a column copied from Excel, a list) */
    onPaste(e) {
      const text = (e.clipboardData || window.clipboardData).getData("text");
      const names = text.split(/[\s,，、;；]+/).filter(Boolean);
      if (names.length < 2) return;
      e.preventDefault();
      this.add(names);
      this.query = "";
      this.suggestions = [];
    },
    onBlur() {
      // a typed name that was not picked still counts
      setTimeout(() => {
        if (this.query.trim() && document.activeElement !== this.$refs.search) {
          this.add([this.query]);
          this.query = "";
        }
        this.suggestions = [];
      }, 150);
    },
    async invite() {
      if (!this.pending.length || this.busy) return;
      this.busy = true;
      this.unknown = [];
      try {
        const r = await axios.post(`/api/dataset/${this.datasetId}/members`, { add: this.pending });
        this.members = r.data.members;
        this.$toastr.success(this.$t("members.added", { n: r.data.added.length }));
        this.pending = [];
        this.$emit("changed");
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        if (data.unknown) this.unknown = data.unknown;
        else this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    },
    async remove(m) {
      if (!confirm(this.$t("members.removeConfirm", { name: m.name || m.username }))) return;
      this.busy = true;
      try {
        const r = await axios.post(`/api/dataset/${this.datasetId}/members`, { remove: [m.username] });
        this.members = r.data.members;
        this.$toastr.success(this.$t("members.removed", { name: m.name || m.username }));
        this.$emit("changed");
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    }
  }
};
</script>

<style scoped>
.chips-input {
  min-height: 38px;
  cursor: text;
}
.chips-input input {
  outline: none;
  min-width: 160px;
  background: transparent;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #e7f1ff;
  color: #0a58ca;
  font-size: 0.85rem;
}
.chip.bad {
  background: #f8d7da;
  color: #842029;
}
.chip .fa {
  cursor: pointer;
  opacity: 0.7;
}
.suggest {
  position: absolute;
  z-index: 20;
  left: 0;
  right: 0;
  top: 100%;
  margin-top: 2px;
  background: var(--bs-body-bg, #fff);
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 6px;
  overflow: hidden;
}
.suggest-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 10px;
  border: 0;
  background: transparent;
  text-align: left;
}
.suggest-item.active {
  background: #e7f1ff;
}
.member {
  padding: 8px 0;
  border-bottom: 1px solid var(--bs-border-color, #eee);
}
.member:last-child {
  border-bottom: 0;
}
.avatar {
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #6c757d;
  color: #fff;
  font-weight: 600;
}
.avatar.role-owner {
  background: #212529;
}
.avatar.role-reviewer {
  background: #0aa2c0;
}
.avatar.sm {
  width: 24px;
  height: 24px;
  font-size: 0.75rem;
}
.min-w-0 {
  min-width: 0;
}
</style>
