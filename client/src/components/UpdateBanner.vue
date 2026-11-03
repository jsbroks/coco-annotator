<template>
  <div v-if="secondsLeft != null" class="update-banner" role="alert">
    <i class="fa fa-refresh fa-spin" />
    <span>{{ $t('update.message', { n: secondsLeft }) }}</span>
    <button type="button" class="btn btn-sm btn-light" @click="reloadNow">{{ $t('update.now') }}</button>
  </div>
</template>

<script>
/* global __BUILD_ID__ */
const CHECK_EVERY = 60 * 1000;
const COUNTDOWN = 10;

/**
 * After the server is updated, pages still running the old version reload
 * by themselves (after a short countdown; edits in the annotator are saved
 * when the page goes, as on any reload).
 */
export default {
  name: "UpdateBanner",
  data() {
    return { secondsLeft: null, timer: null, ticker: null };
  },
  mounted() {
    this.timer = setInterval(() => !document.hidden && this.check(), CHECK_EVERY);
    document.addEventListener("visibilitychange", this.onVisible);
  },
  beforeUnmount() {
    clearInterval(this.timer);
    clearInterval(this.ticker);
    document.removeEventListener("visibilitychange", this.onVisible);
  },
  methods: {
    onVisible() {
      if (!document.hidden) this.check();
    },
    /** called on a schedule, and when the socket reconnects (the server restarted) */
    async check() {
      if (this.secondsLeft != null || typeof __BUILD_ID__ === "undefined") return;
      try {
        const r = await fetch(`/version.json?t=${Date.now()}`, { cache: "no-store" });
        if (!r.ok) return; // development server: no version file
        const { build } = await r.json();
        if (build && build !== __BUILD_ID__) this.start();
      } catch {
        // server restarting: try again later
      }
    },
    start() {
      this.secondsLeft = COUNTDOWN;
      this.ticker = setInterval(() => {
        this.secondsLeft -= 1;
        if (this.secondsLeft <= 0) this.reloadNow();
      }, 1000);
    },
    reloadNow() {
      clearInterval(this.ticker);
      window.location.reload();
    }
  }
};
</script>

<style scoped>
.update-banner {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 0 0 10px 10px;
  background: #0d6efd;
  color: #fff;
  font-size: 0.9rem;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
</style>
