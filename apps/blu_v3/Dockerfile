# apps/blu_v3/Dockerfile
# Docker multi-stage para o frontend Blu (blu_v3)
#
# Build:  docker build -t blu-frontend -f apps/blu_v3/Dockerfile .
# Run:    docker run -p 80:80 blu-frontend
#
# Cloud Run:  gcloud builds submit --tag gcr.io/$PROJECT/blu-frontend
#             gcloud run deploy blu-frontend --image gcr.io/$PROJECT/blu-frontend --port 80

# ─── Stage 1: Build ───────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Cache de dependências (só reinstala se package*.json mudar)
COPY apps/blu_v3/package*.json ./
RUN npm ci

# Cópia do código fonte e dependências do monorepo
COPY apps/blu_v3/ .
COPY packages/ /app/../packages/
COPY tsconfig*.json /app/../

# Build
RUN npm run build

# ─── Stage 2: Serve ───────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Nginx config com CSP de produção
COPY apps/blu_v3/nginx.conf /etc/nginx/conf.d/default.conf

# Assets do build (HTML, JS, CSS, imagens)
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/healthz || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
