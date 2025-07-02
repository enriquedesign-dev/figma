#!/bin/bash

# Figma API Simple Production Deployment Script
# This script sets up the FastAPI server for production use

set -e

echo "🚀 Setting up Figma API for production deployment..."

# Create systemd service for auto-restart and management
sudo tee /etc/systemd/system/figma-api.service > /dev/null <<EOF
[Unit]
Description=Figma API FastAPI Server
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/root/figma
Environment=PATH=/root/figma/venv/bin
ExecStart=/root/figma/venv/bin/python /root/figma/main.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/root/figma

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable figma-api.service

echo "✅ Systemd service created and enabled"

# Install nginx for reverse proxy
echo "📦 Installing Nginx..."
sudo apt update
sudo apt install -y nginx

# Create simple nginx configuration
sudo tee /etc/nginx/sites-available/figma-api > /dev/null <<EOF
server {
    listen 80;
    server_name _; # Replace with your domain if you have one
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers (if needed for web access)
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization";
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/figma-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

if [ $? -eq 0 ]; then
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    echo "✅ Nginx configured successfully"
    echo "🌐 Your API will be available at: http://168.119.237.216/"
else
    echo "❌ Nginx configuration error"
    exit 1
fi

# Create monitoring script
tee /root/figma/monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# Simple monitoring script for Figma API

API_URL="http://localhost:8000/health"
LOG_FILE="/root/figma/monitor.log"

# Test API health
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL" 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    echo "$(date): ✅ API healthy (HTTP $response)" >> "$LOG_FILE"
else
    echo "$(date): ❌ API unhealthy (HTTP $response)" >> "$LOG_FILE"
    # Restart service if unhealthy
    sudo systemctl restart figma-api.service
    echo "$(date): 🔄 Restarted figma-api service" >> "$LOG_FILE"
fi
EOF

chmod +x /root/figma/monitor.sh

# Add monitoring to crontab (check every 5 minutes)
(crontab -l 2>/dev/null | grep -v "figma.*monitor"; echo "*/5 * * * * /root/figma/monitor.sh") | crontab -

echo "✅ Monitoring script installed (checks every 5 minutes)"

# Stop any existing manual processes
pkill -f "python main.py" || true

# Start the service
sudo systemctl start figma-api.service

echo ""
echo "🎉 Production deployment complete!"
echo ""
echo "📋 Service Management Commands:"
echo "  sudo systemctl status figma-api    # Check status"
echo "  sudo systemctl restart figma-api   # Restart"
echo "  sudo systemctl stop figma-api      # Stop"
echo "  sudo systemctl start figma-api     # Start"
echo ""
echo "📊 Monitoring:"
echo "  tail -f /root/figma/monitor.log    # View health logs"
echo "  journalctl -fu figma-api          # View service logs"
echo ""
echo "🌐 Your API endpoints are now available at:"
echo "  http://168.119.237.216/health"
echo "  http://168.119.237.216/api/figma/texts"
echo "  http://168.119.237.216/api/figma/pages"
echo ""
echo "🔧 For mobile app integration, use this base URL:"
echo "  Production: http://168.119.237.216/api/" 