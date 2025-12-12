#!/bin/bash
# Startup script for Redis VM

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

# Create docker-compose directory
mkdir -p /opt/vizu/redis
cd /opt/vizu/redis

# Create redis data directory with proper permissions
mkdir -p /data/redis
chmod 755 /data/redis

# Create docker-compose.yml for Redis
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --bind 0.0.0.0
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis_data:
    driver: local
EOF

# Create vizu-network if it doesn't exist
docker network create vizu-network || true

# Start Redis
docker-compose up -d

# Wait for Redis to be ready
sleep 5
docker-compose exec -T redis redis-cli ping || echo "Redis not yet ready"

echo "Redis started successfully"
echo "Redis is available at redis://vizu-redis:6379"
