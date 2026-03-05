#!/bin/bash
# V2 FINAL Call Intelligence Cron Installer

echo "🚀 Installing V2 FINAL Call Intelligence cron job..."

# Apply the updated crontab directly
crontab /Users/niamhcollins/clawd/ae_call_analysis/updated_cron.txt

if [ $? -eq 0 ]; then
    echo "✅ V2 FINAL cron job installed successfully!"
    echo "📅 V2_FINAL_PRODUCTION.py will run every 30 minutes"
    
    # Verify installation
    echo "📋 Verification:"
    crontab -l | grep "V2_FINAL_PRODUCTION"
    
    echo "📊 Monitor with: tail -f /Users/niamhcollins/clawd/ae_call_analysis/logs/v2_final.log"
else
    echo "❌ Cron installation failed"
    exit 1
fi