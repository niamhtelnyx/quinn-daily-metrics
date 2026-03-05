#!/bin/bash
# V2 FINAL Call Intelligence with Salesforce Links Control Script

cd /Users/niamhcollins/clawd/ae_call_analysis

case "$1" in
    "start")
        echo "🚀 Starting V2 FINAL Call Intelligence with Salesforce Links..."
        nohup ./run_v2_sales_calls_sf.sh > logs/v2_sf_daemon.log 2>&1 & 
        echo $! > v2_sf.pid
        echo "✅ Started with PID: $(cat v2_sf.pid)"
        ;;
    "stop")
        if [ -f v2_sf.pid ]; then
            PID=$(cat v2_sf.pid)
            echo "🛑 Stopping V2 FINAL (PID: $PID)..."
            kill $PID 2>/dev/null
            rm -f v2_sf.pid
            echo "✅ Stopped"
        else
            echo "⚠️ No PID file found"
            pkill -f run_v2_sales_calls_sf.sh
        fi
        ;;
    "status")
        if [ -f v2_sf.pid ]; then
            PID=$(cat v2_sf.pid)
            if ps -p $PID > /dev/null; then
                echo "🟢 V2 FINAL with Salesforce Links is running (PID: $PID)"
                echo "💬 Posting to: #sales-calls"
                echo "🔗 Features: AI Analysis + Salesforce Links + Smart Deduplication"
                echo "📊 Logs: tail -f logs/v2_sf.log"
            else
                echo "🔴 V2 FINAL not running (stale PID file)"
                rm -f v2_sf.pid
            fi
        else
            echo "🔴 V2 FINAL not running"
        fi
        ;;
    "logs")
        echo "📊 V2 Processing Logs:"
        tail -20 logs/v2_sf.log 2>/dev/null || echo "No processing logs yet"
        echo ""
        echo "🔧 Daemon Logs:"
        tail -10 logs/v2_sf_daemon.log 2>/dev/null || echo "No daemon logs yet"
        ;;
    *)
        echo "V2 FINAL Call Intelligence with Salesforce Links Control"
        echo "Usage: $0 {start|stop|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start  - Start V2 live processing with Salesforce links"
        echo "  stop   - Stop V2 live processing" 
        echo "  status - Check if V2 is running"
        echo "  logs   - Show recent logs"
        echo ""
        echo "🔗 Enhanced Features:"
        echo "   ✅ Clickable Salesforce links in Slack messages"
        echo "   ✅ AI-powered call analysis"
        echo "   ✅ Smart deduplication"
        echo "   ✅ Posts to #sales-calls every 30 minutes"
        ;;
esac