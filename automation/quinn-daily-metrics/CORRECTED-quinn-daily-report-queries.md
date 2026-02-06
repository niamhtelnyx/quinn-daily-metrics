# Quinn Daily Report - CORRECTED SOQL Queries ✅

**🚨 CRITICAL CORRECTION APPLIED:** Fixed SQO definition to use `Velocity_D_T_Stage1__c` (actual Stage 1 D&T progression) instead of `SDR_First_Zoom_Meeting__c` (AE intro meetings)

Documentation for automating the daily Quinn bot performance report with ACCURATE SQO tracking.

## Metric 1: Sales Handoffs Handled ✅

**Count:** 88 (Feb 6, 2026)

**Query:**
```sql
SELECT COUNT() 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND Owner_Email__c = 'quinn@telnyx.com'
AND CreatedDate = TODAY
```

**Automation:** Single query returns count

---

## Metric 2: Unique Accounts Touched ✅

**Count:** 337 (Feb 6, 2026)

**Query Sequence (3-step due to Salesforce limitations):**

**Step 1 - Get Quinn's tasks today:**
```sql
SELECT Id, WhatId, WhoId, Subject, CreatedDate 
FROM Task 
WHERE OwnerId = '005Qk000001pqtdIAA' 
AND CreatedDate = TODAY
AND WhoId != null
```

**Step 2 - Resolve Contact IDs to Account IDs:**
```sql
SELECT DISTINCT AccountId, Account.Name
FROM Contact 
WHERE Id IN (/* Contact IDs from Step 1 where WhoId LIKE '003%' */)
AND AccountId != null
```

**Step 3 - Get Lead company information:**
```sql
SELECT DISTINCT ConvertedAccountId, Company, Name 
FROM Lead 
WHERE Id IN (/* Lead IDs from Step 1 where WhoId LIKE '00Q%' */)
```

**Automation:** Requires 3 queries + deduplication logic

---

## Metric 3: Qualification Rate ✅

**Definition:** % of contacts with SDRbot_Perceived_quality = SQL vs not SQL, for all contacts with Quinn Active Latest date in last 24 hours

**Result:** 21.43% (6 SQL out of 28 total contacts)

**Query:**
```sql
SELECT Id, Name, D_T_Quinn_Active_Latest__c, SDRbot_Perceived_Quality__c
FROM Contact 
WHERE D_T_Quinn_Active_Latest__c = TODAY
AND D_T_Quinn_Active_Latest__c != null
ORDER BY D_T_Quinn_Active_Latest__c DESC
```

**Calculation:** (COUNT(WHERE SDRbot_Perceived_Quality__c = 'SQL') / COUNT(total)) * 100

**Automation:** Single query + percentage calculation

---

## Metric 4: SQL Rate ✅

**Definition:** % of "SQL" perceived quality contacts that have an account with a quinn opportunity open. Quinn Active Latest in last 7 days

**Result:** 65.91% (29 out of 44 SQL contacts)

**Query Sequence:**
```sql
-- Step 1: Get Quinn opportunities created in last 7 days  
SELECT AccountId 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA'
AND CreatedDate >= LAST_N_DAYS:7

-- Step 2: Count SQL contacts on those accounts (with Quinn activity last 7 days)
SELECT COUNT(Id) 
FROM Contact 
WHERE SDRbot_Perceived_Quality__c = 'SQL'
AND D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7
AND AccountId IN (/* Account IDs from Step 1 */)

-- Step 3: Count total SQL contacts with Quinn activity last 7 days
SELECT COUNT(Id) 
FROM Contact 
WHERE SDRbot_Perceived_Quality__c = 'SQL'
AND D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7
```

**Automation:** Two-step query + account matching logic

---

## Metric 5: SQO Rate ✅ **CORRECTED**

**Definition:** % of Quinn opportunities that progressed to Stage 1+ (actual SQO via D&T timestamp)

**CORRECTED Query:** Using proper `Velocity_D_T_Stage1__c` field
```sql
-- Step 1: Count Quinn opportunities that reached Stage 1 (SQO) in last 7 days
SELECT COUNT(Id) SQO_Count
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND Velocity_D_T_Stage1__c >= LAST_N_DAYS:7

-- Step 2: Count total Quinn opportunities created in last 7 days
SELECT COUNT(Id) Total_Opps
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND CreatedDate >= LAST_N_DAYS:7

-- Step 3: Calculate SQO rate
-- SQO Rate = (SQO_Count / Total_Opps) * 100
```

