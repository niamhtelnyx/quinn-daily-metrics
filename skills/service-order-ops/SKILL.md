---
name: service-order-ops
description: Manage Salesforce Service Orders and Commitment Manager logging — lookup, approve, terminate, and verify webhook delivery.
---

# Service Order Operations

## Safety Guardrails

1. **NEVER** set `Rev_Ops_Approved__c = true` without Niamh's explicit approval
2. **ALWAYS** check for overlapping commitments before activating a new SO
3. **ALWAYS** verify webhook response after any approval or termination
4. `Contract_End_Date__c` is a **formula field** — never try to update it directly

## ⚠️ MANDATORY: Customer/Org ID Validation

**CRITICAL: When both customer name AND org ID are provided in a request, ALWAYS validate they match before making ANY updates.**

### Validation Process:

1. **Look up customer's Service Orders by name:**
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Mission_Control_Account__c FROM Service_Order__c WHERE Name LIKE '%CUSTOMER_NAME%'" --json
```

2. **Get the Mission Control Account's Organization ID:**
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Organization_ID__c FROM Mission_Control_Account__c WHERE Id = '<MC_ACCOUNT_ID>'" --json
```

3. **Compare Organization_ID__c with the provided org ID:**
   - ✅ **MATCH**: Proceed with request
   - ❌ **MISMATCH**: **STOP IMMEDIATELY** and alert:
     ```
     🚨 ORG ID MISMATCH:
     - Provided: <PROVIDED_ORG_ID>
     - Actual: <ACTUAL_ORG_ID> 
     - Customer: <CUSTOMER_NAME>
     
     VERIFY CORRECT ORG ID BEFORE PROCEEDING
     ```

### Example Validation:
```bash
# Request: "Update Qomon (40a23927-e1e7-4528-a17a-ff19ec37c50e)"

# Step 1: Look up Qomon SOs
sf data query -o niamh@telnyx.com --query "SELECT Mission_Control_Account__c FROM Service_Order__c WHERE Name LIKE '%Qomon%' LIMIT 1" --json
# Returns: Mission_Control_Account__c = "a0T8Z000007xyz"

# Step 2: Get org ID
sf data query -o niamh@telnyx.com --query "SELECT Organization_ID__c FROM Mission_Control_Account__c WHERE Id = 'a0T8Z000007xyz'" --json
# Returns: Organization_ID__c = "40a23927-e1e7-4528-a17a-ff19ec37c50e"

# Step 3: Compare
# Provided: 40a23927-e1e7-4528-a17a-ff19ec37c50e
# Actual:   40a23927-e1e7-4528-a17a-ff19ec37c50e
# ✅ MATCH - Proceed with request
```

## Core Workflow

### 1. Lookup SOs

```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, commitment_handler_id__c, Opportunity__c, Mission_Control_Account__c FROM Service_Order__c WHERE Name LIKE '%ACCOUNT_NAME%'" --json
```

### 2. Assess Status

| Field | Meaning |
|---|---|
| `commitment_handler_id__c` = NULL | Not sent to Commitment Manager |
| `Stage__c` = Signed | Active / ready to send |
| `Stage__c` = Terminated | Done |
| `Rev_Ops_Approved__c` = true | Webhook has been triggered |

### 3. Check for Overlapping Commitments

Query all SOs for the same org. If an older SO has overlapping dates and a `commitment_handler_id__c`, **terminate it first**:

```bash
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <OLD_SO_ID> -v "Stage__c=Terminated" --json
```

Then verify termination webhook fired (expect 204):

```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Body, CreatedDate FROM FeedItem WHERE ParentId = '<OLD_SO_ID>' ORDER BY CreatedDate DESC LIMIT 3" --json
```

### 4. Fix Dates if Needed

End date is a formula (`Start + Duration`). Only update start date and/or duration:

```bash
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Contract_Start_Date__c=2026-01-01" --json
```

### 5. Approve (⚠️ REQUIRES EXPLICIT HUMAN APPROVAL)

```bash
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Rev_Ops_Approved__c=true" --json
```

This triggers the **MMC_webhook** flow (record-triggered on SO update). Flow filters:
- `Stage__c` = Signed
- `Mission_Control_Account__c` ≠ null
- `Rev_Ops_Approved__c` = true AND isChanged

### 6. Verify Webhook

Check Chatter for request/response:

```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Body, CreatedDate FROM FeedItem WHERE ParentId = '<SO_ID>' ORDER BY CreatedDate DESC LIMIT 3" --json
```

- **201** = commitment created
- **204** = terminated/updated

### 7. Confirm

Re-query SO to verify `commitment_handler_id__c` is populated.

### 8. Report

Post summary in Slack thread with: account name, SO name, action taken, commitment_handler_id, any issues.

## ⚠️ CRITICAL: Webhook Data Sources by SO Type

**Webhook data source depends on commitment type:**

### **Static Commitments** (Single flat amount)
- **No** `Service_Order_Details__c` records
- **Webhook reads**: Main `Service_Order__c` fields directly
- **Date changes**: Update main SO `Contract_Start_Date__c` only

### **Ramped Commitments** (Multiple amounts over time)  
- **Has** `Service_Order_Details__c` child records
- **Webhook reads**: `Service_Order_Details__c` normalized fields
- **Date changes**: Update BOTH main SO AND all detail records

### How to Identify SO Type
```bash
# Check for Service Order Details records
sf data query -o niamh@telnyx.com --query "SELECT Id FROM Service_Order_Details__c WHERE Service_Order__c = '<SO_ID>' LIMIT 1" --json

# Result interpretation:
# - Records found = RAMPED commitment (complex workflow)
# - No records = STATIC commitment (simple workflow)
```

