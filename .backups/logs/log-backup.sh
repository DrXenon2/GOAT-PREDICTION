#!/bin/bash
# Log Backup Script

LOG_DIR="../.logs"
BACKUP_DIR="."
DATE=$(date +%Y-%m-%d)

echo "Backing up logs..."
tar -czf "$BACKUP_DIR/daily/logs-$DATE.tar.gz" -C "$LOG_DIR" .

echo "Log backup completed!"
