#!/bin/bash
# Log Rotation Script

LOG_DIR="../"
ROTATED_DIR="."
DATE=$(date +%Y-%m-%d)

echo "Rotating logs..."

# Compress and rotate application logs
tar -czf "$ROTATED_DIR/daily/logs-$DATE.tar.gz" -C "$LOG_DIR/application" .

echo "Log rotation completed!"
