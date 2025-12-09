#!/usr/bin/env bash
set -euo pipefail

# Build Dockerfile for a service and verify image size is under threshold.
# Usage: ./scripts/docker_build_and_check.sh <service_dir> [max_size_bytes]

SERVICE_DIR=${1:-}
if [ -z "$SERVICE_DIR" ]; then
  echo "Usage: $0 <path-to-service-dir> [max_size_bytes]"
  exit 2
fi

MAX_SIZE=${2:-200000000} # 200MB default

IMAGE_TAG="ci-check-$(basename "$SERVICE_DIR")-$(date +%s)"

echo "Building image for $SERVICE_DIR as $IMAGE_TAG"
docker build -f "$SERVICE_DIR/Dockerfile" -t "$IMAGE_TAG" "$SERVICE_DIR"

size=$(docker image inspect --format='{{.Size}}' "$IMAGE_TAG")
echo "Image size: $size bytes (max allowed: $MAX_SIZE)"

if [ "$size" -gt "$MAX_SIZE" ]; then
  echo "ERROR: image size exceeded threshold"
  exit 3
fi

echo "Image size OK"
