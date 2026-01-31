#!/bin/bash
# Access Log Rotator Script

LOG_DIR="$(dirname "$0")"
DATE=$(date +%Y-%m-%d)

echo "Rotating access logs..."

# Rotate admin logs
if [ -f "$LOG_DIR/admin/admin-access.log" ]; then
    mv "$LOG_DIR/admin/admin-access.log" "$LOG_DIR/admin/admin-access-$DATE.log"
    touch "$LOG_DIR/admin/admin-access.log"
fi

# Rotate API gateway logs
if [ -f "$LOG_DIR/api-gateway/api-access.log" ]; then
    mv "$LOG_DIR/api-gateway/api-access.log" "$LOG_DIR/api-gateway/api-access-$DATE.log"
    touch "$LOG_DIR/api-gateway/api-access.log"
fi

# Rotate nginx logs
if [ -f "$LOG_DIR/nginx/nginx-access.log" ]; then
    mv "$LOG_DIR/nginx/nginx-access.log" "$LOG_DIR/nginx/nginx-access-$DATE.log"
    touch "$LOG_DIR/nginx/nginx-access.log"
fi

echo "Access log rotation completed!"
