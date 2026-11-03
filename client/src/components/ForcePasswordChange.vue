<template>
  <div class="force-pw-backdrop" role="dialog" aria-modal="true" aria-labelledby="forcePwTitle">
    <form class="force-pw card shadow-lg text-start" @submit.prevent="submit">
      <div class="card-body p-4">
        <div class="icon mb-3"><i class="fa fa-key" /></div>
        <h5 id="forcePwTitle" class="mb-1">{{ $t('forcePassword.title') }}</h5>
        <p class="text-muted small mb-3">{{ $t('forcePassword.body', { name: user.name || user.username }) }}</p>

        <div class="mb-2">
          <label class="form-label small fw-semibold mb-1" for="forcePwOld">{{ $t('forcePassword.current') }}</label>
          <input id="forcePwOld" ref="first" v-model="current" type="password" class="form-control" autocomplete="current-password" />
        </div>
        <div class="mb-2">
          <label class="form-label small fw-semibold mb-1" for="forcePwNew">{{ $t('user.newPassword') }}</label>
          <input
            id="forcePwNew"
            v-model="next"
            type="password"
            class="form-control"
            :class="{ 'is-invalid': next && problem === 'short', 'is-valid': next && !problem }"
            autocomplete="new-password"
          />
          <div class="form-text">{{ $t('user.minimumLengthOf5Characters') }}</div>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold mb-1" for="forcePwConfirm">{{ $t('user.confirmPassword') }}</label>
          <input
            id="forcePwConfirm"
            v-model="confirm"
            type="password"
            class="form-control"
            :class="{ 'is-invalid': confirm && confirm !== next, 'is-valid': confirm && confirm === next && !problem }"
            autocomplete="new-password"
          />
        </div>

        <div v-if="message" class="alert alert-danger py-2 small">{{ message }}</div>
        <div v-else-if="problem && problem !== 'empty' && problem !== 'short'" class="small text-danger mb-2">
          {{ $t('forcePassword.problem.' + problem) }}
        </div>

        <button type="submit" class="btn btn-primary w-100" :disabled="!!problem || saving">
          <i class="fa" :class="saving ? 'fa-spinner fa-spin' : 'fa-check'" /> {{ $t('forcePassword.submit') }}
        </button>
        <div class="text-center mt-2">
          <a href="#" class="small text-muted" @click.prevent="logout">{{ $t('user.logout') }}</a>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";

/** Shown over everything after logging in with a password an admin chose. */
export default {
  name: "ForcePasswordChange",
  props: { user: { type: Object, required: true } },
  data() {
    return { current: "", next: "", confirm: "", saving: false, message: "" };
  },
  computed: {
    problem() {
      if (!this.current || !this.next) return "empty";
      if (this.next.length < 5) return "short";
      if (this.next === this.current) return "same";
      if (this.confirm !== this.next) return "confirm";
      return null;
    }
  },
  watch: {
    current() { this.message = ""; },
    next() { this.message = ""; }
  },
  mounted() {
    this.$nextTick(() => this.$refs.first && this.$refs.first.focus());
  },
  methods: {
    ...mapActions("user", ["logout"]),
    submit() {
      if (this.problem || this.saving) return;
      this.saving = true;
      axios
        .post("/api/user/password", { password: this.current, new_password: this.next })
        .then(() => {
          this.$toastr.success(this.$t("forcePassword.done"));
          // sign in again with the new password
          this.logout();
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.message = data.code ? this.$t("forcePassword.problem." + data.code)
            : /match/i.test(data.message || "") ? this.$t("forcePassword.wrongCurrent") : (data.message || String(error));
        })
        .finally(() => (this.saving = false));
    }
  }
};
</script>

<style scoped>
.force-pw-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(20, 24, 33, 0.72);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.force-pw {
  width: 100%;
  max-width: 400px;
  border: 0;
  border-radius: 12px;
}
.icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #e8f0fb;
  color: #2a78d6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}
</style>
