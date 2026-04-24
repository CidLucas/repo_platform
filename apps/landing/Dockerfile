# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time Vite env for Supabase auth (PKCE flow).
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_DASHBOARD_URL
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_DASHBOARD_URL=$VITE_DASHBOARD_URL

# Copy package manifests and install dependencies
COPY apps/landing/package.json apps/landing/package-lock.json ./
RUN npm install

# Copy source code and build
COPY apps/landing/ ./
# Remove any stray .env so build args take precedence
RUN rm -f .env .env.local .env.development .env.production
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine

RUN apk add --no-cache gettext

RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config template
COPY apps/landing/nginx.conf /etc/nginx/conf.d/nginx.conf

EXPOSE 8080

CMD ["/bin/sh", "-c", "export PORT=${PORT:-8080} && envsubst '$PORT' < /etc/nginx/conf.d/nginx.conf > /tmp/nginx.conf && mv /tmp/nginx.conf /etc/nginx/conf.d/nginx.conf && nginx -g 'daemon off;'"]
