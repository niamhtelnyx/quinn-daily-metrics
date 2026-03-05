#!/bin/bash
# V2 RECENT CALLS ONLY - Every 30 minutes, only process calls from last 2 hours

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🚀 Starting V2 RECENT CALLS ONLY..."
echo "⏰ Only processes calls modified in last 2 hours"
echo "📁 Folder: https://drive.google.com/drive/folders/1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
echo "💬 Posting to: #sales-calls channel"
echo "📅 Will run every 30 minutes"
echo "🛑 Stop with: pkill -f run_v2_recent_only.sh"
echo ""

while true; do
    echo "[$(date)] 🔍 Running V2 RECENT CALLS ONLY..."
    
    # Source environment and run V2 RECENT CALLS
    source .env
    source /Users/niamhcollins/clawd/.env.gog
    python3 V2_RECENT_CALLS_ONLY.py >> logs/v2_recent_calls.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ V2 RECENT CALLS completed successfully"
    else
        echo "[$(date)] ❌ V2 RECENT CALLS failed with exit code $?"
    fi
    
    echo "[$(date)] ⏰ Waiting 30 minutes until next run..."
    sleep 1800  # 30 minutes = 1800 seconds
done