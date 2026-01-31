#!/bin/bash
# Airflow Manager Script

echo "Managing Airflow..."

# Start Airflow
docker-compose -f docker-compose.airflow.yml up -d

echo "Airflow management completed!"
