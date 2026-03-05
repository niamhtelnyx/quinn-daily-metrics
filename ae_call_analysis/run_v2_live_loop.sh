#!/bin/bash
# V2 FINAL Call Intelligence - Self-Running Loop (Alternative to cron)
# Runs V2_FINAL_PRODUCTION_LIVE.py every 30 minutes in the background

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🚀 Starting V2 FINAL Call Intelligence loop..."
echo "📅 Will run every 30 minutes"
echo "📊 Logs: logs/v2_final.log"
echo "🛑 Stop with: pkill -f run_v2_loop.sh"
echo ""

while true; do
    echo "[$(date)] 🔄 Running V2 FINAL Call Intelligence..."
    
    # Source environment and run V2
    source .env
    source /Users/niamhcollins/clawd/.env.gog
    python3 V2_FINAL_PRODUCTION_LIVE.py >> logs/v2_final.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ V2 FINAL completed successfully"
    else
        echo "[$(date)] ❌ V2 FINAL failed with exit code $?"
    fi
    
    echo "[$(date)] ⏰ Waiting 30 minutes until next run..."
    sleep 1800  # 30 minutes = 1800 seconds
done