<template>
  <div class="reject-reasons" @mousedown.stop @click.stop>
    <button
      v-for="(r, k) in reasons"
      :key="r"
      type="button"
      class="reason"
      :title="$t('rejectReasons.pickHint', { n: k + 1 })"
      @mousedown.prevent
      @click="$emit('pick', r)"
    >
      <span class="num">{{ k + 1 }}</span>{{ r }}
      <i v-if="editing" class="fa fa-times remove" :title="$t('rejectReasons.remove')" @click.stop="remove(r)" />
    </button>
    <button
      v-if="canSave"
      type="button"
      class="reason add"
      :title="$t('rejectReasons.saveHint')"
      @mousedown.prevent
      @click="add"
    >
      <i class="fa fa-plus" /> {{ $t('rejectReasons.save') }}
    </button>
    <button
      v-if="reasons.length"
      type="button"
      class="reason edit"
      :title="editing ? $t('rejectReasons.done') : $t('rejectReasons.edit')"
      @mousedown.prevent
      @click="editing = !editing"
    >
      <i class="fa" :class="editing ? 'fa-check' : 'fa-pencil'" />
    </button>
  </div>
</template>

<script>
import { loadRejectReasons, reasonsOr, rejectReasons, saveRejectReasons } from "@/libs/rejectReasons";

/**
 * A reviewer's saved reasons for rejecting: click one (or press its number in
 * an empty reason box) to use it; "save" keeps what is typed for next time.
 */
export default {
  name: "RejectReasons",
  props: {
    // the reason typed now (offered for saving)
    note: { type: String, default: "" }
  },
  emits: ["pick"],
  data() {
    return { editing: false };
  },
  computed: {
    reasons() {
      void rejectReasons.list;
      return reasonsOr(this.$t("rejectReasons.defaults").split("\n").filter(Boolean));
    },
    canSave() {
      const text = this.note.trim();
      return !!text && text.length <= 200 && !this.reasons.includes(text) && this.reasons.length < 9;
    }
  },
  created() {
    const me = this.$store.state.user.user;
    loadRejectReasons(me ? me.username : null);
  },
  methods: {
    async add() {
      try {
        await saveRejectReasons([...this.reasons, this.note.trim()]);
        this.$toastr.success(this.$t("rejectReasons.saved"));
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      }
    },
    async remove(r) {
      try {
        await saveRejectReasons(this.reasons.filter(x => x !== r));
      } catch (e) {
        this.$toastr.error((e.response && e.response.data.message) || String(e));
      }
    },
    /** a number key in an empty reason box: that reason (returns it, or null) */
    forKey(e, note) {
      if ((note || "").trim() || e.ctrlKey || e.metaKey || e.altKey || !/^[1-9]$/.test(e.key)) return null;
      return this.reasons[Number(e.key) - 1] || null;
    }
  }
};
</script>

<style scoped>
.reject-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.reason {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1px 8px 1px 3px;
  border: 1px solid #5a6273;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: #e9ecef;
  font-size: 0.75rem;
  line-height: 1.5;
}
.reason:hover {
  border-color: #ff6b6b;
  background: rgba(255, 107, 107, 0.12);
}
.num {
  display: inline-block;
  min-width: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #454c5c;
  color: #ced4da;
  font-size: 0.68rem;
  text-align: center;
}
.reason.add,
.reason.edit {
  padding-left: 8px;
  border-style: dashed;
  color: #adb5bd;
}
.remove {
  margin-left: 2px;
  color: #ff6b6b;
}
</style>
