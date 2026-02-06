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

## Metric 5: SQO Rate ✅

**Definition:** % of opportunities that had AE intro calls in last 7 days that have since been SQO'd (moved to Stage 1+)

**Result:** 13.16% (5 out of 38 opportunities)

**Query:**
```sql
SELECT StageName, COUNT(Id) 
FROM Opportunity 
WHERE SDR__c = '005Qk000001pqtdIAA'
AND SDR_First_Zoom_Meeting__c >= LAST_N_DAYS:7
GROUP BY StageName
```

**Stage Breakdown:**
- Stage 1+ (SQO): 3 Discovery + 2 Proposal = 5 total
- Stage 0 (AE Qualification): 16
- Lost Business: 17
- Total with intro calls: 38

**Automation:** Single query + stage filtering (Stage >= 1)

---

## Quinn Bot Details

- **Name:** Quinn Taylor (bot)
- **Email:** quinn@telnyx.com
- **User ID:** 005Qk000001pqtdIAA
- **Salesforce Profile:** Bot user

---

## Notes

- Task entity limitations require multi-step queries for account relationships
- All date filters use TODAY or relative date functions for automation
- Queries tested and validated on Feb 6, 2026