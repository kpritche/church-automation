#!/bin/bash
# Force rebuild Docker container without any cache

echo "Stopping and removing existing containers..."
sudo docker compose down

echo "Removing old images..."
sudo docker compose rm -f
sudo docker rmi $(sudo docker images -q church-automation*) 2>/dev/null || true

echo "Building fresh image without cache..."
sudo docker compose build --no-cache --pull

echo "Starting containers..."
sudo docker compose up -d

echo "Checking container status..."
sudo docker compose ps

echo ""
echo "✓ Container rebuilt from scratch!"
echo "✓ Web UI should be available at http://localhost:8080"
echo ""
echo "To view logs:"
echo "  sudo docker compose logs -f church-automation"
