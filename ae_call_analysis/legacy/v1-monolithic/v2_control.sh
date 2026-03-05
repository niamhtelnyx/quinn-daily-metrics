#!/bin/bash
# V2 FINAL Call Intelligence Control Script

cd /Users/niamhcollins/clawd/ae_call_analysis

case "$1" in
    "start")
        echo "🚀 Starting V2 FINAL Call Intelligence..."
        nohup ./run_v2_sales_calls.sh > logs/v2_sales_calls_daemon.log 2>&1 & 
        echo $! > v2_sales_calls.pid
        echo "✅ Started with PID: $(cat v2_sales_calls.pid)"
        ;;
    "stop")
        if [ -f v2_sales_calls.pid ]; then
            PID=$(cat v2_sales_calls.pid)
            echo "🛑 Stopping V2 FINAL (PID: $PID)..."
            kill $PID 2>/dev/null
            rm -f v2_sales_calls.pid
            echo "✅ Stopped"
        else
            echo "⚠️ No PID file found"
            pkill -f run_v2_sales_calls.sh
        fi
        ;;
    "status")
        if [ -f v2_sales_calls.pid ]; then
            PID=$(cat v2_sales_calls.pid)
            if ps -p $PID > /dev/null; then
                echo "🟢 V2 FINAL is running (PID: $PID)"
                echo "💬 Posting to: #sales-calls"
                echo "📊 Logs: tail -f logs/v2_live_sales_calls.log"
            else
                echo "🔴 V2 FINAL not running (stale PID file)"
                rm -f v2_sales_calls.pid
            fi
        else
            echo "🔴 V2 FINAL not running"
        fi
        ;;
    "logs")
        echo "📊 V2 Processing Logs:"
        tail -20 logs/v2_live_sales_calls.log 2>/dev/null || echo "No processing logs yet"
        echo ""
        echo "🔧 Daemon Logs:"
        tail -10 logs/v2_sales_calls_daemon.log 2>/dev/null || echo "No daemon logs yet"
        ;;
    *)
        echo "V2 FINAL Call Intelligence Control"
        echo "Usage: $0 {start|stop|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start  - Start V2 live processing"
        echo "  stop   - Stop V2 live processing" 
        echo "  status - Check if V2 is running"
        echo "  logs   - Show recent logs"
        ;;
esac