### Object Structure (Ramped SOs only)
- **Object Name**: `Service_Order_Details__c` (PLURAL - not Detail__c)
- **Key Fields**:
  - `Commit_Start_Date__c` - Base start date (EDITABLE)
  - `Commit_End_Date__c` - Base end date (EDITABLE) 
  - `Commit_Start_Date_Normalized__c` - Webhook source (READ-ONLY)
  - `Commit_End_Date_Normalized__c` - Webhook source (READ-ONLY)
  - `Commit_Amount__c` - Monthly amount
  - `Cycle_Number__c` - Ramp sequence

### Query Service Order Details
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Cycle_Number__c, Commit_Amount__c, Commit_Duration__c, Commit_Start_Date__c, Commit_End_Date__c, Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c FROM Service_Order_Details__c WHERE Service_Order__c = '<SO_ID>' ORDER BY Cycle_Number__c" --json
```

## Modified Workflow for Date Changes

### **Static Commitments** (Simple workflow):
1. **Terminate existing commitments** (if any)
2. **Update main SO start date** 
3. **Reactivate and approve**
4. **Verify webhook AND Commitment Manager**

```bash
# Static SO date shift
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Stage__c=Terminated" --json
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Stage__c=Signed Contract_Start_Date__c=2026-02-01 Rev_Ops_Approved__c=false" --json
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Rev_Ops_Approved__c=true" --json
```

### **Ramped Commitments** (Complex workflow):
1. **Terminate existing commitments** (if any)
2. **Update main SO start date** 
3. **🚨 CRITICAL: Update EACH Service Order Detail record**
4. **Reactivate and approve**
5. **Verify both webhook AND Commitment Manager**

### Example: Shift ramped commitment by 1 month

```bash
# Step 1: Terminate if needed
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Stage__c=Terminated" --json

# Step 2: Update main SO 
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Stage__c=Signed Contract_Start_Date__c=2026-02-01 Rev_Ops_Approved__c=false" --json

# Step 3: Update EACH detail record (get IDs from query above)
sf data update record -o niamh@telnyx.com -s Service_Order_Details__c -i <DETAIL_1_ID> -v "Commit_Start_Date__c=2026-02-01" --json
sf data update record -o niamh@telnyx.com -s Service_Order_Details__c -i <DETAIL_2_ID> -v "Commit_Start_Date__c=2026-03-01" --json
sf data update record -o niamh@telnyx.com -s Service_Order_Details__c -i <DETAIL_3_ID> -v "Commit_Start_Date__c=2026-06-01" --json

# Step 4: Approve 
sf data update record -o niamh@telnyx.com -s Service_Order__c -i <SO_ID> -v "Rev_Ops_Approved__c=true" --json
```

## Commitment Manager Validation

### How to Check Active Commitments

**ALWAYS use include_cancelled=true to get complete picture:**

```bash
# Get ALL commitments (active and cancelled)
curl -H "username: commitment_webhook" -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1\$aa" "https://api.telnyx.com/v2/commitment_manager/webhook/commitments?include_cancelled=true&organization_id=<MCORG_ID>"
```

### Active Commitment Logic

A commitment is **ACTIVE** if BOTH conditions are true:
1. **cancelled_at** is `null` (not explicitly cancelled)
2. **period_end** is in the future (commitment period hasn't expired)

A commitment is **INACTIVE** if EITHER:
- **cancelled_at** is not `null` (explicitly cancelled)
- **period_end** is in the past (commitment period has expired)

### Example Analysis
```json
{
  "id": "abc123",
  "period_end": "2024-09-01",
  "cancelled_at": null
}
```
**Status**: INACTIVE (period ended September 2024, even though not explicitly cancelled)

```json
{
  "id": "def456", 
  "period_end": "2026-12-01",
  "cancelled_at": "2026-01-15T10:00:00Z"
}
```
**Status**: INACTIVE (explicitly cancelled, even though period hasn't ended)

```json
{
  "id": "ghi789",
  "period_end": "2026-12-01", 
  "cancelled_at": null
}
```
**Status**: ACTIVE (not cancelled and period hasn't ended)

## Common Pitfalls

1. **❌ Skipping customer/org ID validation** → Risk updating wrong customer's commitments
2. **❌ Only updating main SO start date** → Webhook still sends old dates
3. **❌ Trying to update normalized fields** → Permission error  
4. **❌ Wrong object name** → Service_Order_Detail__c vs Service_Order_Details__c
5. **❌ Not validating in Commitment Manager** → Miss failed webhooks
6. **❌ Using include_cancelled=false only** → Miss audit trail

## Domain Knowledge

- **Static SO**: Flat monthly commit (`Min_Monthly_Commit__c`) → webhook reads main SO fields
- **Ramped SO**: Escalating commits via `Service_Order_Details__c` child records → webhook reads detail records
- **organization_id** in Commitment Manager comes from `Mission_Control_Account__c` on the SO
- **MMC_webhook** flow ApiName: `MMC_webhook`
- Chatter `FeedItem` records on the SO show the full webhook request body and response
- **Webhook data sources**:
  - Static: `Service_Order__c.Contract_Start_Date__c`, `Min_Monthly_Commit__c`
  - Ramped: `Service_Order_Details__c.Commit_Start_Date_Normalized__c`, `Commit_Amount__c`

## Related Queries

```bash
# Lookup renewal opportunity
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, StageName, CloseDate FROM Opportunity WHERE AccountId = '<ACCT_ID>' AND Name LIKE '%Renewal%'" --json

# Query SO details (ramped) - CORRECTED
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Cycle_Number__c, Commit_Amount__c FROM Service_Order_Details__c WHERE Service_Order__c = '<SO_ID>' ORDER BY Cycle_Number__c" --json
```
