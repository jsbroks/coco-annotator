/**
 * Reload a panel every ``ms`` while it is on screen: paused while the
 * browser tab is hidden, and refreshed as soon as it is shown again.
 *
 *   mixins: [autoRefresh("load", 15000)]
 *
 * ``refreshedAt`` (a Date) is set after each successful reload.
 */
export default function autoRefresh(method, ms) {
  return {
    data() {
      return { refreshedAt: null };
    },
    mounted() {
      this.autoRefreshTimer = setInterval(() => {
        if (!document.hidden) this.autoRefreshRun();
      }, ms);
      this.autoRefreshVisible = () => {
        const last = this.refreshedAt ? this.refreshedAt.getTime() : 0;
        if (!document.hidden && Date.now() - last > ms / 2) this.autoRefreshRun();
      };
      document.addEventListener("visibilitychange", this.autoRefreshVisible);
    },
    beforeUnmount() {
      clearInterval(this.autoRefreshTimer);
      document.removeEventListener("visibilitychange", this.autoRefreshVisible);
    },
    methods: {
      async autoRefreshRun() {
        if (this.autoRefreshBusy) return;
        this.autoRefreshBusy = true;
        try {
          await this[method]({ background: true });
          this.refreshedAt = new Date();
        } catch {
          // try again next time
        } finally {
          this.autoRefreshBusy = false;
        }
      }
    }
  };
}
