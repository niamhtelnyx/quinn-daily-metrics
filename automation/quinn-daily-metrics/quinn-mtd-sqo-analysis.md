# Quinn MTD SQO Tracking & 6-Month Historical Analysis

## 📊 Current MTD SQO Performance

**Quinn MTD SQOs (February 2026):** 31 SQOs (as of Feb 6)

## 📈 6-Month Historical Comparison

| **Month** | **SQOs** | **vs Avg** | **Trend** |
|-----------|----------|------------|-----------|
| **Jan 2026** | 113 | -43% ⬇️ | Recent |
| **Dec 2025** | 94 | -52% ⬇️ | Q4 End Dip |
| **Nov 2025** | 279 | +42% ⬆️ | Strong |
| **Oct 2025** | 309 | +57% ⬆️ | Peak |
| **Sep 2025** | 335 | +70% ⬆️ | **Best Month** |
| **Aug 2025** | 291 | +48% ⬆️ | Solid |

### 📉 Key Insights:

**6-Month Average:** 197 SQOs/month
**Q4 2025 Drop:** September peak (335) → December low (94) = -72%
**Recovery Pattern:** January showed 20% improvement vs December

## 🎯 February 2026 Pace Analysis

**Current Pace (6 days):** 31 SQOs
**Daily Average:** 5.17 SQOs/day
**Projected Month:** ~145 SQOs (28-day month)

**Comparison to Historical:**
- vs 6-Month Avg (197): **-26% below pace** ⚠️
- vs Last Month (113): **+28% above pace** ✅
- vs Peak Month (335): **-57% below pace** 📉

## 🎯 SOQL Queries for Automation

### MTD SQOs:
```sql
SELECT COUNT(Id) MTD_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND SDR_First_Zoom_Meeting__c = THIS_MONTH 
AND StageName != 'Stage 0 - Evaluation'
```

### Previous Month:
```sql
SELECT COUNT(Id) Last_Month_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND SDR_First_Zoom_Meeting__c = LAST_MONTH 
AND StageName != 'Stage 0 - Evaluation'
```

### 6-Month Average (requires individual month queries):
- August 2025: 291 SQOs
- September 2025: 335 SQOs  
- October 2025: 309 SQOs
- November 2025: 279 SQOs
- December 2025: 94 SQOs
- January 2026: 113 SQOs
- **Average:** 197 SQOs/month

## 📱 Enhanced Slack Output Format

```
📊 *Quinn Daily Metrics - February 6, 2026*

• *Sales Handoffs:* 88 (24h)
• *Unique Accounts Touched:* 337 (24h)  
• *Qualification Rate:* 21.43% SQL (6/28) (24h)
• *SQL Rate:* 65.91% (29/44) (7d)
• *SQO Rate:* 13.16% (5/38) (7d)

🎯 *MTD SQO Tracking:*
• *MTD SQOs:* 31 (6 days) | Pace: ~145/month
• *vs Last Month:* +28% ⬆️ (Jan: 113)
• *vs 6M Avg:* -26% ⬇️ (Avg: 197)
• *Peak Month:* Sep'25 (335 SQOs)

💡 *Key Insights:* February pace ahead of January but below 6-month average...

_Automated daily report • Data timeframes: 24h for activity, 7d for conversions, MTD for SQO trending_
```

## 🔄 Action Items:

1. **Add MTD SQO query** to daily automation
2. **Update Slack format** with trending context
3. **Monitor pace** against 6-month average (197)
4. **Alert on significant drops** (>30% below pace)
5. **Track recovery patterns** from Q4 dip

---

*Analysis Date: Feb 6, 2026*
*Data Sources: Salesforce Opportunity records*