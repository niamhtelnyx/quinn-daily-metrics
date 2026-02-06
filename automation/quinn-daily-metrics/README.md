# Quinn Daily Metrics Automation

Automated daily reporting system for Quinn bot performance metrics, posting to #quinn-daily-metrics Slack channel every day at 9:00 AM CST.

## 📊 Metrics Tracked

| **Metric** | **Description** | **Timeframe** | **Source** |
|------------|-----------------|---------------|-----------|
| **Sales Handoffs** | Count of handoffs handled by Quinn | 24 hours | Sales_Handoff__c |
| **Unique Accounts** | Count of unique accounts Quinn touched | 24 hours | Task records → Contact/Lead → Accounts |
| **Qualification Rate** | % of contacts Quinn marked as SQL | 24 hours | Contact.SDRbot_Perceived_Quality__c |
| **SQL Rate** | % of SQL contacts with Quinn opportunities | 7 days | Contact + Opportunity matching |
| **SQO Rate** | % of Quinn opportunities that reached Stage 1+ | 7 days | Opportunity.StageName progression |

## 🗓️ Schedule

- **Time:** 9:00 AM CST daily
- **Channel:** #quinn-daily-metrics (`C0AEDQ1K508`)
- **Cron:** `0 9 * * *`
- **Session:** Isolated background execution

## 📋 Sample Output

```
📊 *Quinn Daily Metrics - February 6, 2026*

• *Sales Handoffs:* 88 (24h)
• *Unique Accounts Touched:* 337 (24h)
• *Qualification Rate:* 21.43% SQL (6/28) (24h)
• *SQL Rate:* 65.91% (29/44) (7d)
• *SQO Rate:* 13.16% (5/38) (7d)

💡 *Key Insights:* Strong activity volume with 88 handoffs and 337 unique accounts touched...

_Automated daily report • Data timeframes: 24h for activity, 7d for conversions_
```

## 🔧 Setup Instructions

### 1. Create Cron Job

```bash
cron action=add job='{ 
  "name": "Quinn Daily Metrics Report",
  "schedule": {"kind": "cron", "expr": "0 9 * * *"},
  "sessionTarget": "isolated",
  "payload": {...}
}'
```

### 2. Verify Slack Channel Access

- Channel: #quinn-daily-metrics
- ID: `C0AEDQ1K508`
- Bot token: `$SLACK_BOT_TOKEN` (configured in environment)

### 3. Validate SOQL Queries

All queries documented in `quinn-daily-report-queries.md`

## 📁 Files

- `quinn-daily-report-queries.md` - Complete SOQL documentation
- `cron-job-config.json` - Exported cron job configuration
- `README.md` - This documentation

## 🔍 Quinn Bot Details

- **Name:** Quinn Taylor (bot)
- **Email:** quinn@telnyx.com
- **Salesforce User ID:** `005Qk000001pqtdIAA`
- **Role:** SDR Bot

## 🧠 Key Learning: SDR vs Owner Fields

**Critical correction made during development:**
- ❌ Wrong: `OwnerId = Quinn` (Quinn doesn't own opportunities)
- ✅ Correct: `SDR__c = Quinn` (Quinn is the SDR on opportunities)

This correction changed SQL Rate from 2.27% to 65.91% - a massive difference!

## 🚀 Future Enhancements

- Trending analysis vs previous days
- Alerting for significant drops
- Weekly/monthly rollup reports
- Integration with other bot metrics

## 🛠️ Troubleshooting

1. **No data showing:** Check Salesforce authentication
2. **Wrong channel:** Verify channel ID `C0AEDQ1K508`
3. **Formatting issues:** Ensure Slack markdown (`*bold*`, `_italic_`)
4. **Query failures:** Validate field names in Salesforce

---

*Built Feb 6, 2026 • Part of Telnyx RevOps automation suite*