#!/bin/bash
# V2 FINAL Call Intelligence - Live with Slack posting to #revenue

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🚀 Starting V2 FINAL Call Intelligence with LIVE Slack posting..."
echo "💬 Posting to: #revenue channel"
echo "📅 Will run every 30 minutes"
echo "🛑 Stop with: pkill -f run_v2_live_revenue.sh"
echo ""

while true; do
    echo "[$(date)] 🔄 Running V2 FINAL with LIVE Slack posting..."
    
    # Source environment and run V2 LIVE
    source .env
    source /Users/niamhcollins/clawd/.env.gog
    python3 V2_LIVE_REVENUE.py >> logs/v2_live_revenue.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ V2 FINAL LIVE completed successfully"
    else
        echo "[$(date)] ❌ V2 FINAL LIVE failed with exit code $?"
    fi
    
    echo "[$(date)] ⏰ Waiting 30 minutes until next run..."
    sleep 1800  # 30 minutes = 1800 seconds
done