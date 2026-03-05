#!/bin/bash
# Quick start script for V1 Enhanced Call Intelligence System

echo "🚀 Starting V1 Enhanced Call Intelligence System..."

# Source environment
source /Users/niamhcollins/clawd/.env.gog
source .env

# Run the system
echo "📊 Processing calls and posting to Slack..."
python3 V1_GOOGLE_DRIVE_ENHANCED.py

echo "✅ System run complete! Check #sales-calls for any new call analyses."
