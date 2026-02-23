# Quinn Daily Metrics Automation

Automated daily reporting system for Quinn bot performance metrics, posting to #quinn-daily-metrics Slack channel every day at 9:00 AM CST.

## 📊 Metrics Tracked & Calculations

### 1. **Sales Handoffs** (24h activity)
**What it measures:** Volume of leads/contacts Quinn handed off to sales today  
**Calculation:** Simple count  
```
COUNT(Sales_Handoff__c WHERE Owner_Name__c = 'Quinn Taylor' AND CreatedDate = TODAY)
```
**How to interpret:**
- **50-100:** Normal daily volume
- **>100:** High activity day  
- **<30:** Low activity, investigate Quinn health

### 2. **Unique Accounts Touched** (24h activity)  
**What it measures:** Breadth of Quinn's outreach - how many different companies contacted  
**Calculation:** Deduplicated account count from all Quinn's tasks today  
```
Step 1: Get Quinn's tasks today → Extract Contact/Lead IDs
Step 2: Map Contact IDs → Account IDs  
Step 3: Map Lead IDs → Company names
Step 4: Deduplicate unique accounts + companies
```
**How to interpret:**
- **200-400:** Healthy outreach breadth
- **>400:** Exceptional coverage
- **<150:** Narrow focus, may miss opportunities

### 3. **Qualification Rate** (24h conversion)
**What it measures:** Quinn's accuracy at identifying qualified leads  
**Calculation:** 
```
(SQL Contacts / Total Contacts Quinn spoke to today) × 100
SQL Count = COUNT(Contact WHERE D_T_Quinn_Active_Latest__c = TODAY AND SDRbot_Perceived_Quality__c = 'SQL')  
Total Count = COUNT(Contact WHERE D_T_Quinn_Active_Latest__c = TODAY)
```
**How to interpret:**
- **15-25%:** Healthy qualification rate
- **>30%:** Excellent targeting or lucky day
- **<10%:** Poor lead quality or Quinn needs tuning

### 4. **SQL Rate** (7d funnel performance)
**What it measures:** How many SQLs Quinn found actually converted to opportunities  
**Calculation:**
```
(SQL Contacts with Quinn Opportunities / Total SQL Contacts last 7d) × 100

Numerator: COUNT(SQL Contacts WHERE AccountId IN [Quinn Opportunity Account IDs])
Denominator: COUNT(SQL Contacts WHERE D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7)
```
**How to interpret:**
- **50-70%:** Good SQL→Opportunity conversion
- **>70%:** Excellent qualified lead follow-up
- **<40%:** SQLs not converting, investigate handoff process

### 5. **SQO Rate** (7d progression tracking) ✅ CORRECTED
**What it measures:** How many Quinn opportunities actually progress to Stage 1 D&T  
**Calculation:**
```
(Quinn SQOs / Quinn SQLs last 7d) × 100

SQOs = COUNT(Opportunity WHERE SDR__c = 'Quinn' AND Velocity_D_T_Stage1__c >= LAST_N_DAYS:7)
SQLs = COUNT(Contact WHERE D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7 AND SDRbot_Perceived_Quality__c = 'SQL')
```
**How to interpret:**
- **20-30%:** Healthy SQL→SQO progression  
- **>30%:** Excellent opportunity quality
- **<15%:** Poor conversion, investigate handoff quality or AE follow-up

### 6. **MTD SQO Tracking** (Monthly trending)
**What it measures:** Month-to-date Stage 1 progressions with pace analysis  
**Calculation:**
```
MTD Count = COUNT(Opportunity WHERE SDR__c = 'Quinn' AND Velocity_D_T_Stage1__c = THIS_MONTH)
Daily Pace = MTD Count / Days Elapsed This Month  
Monthly Projection = Daily Pace × Total Days in Month
vs Last Month % = ((Projected - Last Month Actual) / Last Month Actual) × 100
```
**How to interpret:**
- **Pace >1.5/day:** Strong month (~45+ monthly)
- **Pace 1.0-1.5/day:** Average performance (~30-45)  
- **Pace <1.0/day:** Below target, investigate issues

## 🔍 Reading the Metrics Together

**🎯 Healthy Quinn Performance Pattern:**
- Handoffs: 50-100 | Accounts: 200-400 | Qual Rate: 15-25% | SQL Rate: 50-70% | SQO Rate: 20-30%

**🚨 Common Issue Patterns:**

| **Pattern** | **What It Means** | **Action Needed** |
|-------------|-------------------|-------------------|
| High handoffs, low accounts | Quinn hitting same accounts repeatedly | Expand target list |
| High qual rate, low SQL rate | Good qualification but poor handoff process | Check AE follow-up |  
| High SQL rate, low SQO rate | Opportunities created but not progressing | Investigate Stage 1 conversion |
| All metrics low | Quinn system issue | Check bot health |
| Handoffs up, all rates down | Lead quality degraded | Review lead sources |

**💡 Trending Insights:**
- **Week-over-week:** Look for consistent patterns vs one-off spikes
- **Day-of-week:** Monday/Friday typically lower than mid-week  
- **MTD pace:** Early month pace often higher than sustainable rate

## 🗓️ Schedule

- **Time:** 9:00 AM CST daily
- **Channel:** #quinn-daily-metrics (`C0AEDQ1K508`)
- **Cron:** `0 9 * * *`
- **Session:** Isolated background execution

## 📋 Sample Output (How to Read Each Number)

```
📊 *Quinn Daily Metrics - February 6, 2026*

• *Sales Handoffs:* 88 (24h)
   └─ 88 handoffs created today ✅ High activity
   
• *Unique Accounts Touched:* 337 (24h)  
   └─ 337 different companies contacted today ✅ Great coverage
   
• *Qualification Rate:* 21.43% SQL (6/28) (24h)
   └─ 6 SQLs out of 28 total contacts = 21.43% ✅ Good targeting
   
• *SQL Rate:* 65.91% (29/44) (7d)
   └─ 29 SQLs (last 7d) with Quinn opps out of 44 total SQLs ✅ Strong conversion
   
• *SQO Rate:* 27.27% (12/44) (7d) ✅ CORRECTED  
   └─ 12 opps reached Stage 1 D&T out of 44 SQLs = 27.27% ✅ Excellent progression

🎯 *MTD SQO Tracking:* ✅ Velocity_D_T_Stage1__c
• *MTD SQOs:* 11 (6 days) | Pace: ~51/month
   └─ 11 Stage 1 progressions ÷ 6 days = 1.83/day pace
• *vs Last Month:* -74% ⬇️ (42)  
   └─ Projected 51 vs Jan actual 42 = big improvement
• *vs 6M Avg:* Tracking to average
   └─ On pace to meet historical average performance

💡 *Key Insights:* Excellent day - high activity (88 handoffs), broad reach (337 accounts), 
good qualification accuracy (21%), and strong funnel progression (27% SQO rate)

_Automated report • ✅ CORRECTED: SQO = Velocity_D_T_Stage1__c (actual Stage 1 movement)_
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