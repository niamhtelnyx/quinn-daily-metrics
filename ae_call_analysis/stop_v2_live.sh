#!/bin/bash
# Stop V2 FINAL Call Intelligence Live Processing

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🛑 Stopping V2 FINAL Call Intelligence..."

if [ -f v2_live.pid ]; then
    PID=$(cat v2_live.pid)
    echo "📋 Found PID: $PID"
    
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "✅ V2 FINAL stopped (PID: $PID)"
        rm v2_live.pid
    else
        echo "⚠️ Process not running, cleaning up PID file"
        rm v2_live.pid
    fi
else
    echo "📋 No PID file found, trying to stop by name..."
    pkill -f run_v2_loop.sh
    if [ $? -eq 0 ]; then
        echo "✅ V2 FINAL stopped"
    else
        echo "⚠️ No V2 FINAL processes found"
    fi
fi

echo "🔍 Current V2 processes:"
ps aux | grep -E "(V2_FINAL|run_v2_loop)" | grep -v grep