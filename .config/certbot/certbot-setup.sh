#!/bin/bash
# Certbot Setup Script

echo "Setting up Certbot for SSL certificates..."

# Install Certbot if not installed
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt-get update
    sudo apt-get install certbot python3-certbot-nginx -y
fi

# Request SSL certificate
echo "Requesting SSL certificate..."
sudo certbot --nginx -d goat-prediction.com -d www.goat-prediction.com

# Setup auto-renewal
echo "Setting up auto-renewal..."
sudo certbot renew --dry-run

echo "Certbot setup completed!"
