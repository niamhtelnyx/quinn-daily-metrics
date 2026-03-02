#!/bin/bash

echo "🚀 EASY CRONTAB SETUP FOR V1"
echo "=" * 35

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_LINE="*/30 * * * * cd $CURRENT_DIR && source .env && python3 fellow_cron_job.py >> logs/cron.log 2>&1"

echo "📁 Current directory: $CURRENT_DIR"
echo ""

echo "🔍 Your cron line will be:"
echo "   $CRON_LINE"
echo ""

echo "📋 OPTION 1 - AUTOMATIC SETUP:"
read -p "   Add this to your crontab automatically? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   🔧 Adding to crontab..."
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "   ✅ Added to crontab!"
    echo ""
    echo "   📊 Current crontab:"
    crontab -l | grep fellow_cron
else
    echo "   📋 Manual setup instructions:"
    echo ""
    echo "   1️⃣ Run: crontab -e"
    echo "   2️⃣ Add this line:"
    echo "      $CRON_LINE"
    echo "   3️⃣ Save and exit"
fi

echo ""
echo "🧪 TEST THE CRON JOB:"
echo "   cd $CURRENT_DIR"
echo "   source .env"
echo "   python3 fellow_cron_job.py"
echo ""

echo "📊 MONITOR CRON JOBS:"
echo "   # View current crontab"
echo "   crontab -l"
echo ""
echo "   # Watch cron logs"
echo "   tail -f $CURRENT_DIR/logs/cron.log"
echo ""
echo "   # Check if cron is running"
echo "   ps aux | grep cron"
echo ""

echo "✅ V1 cron job setup complete!"
echo "🕐 Next run will be within 30 minutes"