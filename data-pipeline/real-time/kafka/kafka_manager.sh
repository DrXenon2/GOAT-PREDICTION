#!/bin/bash
# Kafka Manager Script

echo "Managing Kafka..."

# Start Kafka cluster
docker-compose -f docker-compose.kafka.yml up -d

echo "Kafka management completed!"
