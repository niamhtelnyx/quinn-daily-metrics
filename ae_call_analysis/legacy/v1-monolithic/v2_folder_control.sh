#!/bin/bash
# V2 FINAL Call Intelligence FOLDER-SPECIFIC Control Script

cd /Users/niamhcollins/clawd/ae_call_analysis

case "$1" in
    "start")
        echo "🚀 Starting V2 FINAL Call Intelligence FOLDER-SPECIFIC..."
        nohup ./run_v2_folder_specific.sh > logs/v2_folder_daemon.log 2>&1 & 
        echo $! > v2_folder.pid
        echo "✅ Started with PID: $(cat v2_folder.pid)"
        echo "📁 Folder: https://drive.google.com/drive/folders/1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
        ;;
    "stop")
        if [ -f v2_folder.pid ]; then
            PID=$(cat v2_folder.pid)
            echo "🛑 Stopping V2 FOLDER-SPECIFIC (PID: $PID)..."
            kill $PID 2>/dev/null
            rm -f v2_folder.pid
            echo "✅ Stopped"
        else
            echo "⚠️ No PID file found"
            pkill -f run_v2_folder_specific.sh
        fi
        ;;
    "status")
        if [ -f v2_folder.pid ]; then
            PID=$(cat v2_folder.pid)
            if ps -p $PID > /dev/null; then
                echo "🟢 V2 FOLDER-SPECIFIC is running (PID: $PID)"
                echo "📁 Folder: 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
                echo "💬 Posting to: #sales-calls"
                echo "🔗 Features: AI Analysis + Salesforce Links + Folder-Specific Search"
                echo "📊 Logs: tail -f logs/v2_folder_specific.log"
            else
                echo "🔴 V2 FOLDER-SPECIFIC not running (stale PID file)"
                rm -f v2_folder.pid
            fi
        else
            echo "🔴 V2 FOLDER-SPECIFIC not running"
        fi
        ;;
    "logs")
        echo "📊 V2 Processing Logs:"
        tail -20 logs/v2_folder_specific.log 2>/dev/null || echo "No processing logs yet"
        echo ""
        echo "🔧 Daemon Logs:"
        tail -10 logs/v2_folder_daemon.log 2>/dev/null || echo "No daemon logs yet"
        ;;
    "folder")
        echo "📁 Target Folder Details:"
        echo "   🔗 URL: https://drive.google.com/drive/folders/1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
        echo "   🆔 ID: 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
        echo "   📋 Contains subfolders organized by AE email addresses"
        echo "   🔍 Searches recursively for 'Notes by Gemini' documents"
        ;;
    *)
        echo "V2 FINAL Call Intelligence FOLDER-SPECIFIC Control"
        echo "Usage: $0 {start|stop|status|logs|folder}"
        echo ""
        echo "Commands:"
        echo "  start  - Start V2 folder-specific processing"
        echo "  stop   - Stop V2 folder-specific processing" 
        echo "  status - Check if V2 is running"
        echo "  logs   - Show recent logs"
        echo "  folder - Show folder details"
        echo ""
        echo "📁 FOLDER-SPECIFIC Features:"
        echo "   ✅ Searches ONLY in specified Drive folder"
        echo "   ✅ Recursive search through subfolders"
        echo "   ✅ AI analysis + Salesforce links"
        echo "   ✅ Posts to #sales-calls every 30 minutes"
        ;;
esac