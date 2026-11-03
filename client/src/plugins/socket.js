// Minimal replacement for vue-socket.io (Vue 2 only).
// Components keep declaring handlers in a `sockets: { event(data) {} }`
// option; `connect` / `disconnect` map to socket.io's lifecycle events.
import { io } from "socket.io-client";

export default {
  install(app, { connection = window.location.origin, options = {} } = {}) {
    // Start with HTTP long-polling and upgrade to WebSocket when possible:
    // behind a reverse proxy that does not pass WebSocket upgrades the
    // connection still works (WebSocket-first never fell back to polling).
    const socket = io(connection, { transports: ["polling", "websocket"], tryAllTransports: true, ...options });
    app.config.globalProperties.$socket = socket;

    app.mixin({
      created() {
        const handlers = this.$options.sockets;
        if (!handlers) return;
        this.__socketHandlers = Object.entries(handlers).map(([event, fn]) => {
          const bound = fn.bind(this);
          socket.on(event, bound);
          // the component may be created after the socket already connected
          if (event === "connect" && socket.connected) bound();
          return [event, bound];
        });
      },
      beforeUnmount() {
        (this.__socketHandlers || []).forEach(([event, fn]) => socket.off(event, fn));
      }
    });
  }
};
