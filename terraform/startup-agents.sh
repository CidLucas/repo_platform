#!/bin/bash
# Startup script for Agents Pool VM

set -e

# Update system
apt-get update
apt-get install -y \
  curl \
  wget \
  git \
  docker.io \
  docker-compose \
  jq \
  ca-certificates \
  gnupg \
  lsb-release

# Start Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate with service account
gcloud auth activate-service-account --key-file=/etc/google/key.json

# Configure Docker to pull from Artifact Registry
gcloud auth configure-docker us-east1-docker.pkg.dev

# Create docker-compose directory
mkdir -p /opt/vizu/agents-pool
cd /opt/vizu/agents-pool

# Create docker-compose.yml for agents pool services
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  atendente_core:
    image: us-east1-docker.pkg.dev/vizudev/vizu-mono/atendente_core:latest
    ports:
      - "8003:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
      LANGFUSE_HOST: ${LANGFUSE_HOST}
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  tool_pool_api:
    image: us-east1-docker.pkg.dev/vizudev/vizu-mono/tool_pool_api:latest
    ports:
      - "9000:9000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  vendas_agent:
    image: us-east1-docker.pkg.dev/vizudev/vizu-mono/vendas_agent:latest
    ports:
      - "8009:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
      LANGFUSE_HOST: ${LANGFUSE_HOST}
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  support_agent:
    image: us-east1-docker.pkg.dev/vizudev/vizu-mono/support_agent:latest
    ports:
      - "8010:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
      LANGFUSE_HOST: ${LANGFUSE_HOST}
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  vizu-network:
    external: true
EOF

# Get secrets from Google Secret Manager
export DATABASE_URL=$(gcloud secrets versions access latest --secret="DATABASE_URL")
export REDIS_URL="redis://vizu-redis:6379"
export OLLAMA_BASE_URL=$(gcloud secrets versions access latest --secret="OLLAMA_BASE_URL")
export LANGFUSE_HOST=$(gcloud secrets versions access latest --secret="LANGFUSE_HOST")
export GOOGLE_API_KEY=$(gcloud secrets versions access latest --secret="GOOGLE_API_KEY")

# Create vizu-network if it doesn't exist
docker network create vizu-network || true

# Start services
docker-compose up -d

echo "Agents Pool started successfully"
