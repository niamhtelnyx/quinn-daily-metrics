#!/bin/bash

echo "🚀 Starting Call Intelligence API"
echo "================================"

# Kill any existing webhook processes
pkill -f webhook_receiver.py
pkill -f ngrok

# Set environment variables
# export FELLOW_API_KEY='your_fellow_api_key_here'  # Configure in .env file
# export OPENAI_API_KEY='your_openai_api_key_here'  # Configure in .env file

echo "✅ Environment configured"
echo "🎯 API will run on http://localhost:8000"
echo "📡 Process endpoint: POST /process-call"
echo "💊 Health check: GET /health"
echo ""

# Start the FastAPI server
python3 call_intelligence_api.py