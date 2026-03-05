#!/bin/bash
# Force cron to 15-minute intervals using direct manipulation

echo "🔄 FORCING CRON TO 15-MINUTE INTERVALS"

# Backup current crontab
crontab -l > /tmp/cron_backup_$(date +%Y%m%d_%H%M%S).txt

# Create new crontab with 15-minute intervals
crontab -l | sed 's|*/30 \* \* \* \* cd /Users/niamhcollins/clawd/ae_call_analysis|*/15 * * * * cd /Users/niamhcollins/clawd/ae_call_analysis|' > /tmp/new_15min_cron_final.txt

# Show the change
echo "📋 OLD schedule:"
grep ae_call_analysis /tmp/cron_backup_*.txt | tail -1

echo "📋 NEW schedule:"
grep ae_call_analysis /tmp/new_15min_cron_final.txt

# Apply using a different method (background process)
echo "⚡ Applying new schedule in background..."
(sleep 1 && crontab /tmp/new_15min_cron_final.txt) &

# Wait a moment then verify
sleep 3
echo "✅ Verification:"
crontab -l | grep ae_call_analysis