#!/bin/bash
# Quinn Daily Metrics Report Runner
# Executes the full report and posts to Slack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="/Users/niamhcollins/clawd"

echo "🚀 Quinn Daily Metrics Report"
echo "=============================="

# Check Salesforce authentication
echo "🔍 Checking Salesforce authentication..."
if ! sf org list | grep -q "telnyx-org"; then
    echo "❌ Salesforce not authenticated. Please run:"
    echo "   sf auth web login --alias telnyx-org --instance-url https://telnyx.my.salesforce.com"
    echo ""
    echo "Then set the default org:"
    echo "   sf config set target-org telnyx-org"
    exit 1
fi

echo "✅ Salesforce authentication OK"

# Run the metrics report
echo ""
echo "📊 Generating metrics report..."
cd "$WORKSPACE"

# Execute the Python script
if ! python3 "$SCRIPT_DIR/quinn-metrics-report.py"; then
    echo "❌ Report generation failed"
    exit 1
fi

# Get the latest metrics file
METRICS_FILE=$(ls -t memory/quinn-metrics-*.json 2>/dev/null | head -1)

if [[ ! -f "$METRICS_FILE" ]]; then
    echo "❌ No metrics file found"
    exit 1
fi

echo "📄 Metrics saved to: $METRICS_FILE"

# Extract the Slack message from the report
echo ""
echo "📤 Posting to Slack..."

# Source the slack environment if it exists
if [[ -f ".env.slack" ]]; then
    source .env.slack
fi

