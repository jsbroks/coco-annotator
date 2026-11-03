import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import { createRequire } from "node:module";

// Serve / emit paper.js as a classic (non-module) script, see src/libs/paper-shim.js
const require = createRequire(import.meta.url);
const PAPER_URL = "vendor/paper-core.min.js";
function paperClassicScript() {
  const file = require.resolve("paper/dist/paper-core.min.js");
  return {
    name: "paper-classic-script",
    configureServer(server) {
      server.middlewares.use("/" + PAPER_URL, (req, res) => {
        res.setHeader("Content-Type", "application/javascript");
        res.end(readFileSync(file));
      });
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: PAPER_URL, source: readFileSync(file) });
    }
  };
}

// Write a .gz copy next to each text file of the build: the server sends it to
// browsers that accept gzip (about a third of the size).
const GZIP = /\.(js|css|svg|json|html|ttf|eot|txt|map)$/;
function precompress() {
  let outDir = "dist";
  return {
    name: "precompress",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    closeBundle() {
      const walk = dir => {
        for (const name of readdirSync(dir)) {
          const file = join(dir, name);
          if (statSync(file).isDirectory()) walk(file);
          else if (GZIP.test(name) && name !== "index.html") {
            const raw = readFileSync(file);
            if (raw.length < 1024) continue;
            const gz = gzipSync(raw, { level: 9 });
            if (gz.length < raw.length * 0.9) writeFileSync(file + ".gz", gz);
          }
        }
      };
      walk(outDir);
    }
  };
}

// Each build gets an id: written to version.json (read by open pages to notice
// an update) and compiled into the page itself (__BUILD_ID__).
const BUILD_ID = Date.now().toString(36);
function versionFile() {
  return {
    name: "version-file",
    apply: "build",
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "version.json", source: JSON.stringify({ build: BUILD_ID }) });
    }
  };
}

// In development the Flask backend runs at BACKEND_URL (docker-compose.dev.yml
// sets it to the "webserver" service); API and websocket calls are proxied.
const backend = process.env.BACKEND_URL || "http://localhost:5000";

export default defineConfig({
  plugins: [vue(), paperClassicScript(), precompress(), versionFile()],
  define: {
    __BUILD_ID__: JSON.stringify(BUILD_ID)
  },
  resolve: {
    alias: [
      // CommonJS packages (vue-loading-overlay) require("vue"): give them the
      // runtime build too, not the full build with the template compiler
      { find: /^vue$/, replacement: "vue/dist/vue.runtime.esm-bundler.js" },
      { find: "@", replacement: fileURLToPath(new URL("./src", import.meta.url)) },
      { find: /^paper$/, replacement: fileURLToPath(new URL("./src/libs/paper-shim.js", import.meta.url)) }
    ]
  },
  server: {
    host: true,
    port: 8080,
    allowedHosts: true,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/socket.io": { target: backend, changeOrigin: true, ws: true }
    }
  },
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 2000
  },
  test: {
    environment: "jsdom"
  }
});
