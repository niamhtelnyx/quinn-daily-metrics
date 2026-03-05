#!/bin/bash
# V2 FINAL Call Intelligence - FOLDER-SPECIFIC (Only specified Drive folder)

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🚀 Starting V2 FINAL Call Intelligence - FOLDER-SPECIFIC..."
echo "📁 Searching ONLY in: https://drive.google.com/drive/folders/1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
echo "💬 Posting to: #sales-calls channel"
echo "📅 Will run every 30 minutes"
echo "🛑 Stop with: pkill -f run_v2_folder_specific.sh"
echo ""

while true; do
    echo "[$(date)] 🔍 Running V2 FINAL - FOLDER-SPECIFIC search..."
    
    # Source environment and run V2 FOLDER-SPECIFIC
    source .env
    source /Users/niamhcollins/clawd/.env.gog
    python3 V2_FOLDER_SPECIFIC_FIXED.py >> logs/v2_folder_specific.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ V2 FOLDER-SPECIFIC completed successfully"
    else
        echo "[$(date)] ❌ V2 FOLDER-SPECIFIC failed with exit code $?"
    fi
    
    echo "[$(date)] ⏰ Waiting 30 minutes until next run..."
    sleep 1800  # 30 minutes = 1800 seconds
done