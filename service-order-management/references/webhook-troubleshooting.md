# Webhook Troubleshooting Guide

## Overview

This guide covers common webhook issues between Salesforce Service Orders and Commitment Manager, including diagnostics, resolution steps, and prevention strategies.

## Webhook Flow Architecture

```
Salesforce SO Update → MMC_webhook Flow → Commitment Manager API → Chatter Response
```

### Flow Trigger Conditions
The `MMC_webhook` flow triggers when ALL conditions are met:
1. `Stage__c` = "Signed"
2. `Mission_Control_Account__c` ≠ null
3. `Rev_Ops_Approved__c` = true AND isChanged (field was just updated)

## Diagnostic Commands

### 1. Check Service Order Status
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Stage__c, Rev_Ops_Approved__c, commitment_handler_id__c, Mission_Control_Account__r.Organization_ID__c FROM Service_Order__c WHERE Id = 'SO_ID'" --json
```

### 2. Check Webhook History
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Body, CreatedDate FROM FeedItem WHERE ParentId = 'SO_ID' AND Body LIKE '%webhook%' ORDER BY CreatedDate DESC LIMIT 5" --json
```

### 3. Validate in Commitment Manager
```bash
curl -H "username: commitment_webhook" -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1\$aa" "https://api.telnyx.com/v2/commitment_manager/webhook/commitments?include_cancelled=true&organization_id=ORG_ID"
```

### 4. Audit Failed Webhooks
```bash
python scripts/commitment_manager_validator.py audit
```

## Common Issues & Solutions

### Issue 1: No Webhook Activity

**Symptoms:**
- `Rev_Ops_Approved__c` = true
- `commitment_handler_id__c` = null
- No FeedItem records with webhook content

**Diagnosis:**
```bash
# Check flow trigger conditions
sf data query -o niamh@telnyx.com --query "SELECT Stage__c, Rev_Ops_Approved__c, Mission_Control_Account__c FROM Service_Order__c WHERE Id = 'SO_ID'"
```

**Common Causes:**
1. **Stage ≠ Signed**: Flow won't trigger
2. **Missing Mission Control Account**: No org ID to send
3. **Rev_Ops_Approved__c not changed**: Flow only triggers on field change

**Solutions:**
```bash
# Ensure proper stage and reset approval
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Stage__c=Signed Rev_Ops_Approved__c=false"

# Re-approve to trigger webhook
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Rev_Ops_Approved__c=true"
```

### Issue 2: HTTP 400 Bad Request

**Symptoms:**
- FeedItem shows "400 Bad Request"
- Webhook triggered but data rejected

**Common Causes:**
1. **Missing required fields** in payload
2. **Invalid date formats** 
3. **Missing organization_id**
4. **Malformed JSON payload**

**Solutions:**
```bash
# Verify organization ID exists
sf data query -o niamh@telnyx.com --query "SELECT Mission_Control_Account__r.Organization_ID__c FROM Service_Order__c WHERE Id = 'SO_ID'"

# For ramped commitments, ensure all detail records have valid dates
sf data query -o niamh@telnyx.com --query "SELECT Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c, Commit_Amount__c FROM Service_Order_Details__c WHERE Service_Order__c = 'SO_ID'"
```

### Issue 3: HTTP 401 Unauthorized

**Symptoms:**
- FeedItem shows "401 Unauthorized" 
- API credentials rejected

**Solutions:**
1. **Verify API credentials** in Salesforce Flow
2. **Check Commitment Manager API status**
3. **Validate username/API key** hasn't expired

### Issue 4: HTTP 500 Server Error  

**Symptoms:**
- FeedItem shows "500 Internal Server Error"
- Commitment Manager API issue

**Solutions:**
1. **Check Commitment Manager API health**
2. **Retry the webhook** after service recovery
3. **Contact platform team** if persistent

### Issue 5: Wrong Commitment Data

**Symptoms:**
- Webhook succeeds (201/204) but wrong data in CM
- commitment_handler_id populated but amounts/dates wrong

**Diagnosis - Static Commitments:**
```bash
# Check main SO data (webhook source for static)
sf data query -o niamh@telnyx.com --query "SELECT Contract_Start_Date__c, Contract_End_Date__c, Min_Monthly_Commit__c FROM Service_Order__c WHERE Id = 'SO_ID'"
```

**Diagnosis - Ramped Commitments:**
```bash  
# Check detail record normalized fields (webhook source for ramped)
sf data query -o niamh@telnyx.com --query "SELECT Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c, Commit_Amount__c FROM Service_Order_Details__c WHERE Service_Order__c = 'SO_ID' ORDER BY Cycle_Number__c"
```

**Solutions:**
```bash
# For static: Update main SO fields
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Contract_Start_Date__c=2026-02-01 Rev_Ops_Approved__c=false"

# For ramped: Update detail record base dates (normalized fields auto-calculate)
sf data update record -o niamh@telnyx.com -s Service_Order_Details__c -i DETAIL_ID -v "Commit_Start_Date__c=2026-02-01"

# Re-approve to send corrected data
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Rev_Ops_Approved__c=true"
```

## Response Code Reference

