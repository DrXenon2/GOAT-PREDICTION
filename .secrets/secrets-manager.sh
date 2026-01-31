#!/bin/bash
# Secrets Manager Script

echo "Managing secrets..."

# Ensure proper permissions
chmod 600 .secrets/**/*.key
chmod 600 .secrets/**/*.crt
chmod 600 .secrets/**/*.env

echo "Secrets management completed!"
