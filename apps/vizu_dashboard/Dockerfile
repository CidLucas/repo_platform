# Estágio 1: Builder - Instala dependências e gera os arquivos estáticos
FROM node:20-alpine as builder

# Define o diretório de trabalho
WORKDIR /app

# Build arguments for Vite environment variables
# These will be embedded in the bundle at build time
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_API_URL
ARG VITE_ATENDENTE_CORE
ARG VITE_API_URL_ANALYTICS
ARG VITE_DATA_INGESTION_API_URL

# Export as environment variables for Vite build
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ATENDENTE_CORE=$VITE_ATENDENTE_CORE
ENV VITE_API_URL_ANALYTICS=$VITE_API_URL_ANALYTICS
ENV VITE_DATA_INGESTION_API_URL=$VITE_DATA_INGESTION_API_URL

# 1. COPIA os arquivos de manifesto de dependências
# Note: When building from monorepo root, paths are relative to root
COPY apps/vizu_dashboard/package.json apps/vizu_dashboard/package-lock.json ./

# 2. INSTALA as dependências do projeto
RUN npm install

# 3. COPIA todo o código-fonte da aplicação
COPY apps/vizu_dashboard/ ./

# 4. Remove .env file so build args take precedence
# Vite prioritizes .env files over environment variables
RUN rm -f .env .env.local .env.development .env.production

# 5. EXECUTA o build de produção
# Isso irá gerar a pasta /dist com os arquivos otimizados
# Vite will embed the VITE_* environment variables from ENV
RUN npm run build

# -----------------------------------------------------

# Estágio 2: Final - Apenas o Runtime com Nginx
FROM nginx:stable-alpine

# Instala gettext para ter o comando envsubst (substituição de variáveis de ambiente)
RUN apk add --no-cache gettext

RUN rm -rf /usr/share/nginx/html/*
# 1. COPIA os arquivos estáticos gerados no estágio de build
# O Nginx por padrão serve arquivos de /usr/share/nginx/html
COPY --from=builder /app/dist /usr/share/nginx/html

# 2. REMOVE a configuração padrão do Nginx
RUN rm /etc/nginx/conf.d/default.conf

# 3. COPIA o arquivo de configuração customizado para o Nginx (template com ${PORT})
# Este arquivo será criado a seguir e é essencial para o roteamento do React
COPY apps/vizu_dashboard/nginx.conf /etc/nginx/conf.d/nginx.conf

# 4. EXPÕE a porta dinâmica (Cloud Run usa $PORT)
EXPOSE 8080

# 5. Script de inicialização que substitui ${PORT} no nginx.conf e inicia o servidor
# Usa envsubst para substituir variáveis de ambiente no template
# Default PORT=8080 for Cloud Run, can be overridden locally
CMD ["/bin/sh", "-c", "export PORT=${PORT:-8080} && envsubst '${PORT}' < /etc/nginx/conf.d/nginx.conf > /tmp/nginx.conf && mv /tmp/nginx.conf /etc/nginx/conf.d/nginx.conf && nginx -g 'daemon off;'"]
