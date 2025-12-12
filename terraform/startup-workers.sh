#!/bin/bash
# Startup script for Workers Pool VM

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
gcloud auth configure-docker southamerica-east1-docker.pkg.dev

# Create docker-compose directory
mkdir -p /opt/vizu/workers-pool
cd /opt/vizu/workers-pool

# Create docker-compose.yml for workers pool services
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  data_ingestion_worker:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data_ingestion_worker:latest
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
    networks:
      - vizu-network
    restart: unless-stopped

  file_processing_worker:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/file_processing_worker:latest
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
    networks:
      - vizu-network
    restart: unless-stopped

  data_ingestion_api:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/data_ingestion_api:latest
    ports:
      - "8008:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  file_upload_api:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/file_upload_api:latest
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  analytics_api:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/analytics_api:latest
    ports:
      - "8004:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://vizu-redis:6379
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

# Create vizu-network if it doesn't exist
docker network create vizu-network || true

# Start services
docker-compose up -d

echo "Workers Pool started successfully"
