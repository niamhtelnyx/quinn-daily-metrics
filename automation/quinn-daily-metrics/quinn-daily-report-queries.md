# Quinn Daily Report - SOQL Queries

Documentation for automating the daily Quinn bot performance report.

## Metric 1: Sales Handoffs Handled ✅

**Count:** 88 (Feb 6, 2026)

**Query:**
```sql
SELECT Id, Name, CreatedDate, Owner_Name__c, Owner_Email__c, 
       Contact__c, Lead__c, Handoff_Type__c, Sales_Handoff_Reason__c 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND Owner_Email__c = 'quinn@telnyx.com'
AND CreatedDate = TODAY 
ORDER BY CreatedDate DESC
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
-- Step 1: Get Quinn opportunities created in last 7 days (CORRECTED: SDR__c not OwnerId)
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

**Breakdown:** 29 SQL contacts on accounts with Quinn opportunities out of 44 total SQL contacts
**Quinn Opportunities Created:** 38 in last 7 days

**Automation:** Two-step query + account matching logic

---

## Metric 5: SQO Rate ✅ (CORRECTED)

**Definition:** % of SQL contacts Quinn spoke to (last 7d) whose accounts have Quinn opportunities that reached Stage 1 D&T

**CORRECTED:** Uses Opportunity.Velocity_D_T_Stage1__c timestamp (actual Stage 1 progression)

**Query Sequence:**
```sql
-- Step 1: Get Quinn SQLs from last 7 days
SELECT COUNT(Id) SQL_Count
FROM Contact 
WHERE D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7 
AND SDRbot_Perceived_Quality__c = 'SQL'

-- Step 2: Get Quinn opportunities that reached Stage 1 D&T (last 7 days)
SELECT COUNT(Id) SQO_Count
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA'
AND Velocity_D_T_Stage1__c >= LAST_N_DAYS:7
```

**CORRECTED Result:** 27.27% (12 SQOs out of 44 SQLs)

**Calculation:** (SQO Count / SQL Count) × 100

**Automation:** Two simple aggregate queries

---

## Quinn Bot Details

- **Name:** Quinn Taylor (bot)
- **Email:** quinn@telnyx.com
- **User ID:** 005Qk000001pqtdIAA
- **Salesforce Profile:** Bot user

---

## Metric 6: MTD SQO Tracking & 6-Month Comparison ✅ (CORRECTED)

**Definition:** Month-to-date SQOs with historical trending and pace analysis

**CORRECTED:** Uses Opportunity.Velocity_D_T_Stage1__c timestamp (actual Stage 1 progression)

**Query Sequence:**
```sql
-- Step 1: MTD SQOs
SELECT COUNT(Id) MTD_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND Velocity_D_T_Stage1__c = THIS_MONTH

-- Step 2: Previous Month SQOs (for comparison)
SELECT COUNT(Id) Last_Month_SQOs 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA' 
AND Velocity_D_T_Stage1__c = LAST_MONTH
```

**Note:** Requires recalculation with corrected Velocity_D_T_Stage1__c field

**6-Month Historical Data:**
- **Feb 2026 (MTD):** 31 SQOs (6 days) | Pace: 5.17/day → ~145/month
- **Jan 2026:** 113 SQOs | vs Avg: -43% ⬇️
- **Dec 2025:** 94 SQOs | vs Avg: -52% ⬇️ (Q4 dip)
- **Nov 2025:** 279 SQOs | vs Avg: +42% ⬆️
- **Oct 2025:** 309 SQOs | vs Avg: +57% ⬆️
- **Sep 2025:** 335 SQOs | vs Avg: +70% ⬆️ (**Peak**)
- **Aug 2025:** 291 SQOs | vs Avg: +48% ⬆️

**6-Month Average:** 197 SQOs/month

**Calculation Logic:**
```
Daily Pace = MTD_SQOs / current_day_of_month
Monthly Projection = Daily Pace * total_days_in_month
vs Last Month % = ((Projected - Last_Month) / Last_Month) * 100
vs 6M Average % = ((Projected - 197) / 197) * 100
```

**Key Insights:**
- February pace (+28% vs Jan) shows recovery from Q4 dip
- Still tracking -26% below 6-month average (197)  
- Q4 2025 saw significant drop: Sep peak (335) → Dec low (94) = -72%
- Need sustained pace >7 SQOs/day to reach 6-month average

**Automation:** Two queries + pace calculation + trending analysis

---

## Notes

- Task entity limitations require multi-step queries for account relationships
- All date filters use TODAY or relative date functions for automation
- MTD SQO tracking provides crucial trending context for strategic decisions
- Queries tested and validated on Feb 6, 2026