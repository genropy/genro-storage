#!/bin/bash
# Script to stop all test services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping test services for genro-storage..."

cd "$PROJECT_DIR"

# Stop all services
docker compose -f tests/docker-compose.yml down

echo "All test services stopped."
