#!/bin/bash
# Startup script for Dashboard VM

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
mkdir -p /opt/vizu/dashboard
cd /opt/vizu/dashboard

# Create docker-compose.yml for dashboard
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  vizu_dashboard:
    image: southamerica-east1-docker.pkg.dev/vizudev/vizu-mono/vizu-dashboard:latest
    ports:
      - "80:3000"
      - "443:3000"
    environment:
      REACT_APP_API_BASE_URL: http://vizu-agents-pool:8003
    networks:
      - vizu-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  vizu-network:
    external: true
EOF

# Create vizu-network if it doesn't exist
docker network create vizu-network || true

# Start services
docker-compose up -d

echo "Dashboard started successfully"
