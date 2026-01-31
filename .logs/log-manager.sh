#!/bin/bash
# Log Manager Script

echo "Managing logs..."

# Run log rotation
./rotated/log-rotate.sh

# Run access log rotation
./access/access-log-rotator.sh

# Run log monitoring
python3 ./application/log-monitor.py

echo "Log management completed!"
