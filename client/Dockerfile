# Development image: Vite dev server with hot reload (see docker-compose.dev.yml)
FROM node:22-alpine
WORKDIR /workspace/client
COPY client/package.json client/package-lock.json ./
RUN npm ci --no-audit --no-fund
EXPOSE 8080
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8080"]
