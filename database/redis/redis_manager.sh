#!/bin/bash
# Redis Manager Script

echo "Managing Redis..."

# Start Redis
docker-compose -f docker-compose.redis.yml up -d

echo "Redis management completed!"