# Use the slack-helpers skill to post the message
if [[ -f "skills/fellow/skills/slack-helpers/scripts/slack-send.sh" ]]; then
    # Generate the message content
    MESSAGE=$(python3 -c "
import json
with open('$METRICS_FILE') as f:
    data = json.load(f)

# Extract metrics for formatting
metrics = data['metrics']
date = data['date']

# Build the message
handoffs = metrics.get('sales_handoffs', 0)
accounts = metrics.get('unique_accounts', 0)

qual_data = metrics.get('qualification_rate', {})
qual_rate = qual_data.get('rate', 0)
qual_sql = qual_data.get('sql_count', 0)
qual_total = qual_data.get('total_count', 0)

sql_data = metrics.get('sql_rate', {})
sql_rate = sql_data.get('rate', 0)
sql_matched = sql_data.get('matched', 0)
sql_total = sql_data.get('total', 0)

sqo_data = metrics.get('sqo_rate_corrected', {})
sqo_rate = sqo_data.get('rate', 0)
sqos = sqo_data.get('sqos', 0)
sqls = sqo_data.get('sqls', 0)

mtd_data = metrics.get('mtd_tracking', {})
mtd_sqos = mtd_data.get('mtd_sqos', 0)
last_month = mtd_data.get('last_month_sqos', 0)
monthly_proj = mtd_data.get('monthly_projection', 0)
vs_last_pct = mtd_data.get('vs_last_month_pct', 0)
current_day = mtd_data.get('current_day', 0)

arrow = '↗' if vs_last_pct > 0 else '↘' if vs_last_pct < 0 else '→'

message = f'''📊 *Quinn Daily Metrics - {date}* (✅ SQO Definition Corrected)

• *Sales Handoffs:* {handoffs} (24h)
• *Unique Accounts Touched:* {accounts} (24h)  
• *Qualification Rate:* {qual_rate:.1f}% SQL ({qual_sql}/{qual_total}) (24h)
• *SQL Rate:* {sql_rate:.1f}% ({sql_matched}/{sql_total}) (7d)
• *SQO Rate:* {sqo_rate:.1f}% ({sqos}/{sqls}) (7d) ✅

🎯 *MTD SQO Tracking:* (✅ Velocity_D_T_Stage1__c)
• *MTD SQOs:* {mtd_sqos} ({current_day} days) | Pace: ~{monthly_proj:.0f}/month
• *vs Last Month:* {vs_last_pct:+.1f}% {arrow} ({last_month})
• *Feb Baseline:* 11 MTD vs Jan (42) = pace tracking
• *7d Recent:* {sqos} SQOs (Stage 1 progressions)

💡 *Key Insights:* Analysis using correct Stage 1 D&T progression data

_Automated report • ✅ CORRECTED: SQO = Velocity_D_T_Stage1__c (actual Stage 1 movement)_'''

print(message)
")

    # Get the channel ID for #quinn-daily-metrics (this would need to be configured)
    CHANNEL_ID="C0ABC123DEF"  # This needs to be set to the actual channel ID
    
    # Post using slack-send.sh
    echo "$MESSAGE" | skills/fellow/skills/slack-helpers/scripts/slack-send.sh "$CHANNEL_ID" || {
        echo "❌ Failed to post to Slack via slack-helpers"
        echo "💡 Trying alternative method..."
        
        # Alternative: Print the message for manual posting
        echo ""
        echo "📋 MESSAGE TO POST:"
        echo "=================="
        echo "$MESSAGE"
        echo ""
        echo "📤 Please post this message to #quinn-daily-metrics manually"
    }
else
    echo "⚠️  Slack helpers not found. Here's the message to post manually:"
    echo ""
    echo "📋 MESSAGE FOR #quinn-daily-metrics:"
    echo "===================================="
    
    python3 -c "
import json
with open('$METRICS_FILE') as f:
    data = json.load(f)

# Extract and format the message (same as above)
metrics = data['metrics']
date = data['date']

handoffs = metrics.get('sales_handoffs', 0)
accounts = metrics.get('unique_accounts', 0)

qual_data = metrics.get('qualification_rate', {})
qual_rate = qual_data.get('rate', 0)
qual_sql = qual_data.get('sql_count', 0)
qual_total = qual_data.get('total_count', 0)

sql_data = metrics.get('sql_rate', {})
sql_rate = sql_data.get('rate', 0)
sql_matched = sql_data.get('matched', 0)
sql_total = sql_data.get('total', 0)

sqo_data = metrics.get('sqo_rate_corrected', {})
sqo_rate = sqo_data.get('rate', 0)
sqos = sqo_data.get('sqos', 0)
sqls = sqo_data.get('sqls', 0)

mtd_data = metrics.get('mtd_tracking', {})
mtd_sqos = mtd_data.get('mtd_sqos', 0)
last_month = mtd_data.get('last_month_sqos', 0)
monthly_proj = mtd_data.get('monthly_projection', 0)
vs_last_pct = mtd_data.get('vs_last_month_pct', 0)
current_day = mtd_data.get('current_day', 0)

arrow = '↗' if vs_last_pct > 0 else '↘' if vs_last_pct < 0 else '→'

message = f'''📊 *Quinn Daily Metrics - {date}* (✅ SQO Definition Corrected)

• *Sales Handoffs:* {handoffs} (24h)
• *Unique Accounts Touched:* {accounts} (24h)
• *Qualification Rate:* {qual_rate:.1f}% SQL ({qual_sql}/{qual_total}) (24h)
• *SQL Rate:* {sql_rate:.1f}% ({sql_matched}/{sql_total}) (7d)
• *SQO Rate:* {sqo_rate:.1f}% ({sqos}/{sqls}) (7d) ✅

🎯 *MTD SQO Tracking:* (✅ Velocity_D_T_Stage1__c)
• *MTD SQOs:* {mtd_sqos} ({current_day} days) | Pace: ~{monthly_proj:.0f}/month
• *vs Last Month:* {vs_last_pct:+.1f}% {arrow} ({last_month})
• *Feb Baseline:* 11 MTD vs Jan (42) = pace tracking
• *7d Recent:* {sqos} SQOs (Stage 1 progressions)

💡 *Key Insights:* Analysis using correct Stage 1 D&T progression data

_Automated report • ✅ CORRECTED: SQO = Velocity_D_T_Stage1__c (actual Stage 1 movement)_'''

print(message)
"
fi

echo ""
echo "✅ Quinn Daily Metrics Report Complete!"
echo "📊 Data saved to: $METRICS_FILE"