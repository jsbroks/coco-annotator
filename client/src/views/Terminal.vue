<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="terminal-page">
      <!-- log in -->
      <div v-if="state !== 'open'" class="login-wrap">
        <div class="card shadow-sm login-card">
          <h4 class="mb-1"><i class="fa fa-terminal" /> {{ $t('terminal.title') }}</h4>
          <div class="text-muted small mb-3">
            {{ info ? $t('terminal.target', { host: info.host, port: info.port }) : '' }}
          </div>
          <div class="alert alert-warning small py-2">
            <i class="fa fa-exclamation-triangle" /> {{ $t('terminal.warning') }}
          </div>
          <form @submit.prevent="connect">
            <label class="form-label small mb-0" for="termUser">{{ $t('terminal.username') }}</label>
            <input
              id="termUser"
              ref="user"
              v-model="username"
              class="form-control mb-2"
              autocomplete="username"
              autocapitalize="off"
              spellcheck="false"
            />
            <label class="form-label small mb-0" for="termPass">{{ $t('terminal.password') }}</label>
            <input id="termPass" v-model="password" type="password" class="form-control mb-3" autocomplete="current-password" />
            <div v-if="message" class="small mb-2" :class="state === 'closed' ? 'text-muted' : 'text-danger'">{{ message }}</div>
            <button type="submit" class="btn btn-dark w-100" :disabled="!username || state === 'connecting'">
              <i class="fa" :class="state === 'connecting' ? 'fa-spinner fa-spin' : 'fa-sign-in'" />
              {{ state === 'connecting' ? $t('terminal.connecting') : $t('terminal.connect') }}
            </button>
          </form>
          <div class="small text-muted mt-3">
            {{ $t('terminal.notStored') }}
            <template v-if="info && info.idle_minutes"> {{ $t('terminal.idle', { n: info.idle_minutes }) }}</template>
          </div>
        </div>
      </div>

      <!-- the session -->
      <div v-show="state === 'open'" class="session">
        <div class="session-bar">
          <span><i class="fa fa-circle text-success me-1" />{{ who }}</span>
          <span class="ms-auto small text-secondary d-none d-md-inline">{{ $t('terminal.copyHint') }}</span>
          <button type="button" class="btn btn-sm btn-outline-light py-0" @click="disconnect">
            <i class="fa fa-sign-out" /> {{ $t('terminal.disconnect') }}
          </button>
        </div>
        <div ref="term" class="term" />
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

/**
 * SSH login to the server in the page (permission "terminal"): the account
 * and password are sent once to open the session and never stored.
 */
export default {
  name: "TerminalPage",
  data() {
    return {
      info: null,
      username: "",
      password: "",
      // idle | connecting | open | closed
      state: "idle",
      message: "",
      who: ""
    };
  },
  methods: {
    connect() {
      if (!this.username || this.state === "connecting") return;
      this.state = "connecting";
      this.message = "";
      const size = this.ensureTerminal();
      this.$socket.emit(
        "term_open",
        { username: this.username, password: this.password, cols: size.cols, rows: size.rows },
        ack => {
          if (!ack || !ack.ok) {
            this.state = "idle";
            this.message = this.$t("terminal.error." + ((ack && ack.code) || "connect"));
          }
        }
      );
      // the password is only needed to log in
      this.password = "";
    },
    /** create the terminal once; returns its size in characters */
    ensureTerminal() {
      if (!this.term) {
        this.term = new Terminal({
          cursorBlink: true,
          fontSize: 14,
          fontFamily: 'Menlo, Consolas, "DejaVu Sans Mono", "Noto Sans Mono CJK TC", monospace',
          scrollback: 5000,
          theme: { background: "#1e1e1e" }
        });
        this.fit = new FitAddon();
        this.term.loadAddon(this.fit);
        this.term.open(this.$refs.term);
        // keys typed in a burst go out together, numbered (kept in order)
        this.term.onData(data => {
          if (this.state !== "open") return;
          this.outBuffer = (this.outBuffer || "") + data;
          if (this.outTimer) return;
          this.outTimer = setTimeout(() => {
            this.outTimer = null;
            const text = this.outBuffer;
            this.outBuffer = "";
            if (text) this.$socket.emit("term_in", { data: text, seq: this.seq++ });
          }, 8);
        });
        this.term.onResize(({ cols, rows }) => {
          if (this.state === "open") this.$socket.emit("term_resize", { cols, rows });
        });
        this.onWindowResize = () => this.refit();
        window.addEventListener("resize", this.onWindowResize);
      }
      this.refit();
      return { cols: this.term.cols, rows: this.term.rows };
    },
    refit() {
      try {
        if (this.fit) this.fit.fit();
      } catch {
        // not visible yet
      }
    },
    disconnect() {
      this.$socket.emit("term_close");
      this.state = "closed";
      this.message = this.$t("terminal.closed.closed");
    }
  },
  sockets: {
    term_ready(data) {
      this.state = "open";
      this.seq = 0;
      this.who = `${data.user}@${data.host}`;
      this.term.reset();
      this.$nextTick(() => {
        this.refit();
        this.term.focus();
        this.$socket.emit("term_resize", { cols: this.term.cols, rows: this.term.rows });
      });
    },
    term_out(data) {
      if (this.term) this.term.write(data.data);
    },
    term_error(data) {
      this.state = "idle";
      this.message = this.$t("terminal.error." + (data.code || "connect")) + (data.message ? `（${data.message}）` : "");
      this.$nextTick(() => this.$refs.user && this.$refs.user.focus());
    },
    term_closed(data) {
      if (this.state === "idle") return;
      this.state = "closed";
      const reason = (data && data.reason) || "exit";
      this.message = this.$t("terminal.closed." + (["idle", "exit", "closed"].includes(reason) ? reason : "exit"));
    },
    disconnect() {
      if (this.state === "open" || this.state === "connecting") {
        this.state = "closed";
        this.message = this.$t("terminal.closed.lost");
      }
    }
  },
  mounted() {
    axios
      .get("/api/terminal/")
      .then(r => (this.info = r.data))
      .catch(() => (this.info = null));
    this.$nextTick(() => this.$refs.user && this.$refs.user.focus());
  },
  beforeUnmount() {
    if (this.state === "open" || this.state === "connecting") this.$socket.emit("term_close");
    window.removeEventListener("resize", this.onWindowResize);
    if (this.term) this.term.dispose();
  }
};
</script>

<style scoped>
.terminal-page {
  height: calc(var(--vh) - 55px);
  background: #f1f3f5;
  text-align: left;
}
.login-wrap {
  display: flex;
  justify-content: center;
  padding: 48px 16px;
}
.login-card {
  width: 420px;
  max-width: 100%;
  padding: 24px;
}
.session {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
}
.session-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: #2d2d2d;
  color: #e9ecef;
  font-size: 0.85rem;
}
.term {
  flex: 1;
  min-height: 0;
  padding: 6px 8px;
}
</style>
