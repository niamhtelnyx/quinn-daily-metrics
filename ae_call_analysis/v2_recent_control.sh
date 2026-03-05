#!/bin/bash
# V2 RECENT CALLS Control Script - Only processes calls from last 2 hours

cd /Users/niamhcollins/clawd/ae_call_analysis

case "$1" in
    "start")
        echo "🚀 Starting V2 RECENT CALLS ONLY..."
        chmod +x run_v2_recent_only.sh
        nohup ./run_v2_recent_only.sh > logs/v2_recent_daemon.log 2>&1 & 
        echo $! > v2_recent.pid
        echo "✅ Started with PID: $(cat v2_recent.pid)"
        echo "⏰ Only processes calls modified in last 2 hours"
        echo "📁 Folder: https://drive.google.com/drive/folders/1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
        ;;
    "stop")
        if [ -f v2_recent.pid ]; then
            PID=$(cat v2_recent.pid)
            echo "🛑 Stopping V2 RECENT CALLS (PID: $PID)..."
            kill $PID 2>/dev/null
            rm -f v2_recent.pid
            echo "✅ Stopped"
        else
            echo "⚠️ No PID file found"
            pkill -f run_v2_recent_only.sh
        fi
        ;;
    "status")
        if [ -f v2_recent.pid ]; then
            PID=$(cat v2_recent.pid)
            if ps -p $PID > /dev/null; then
                echo "🟢 V2 RECENT CALLS is running (PID: $PID)"
                echo "⏰ Processing: Calls modified in last 2 hours only"
                echo "📁 Folder: 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
                echo "💬 Posting to: #sales-calls"
                echo "🔗 Features: Recent calls + AI Analysis + Salesforce verification + QC filtering"
                echo "📊 Logs: tail -f logs/v2_recent_calls.log"
            else
                echo "🔴 V2 RECENT CALLS not running (stale PID file)"
                rm -f v2_recent.pid
            fi
        else
            echo "🔴 V2 RECENT CALLS not running"
        fi
        ;;
    "logs")
        echo "📊 V2 Recent Processing Logs:"
        tail -20 logs/v2_recent_calls.log 2>/dev/null || echo "No processing logs yet"
        echo ""
        echo "🔧 Daemon Logs:"
        tail -10 logs/v2_recent_daemon.log 2>/dev/null || echo "No daemon logs yet"
        echo ""
        echo "🛡️ QC Decisions:"
        tail -10 logs/qc_decisions.log 2>/dev/null || echo "No QC decisions yet"
        ;;
    "test")
        echo "🧪 Testing V2 RECENT CALLS (single run)..."
        source .env
        source /Users/niamhcollins/clawd/.env.gog
        python3 V2_RECENT_CALLS_ONLY.py
        ;;
    *)
        echo "V2 RECENT CALLS ONLY Control"
        echo "Usage: $0 {start|stop|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start  - Start V2 recent calls processing"
        echo "  stop   - Stop V2 recent calls processing" 
        echo "  status - Check if V2 is running"
        echo "  logs   - Show recent logs"
        echo "  test   - Run single test execution"
        echo ""
        echo "⏰ RECENT CALLS ONLY Features:"
        echo "   ✅ Only processes calls modified in last 2 hours"
        echo "   ✅ Avoids reprocessing old calls every 30 minutes"
        echo "   ✅ AI analysis + Salesforce verification"
        echo "   ✅ Posts to #sales-calls every 30 minutes"
        echo "   ✅ Quality control filters out garbage"
        ;;
esac