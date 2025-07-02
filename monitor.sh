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
