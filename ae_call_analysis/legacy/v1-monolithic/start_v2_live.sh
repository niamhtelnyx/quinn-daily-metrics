#!/bin/bash
# Start V2 FINAL Call Intelligence Live Processing

cd /Users/niamhcollins/clawd/ae_call_analysis

echo "🚀 Starting V2 FINAL Call Intelligence Live Processing..."

# Make sure logs directory exists
mkdir -p logs

# Start the background loop
chmod +x run_v2_loop.sh
nohup ./run_v2_loop.sh > logs/v2_daemon.log 2>&1 &

# Get the process ID
PID=$!
echo $PID > v2_live.pid

echo "✅ V2 FINAL is now running live!"
echo "📋 Process ID: $PID"
echo "📊 Main logs: tail -f logs/v2_final.log"  
echo "🔧 Daemon logs: tail -f logs/v2_daemon.log"
echo "🛑 Stop with: ./stop_v2_live.sh"

# Show initial status
sleep 2
ps -p $PID > /dev/null
if [ $? -eq 0 ]; then
    echo "🟢 V2 FINAL is running (PID: $PID)"
    echo "⏰ Next run in 30 minutes, then every 30 minutes after that"
else
    echo "🔴 V2 FINAL failed to start"
fi