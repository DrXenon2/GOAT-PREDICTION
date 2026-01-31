#!/bin/bash
# Nginx Setup Script

echo "Setting up Nginx configuration..."

# Copy nginx config
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo cp sites-available/goat-prediction.conf /etc/nginx/sites-available/

# Create symlink
sudo ln -sf /etc/nginx/sites-available/goat-prediction.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

echo "Nginx setup completed!"
