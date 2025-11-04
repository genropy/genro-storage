#!/bin/bash
# Script to start all required test services using docker-compose
# This script is used both locally and in CI/CD

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting test services for genro-storage..."

cd "$PROJECT_DIR"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker ps &> /dev/null; then
    echo "Error: Docker daemon is not running"
    echo "Please start Docker Desktop (on macOS) or Docker service (on Linux)"
    exit 1
fi

# Start all test services
echo "Starting services: fake-gcs, webdav, azurite, samba, sftp, minio..."
docker-compose up -d fake-gcs webdav azurite samba sftp minio

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check services status
echo "Services status:"
docker-compose ps

# Wait for health checks
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    UNHEALTHY=$(docker-compose ps --format json | grep -c '"Health":"starting"' || true)
    if [ "$UNHEALTHY" -eq "0" ]; then
        echo "All services are ready!"
        exit 0
    fi
    echo "Waiting for services to become healthy... ($WAITED/$MAX_WAIT seconds)"
    sleep 2
    WAITED=$((WAITED + 2))
done

echo "Warning: Some services may not be fully healthy yet, but continuing..."
exit 0
