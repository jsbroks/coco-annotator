# Annotator Web Client

Vue 3 + Vite.

```bash
npm ci
npm run dev      # http://localhost:8080, proxies /api and /socket.io to BACKEND_URL (default http://localhost:5000)
npm run build    # production build into dist/ (served by the Flask webserver)
npm test         # unit tests (Vitest)
npm run lint
```

With Docker: `docker compose -f docker-compose.dev.yml up --build` from the
repository root starts the dev server, the API and its services.

Note: paper.js is loaded as a classic `<script>` (see `vite.config.js` and
`src/libs/paper-shim.js`) because it does not work in strict-mode ES modules.