**CORRECTED Baseline (Feb 6, 2026):**
- SQOs (7d): **12** opportunities with Stage 1 D&T progression
- Total Opps (7d): [calculate during automation]  
- **SQO Rate:** [calculate during automation]

**Previous (WRONG):** 5 out of 38 = 13.16% (using AE meeting timestamps)

**Automation:** Two queries + percentage calculation

---

## Metric 6: MTD SQO Tracking & 6-Month Comparison ✅ **CORRECTED**

**Definition:** Month-to-date SQOs with historical trending and pace analysis using **CORRECT** D&T Stage 1 timestamps

**CORRECTED Query Sequence:**
```sql
-- Step 1: MTD SQOs (CORRECTED)
SELECT COUNT(Id) MTD_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND Velocity_D_T_Stage1__c = THIS_MONTH

-- Step 2: Previous Month SQOs (CORRECTED)
SELECT COUNT(Id) Last_Month_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND Velocity_D_T_Stage1__c = LAST_MONTH
```

**CORRECTED Historical Data (Feb 6, 2026):**

| **Month** | **CORRECTED SQOs** | **vs 6M Avg** | **Trend** |
|-----------|---------------------|---------------|-----------|
| **Feb 2026 (MTD)** | **11** (6 days) → **~51/month** | **0%** ✅ | **Perfect Pace** |
| **Jan 2026** | **42** | **-18%** ⬇️ | Slight dip |
| **Dec 2025** | **29** | **-43%** ⬇️ | Q4 seasonal low |
| **Nov 2025** | **63** | **+24%** ⬆️ | Strong month |
| **Oct 2025** | **61** | **+20%** ⬆️ | Consistent |
| **Sep 2025** | **57** | **+12%** ⬆️ | Solid |
| **Aug 2025** | **54** | **+6%** ⬆️ | Baseline |

**CORRECTED 6-Month Average:** **51 SQOs/month** (vs 197 wrong)

**Key Insights (CORRECTED):**
- **February is tracking PERFECTLY** at 6-month average pace
- **Much more realistic and consistent** SQO volumes (50-60 range)
- **Q4 dip was real** but not catastrophic (29 vs 63 = -54%)
- **Steady performance** with natural seasonal variation

**Calculation Logic:**
```
Daily Pace = MTD_SQOs / current_day_of_month
Monthly Projection = Daily Pace * total_days_in_month  
vs Last Month % = ((Projected - Last_Month) / Last_Month) * 100
vs 6M Average % = ((Projected - 51) / 51) * 100
```

**Automation:** Two queries + pace calculation + trending analysis

---

## Quinn Bot Details

- **Name:** Quinn Taylor (bot)
- **Email:** quinn@telnyx.com
- **User ID:** 005Qk000001pqtdIAA
- **Salesforce Profile:** Bot user

---

## 🚨 CRITICAL CORRECTIONS APPLIED

### **SQO Definition Fixed:**
- ❌ **OLD (WRONG):** `SDR_First_Zoom_Meeting__c` (AE intro meetings)
- ✅ **NEW (CORRECT):** `Velocity_D_T_Stage1__c` (actual Stage 1 D&T progression)

### **Impact of Correction:**
- **MTD SQOs:** 11 vs 31 (wrong) = **65% reduction**
- **6M Average:** 51 vs 197 (wrong) = **74% reduction**  
- **February Pace:** Perfect vs "below average" = **Complete reversal**

### **Why This Matters:**
- **AE meetings ≠ SQOs** - Many meetings don't progress to Stage 1
- **Stage 1 D&T stamp** = True sales qualification milestone
- **More accurate forecasting** and performance tracking
- **Proper trending analysis** for strategic decisions

---

## Notes

- **CORRECTED:** All SQO tracking now uses proper `Velocity_D_T_Stage1__c` timestamps
- Task entity limitations require multi-step queries for account relationships  
- All date filters use TODAY or relative date functions for automation
- **Validation completed:** Feb 6, 2026 with accurate baseline data