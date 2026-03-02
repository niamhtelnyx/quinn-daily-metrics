#!/bin/bash

echo "🚀 Starting Fellow Call Intelligence Webhook Server"
echo "=================================================="

# Install Flask if not installed
pip3 install flask

# Start the webhook receiver
cd ae_call_analysis
python3 webhook_receiver.py

echo ""
echo "✅ Webhook server started!"
echo "📡 Zapier webhook URL: http://localhost:5000/webhook/fellow-call"
echo "💊 Health check: http://localhost:5000/health"  
echo "🧪 Test endpoint: http://localhost:5000/test"
echo ""
echo "Configure Zapier to POST to: http://[your-server-ip]:5000/webhook/fellow-call"