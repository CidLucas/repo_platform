# apps/blu_v3/Dockerfile
# Docker multi-stage para o frontend Blu (blu_v3)
#
# Build:  docker build -t blu-frontend -f apps/blu_v3/Dockerfile .
# Run:    docker run -p 80:80 blu-frontend
#
# Cloud Run:  gcloud builds submit --tag gcr.io/$PROJECT/blu-frontend
#             gcloud run deploy blu-frontend --image gcr.io/$PROJECT/blu-frontend --port 80

# ─── Stage 1: Build ───────────────────────────────────────────────────
# O repo é um npm workspace (workspaces: apps/*, packages/*): as deps são
# hoisted para o node_modules da RAIZ, e é assim que o tsc resolve
# vite/client e que packages/blu-auth enxerga react. O build no Docker
# replica essa estrutura — instalar o app isolado não funciona.
FROM node:20-alpine AS builder

WORKDIR /repo

# Cache de dependências (só reinstala se manifests/lock mudarem)
COPY package.json package-lock.json ./
COPY apps/blu_v3/package.json apps/blu_v3/
COPY packages/blu-auth/package.json packages/blu-auth/
RUN npm ci

# Código fonte do workspace
COPY packages/ packages/
COPY apps/blu_v3/ apps/blu_v3/

# ─── Variáveis VITE_ (build-time) ─────────────────────────────────────
# Vite embute essas variáveis no bundle JS durante o `npm run build` —
# não são configuráveis em runtime no Cloud Run. Os defaults abaixo são
# os valores de produção (todos públicos: viajam no bundle de qualquer
# forma). O .dockerignore da raiz exclui .env.* do contexto, então este
# é o único caminho de injeção. Override via --build-arg se necessário.
# Env vars de processo têm precedência sobre arquivos .env no Vite.
ARG VITE_SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
ARG VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhhcnVld2ZmbnViZGd5b2ZmdHV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNjU5ODAsImV4cCI6MjA3OTc0MTk4MH0.n3XAjdtBtCtB-d3mNDfF_l5C7HtFrcFPiHnvhYQJ-U8
ARG VITE_ATENDENTE_CORE=https://agent-api-960100281317.southamerica-east1.run.app
ARG VITE_STANDALONE_AGENT_API=https://agent-api-960100281317.southamerica-east1.run.app
ARG VITE_TOOL_POOL_API_URL=https://tool-pool-api-960100281317.southamerica-east1.run.app
ARG VITE_GOOGLE_PICKER_API_KEY=AIzaSyClAh9UH_qegz-JfibQXQ9_piPrxgBTGjo
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
    VITE_ATENDENTE_CORE=$VITE_ATENDENTE_CORE \
    VITE_STANDALONE_AGENT_API=$VITE_STANDALONE_AGENT_API \
    VITE_TOOL_POOL_API_URL=$VITE_TOOL_POOL_API_URL \
    VITE_GOOGLE_PICKER_API_KEY=$VITE_GOOGLE_PICKER_API_KEY

# Build
WORKDIR /repo/apps/blu_v3
RUN npm run build

# ─── Stage 2: Serve ───────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Nginx config com CSP de produção
COPY apps/blu_v3/nginx.conf /etc/nginx/conf.d/default.conf

# Assets do build (HTML, JS, CSS, imagens)
COPY --from=builder /repo/apps/blu_v3/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/healthz || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
