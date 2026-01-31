#!/bin/bash
# TimescaleDB Manager Script

echo "Managing TimescaleDB..."

# Start TimescaleDB
docker-compose up -d

echo "TimescaleDB management completed!"