| Code | Meaning | Next Steps |
|---|---|---|
| **201** | Commitment created successfully | ✅ Verify commitment_handler_id populated |
| **204** | Commitment updated/terminated | ✅ Normal for updates and terminations |
| **400** | Bad request - invalid data | ❌ Check payload format and required fields |
| **401** | Unauthorized - bad credentials | ❌ Verify API keys in Flow configuration |
| **403** | Forbidden - access denied | ❌ Check org permissions and API access |
| **404** | Not found - resource missing | ❌ Verify organization_id exists in CM |
| **409** | Conflict - duplicate/overlap | ❌ Terminate existing commitments first |
| **500** | Server error - CM API issue | ❌ Retry later or contact platform team |

## Webhook Retry Strategies

### Manual Retry Process
1. **Reset approval flag**: `Rev_Ops_Approved__c = false`
2. **Fix underlying issue** (dates, data, etc.)
3. **Re-approve**: `Rev_Ops_Approved__c = true`
4. **Verify response** in new FeedItem

### Bulk Retry for Multiple SOs
```bash
# Find failed webhooks
python scripts/commitment_manager_validator.py audit

# For each failed SO:
# 1. Fix the underlying issue
# 2. Reset and re-approve
for so_id in failed_so_ids:
do
    sf data update record -o niamh@telnyx.com -s Service_Order__c -i $so_id -v "Rev_Ops_Approved__c=false"
    sleep 2
    sf data update record -o niamh@telnyx.com -s Service_Order__c -i $so_id -v "Rev_Ops_Approved__c=true"
    sleep 5
done
```

## Preventive Measures

### Pre-Approval Checklist
Before setting `Rev_Ops_Approved__c = true`:

1. **✅ Validate customer/org ID match**
```bash
python scripts/service_order_operations.py validate "Customer Name" "org-id-123"
```

2. **✅ Check for overlapping commitments**
```bash
python scripts/commitment_manager_validator.py validate "org-id-123"
```

3. **✅ Verify SO stage and data**
```bash
# Stage must be "Signed"
# Dates must be valid
# Mission Control Account must be linked
```

4. **✅ For ramped: Validate all detail records**
```bash
sf data query -o niamh@telnyx.com --query "SELECT COUNT() FROM Service_Order_Details__c WHERE Service_Order__c = 'SO_ID' AND (Commit_Amount__c = null OR Commit_Start_Date__c = null)"
```

### Data Quality Checks

```python
def validate_so_before_approval(so_id):
    """Validate Service Order data before webhook approval."""
    errors = []
    
    # Check main SO data
    so_data = sf.query(f"SELECT Stage__c, Mission_Control_Account__c, Contract_Start_Date__c FROM Service_Order__c WHERE Id = '{so_id}'")
    
    if so_data['records'][0]['Stage__c'] != 'Signed':
        errors.append("Stage must be 'Signed'")
    
    if not so_data['records'][0]['Mission_Control_Account__c']:
        errors.append("Mission Control Account required")
    
    # Check commitment type and validate accordingly
    commitment_type, details = check_commitment_type(so_id)
    
    if commitment_type == 'ramped' and not details:
        errors.append("Ramped commitment missing detail records")
    
    return errors
```

## Monitoring & Alerts

### Daily Health Check
```bash
# Check for new webhook failures (run daily)
sf data query -o niamh@telnyx.com --query "SELECT COUNT() FROM Service_Order__c WHERE Rev_Ops_Approved__c = true AND Stage__c = 'Signed' AND commitment_handler_id__c = null AND LastModifiedDate = TODAY"
```

### Weekly Audit
```bash
# Full webhook failure audit (run weekly)
python scripts/commitment_manager_validator.py audit
```

### Real-time Monitoring
Monitor FeedItem creation for webhook responses:
```sql
SELECT COUNT() 
FROM FeedItem 
WHERE CreatedDate = TODAY 
  AND (Body LIKE '%4%' OR Body LIKE '%5%')
  AND ParentId IN (SELECT Id FROM Service_Order__c)
```

## Emergency Procedures

### Critical Webhook Failure
1. **Identify scope**: How many SOs affected?
2. **Check CM API status**: Is the service healthy?
3. **Manual validation**: Verify data in Commitment Manager
4. **Bulk retry**: Use retry scripts for multiple failures
5. **Escalate**: Contact platform team if API issues persist

### Data Corruption Detection
1. **Cross-validate**: Compare SF data with CM API
2. **Identify discrepancies**: Wrong amounts, dates, or status
3. **Terminate incorrect**: Use CM API to cancel wrong commitments
4. **Resend correct**: Fix SF data and re-approve
5. **Document**: Track corrective actions taken

### Rollback Procedures
```bash
# Emergency: Terminate commitment in CM
curl -X DELETE -H "username: commitment_webhook" -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1\$aa" "https://api.telnyx.com/v2/commitment_manager/webhook/commitments/COMMITMENT_ID"

# Reset SO in Salesforce
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Stage__c=Terminated Rev_Ops_Approved__c=false commitment_handler_id__c=''"
```

## Contact Information

### Escalation Path
1. **RevOps Team**: First line for data/process issues
2. **Platform Team**: API and infrastructure issues  
3. **Salesforce Admin**: Flow configuration issues
4. **Commitment Manager Team**: CM API specific issues

### Reference Resources
- **Salesforce Flow**: MMC_webhook
- **CM API Docs**: Internal Confluence
- **Runbook**: Service Order Operations Runbook
- **Scripts**: service_order_operations.py, commitment_manager_validator.py