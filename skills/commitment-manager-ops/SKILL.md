---
name: commitment-manager-ops
description: Query and validate data using the Telnyx Commitment Manager API for billing operations and service order validation
---

# Commitment Manager Operations

## Overview

The Commitment Manager is Telnyx's authoritative billing system that tracks customer commitments, usage, and billing status. This skill teaches you how to query the API, validate data, and troubleshoot billing issues.

## API Basics

### Authentication

```bash
# API endpoint
COMMITMENT_MANAGER_API="https://api.telnyx.com/v2/commitment_manager/webhook"

# Authentication headers
username: "commitment_webhook"
webhook_api_key: "@R[7;rb`P*JD5<^UpUns1$aa"
```

### Base Request Pattern

```bash
curl -H "username: commitment_webhook" \
     -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1$aa" \
     -H "Content-Type: application/json" \
     "$COMMITMENT_MANAGER_API/endpoint?organization_id=$MCORGID"
```

## Core Operations

### 1. Get Current Commitment Status

**When to use**: Before any service order changes, to understand current billing state

```bash
# Get commitments for an organization (including cancelled ones)
curl -H "username: commitment_webhook" \
     -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1\$aa" \
     "https://api.telnyx.com/v2/commitment_manager/webhook/commitments?include_cancelled=true&organization_id={mcorgid}"
```

**Response includes** (array of commitments):
- `commitment_id`: Unique identifier for this commitment
- `organization_id`: The mission control organization ID
- `amount`: Monthly Minimum Commitment amount in cents
- `start_date`: When commitment period started (ISO format)
- `end_date`: When commitment period ends (ISO format)
- `status`: active | cancelled | expired | pending
- `created_at`: When commitment was created
- `updated_at`: Last modification timestamp
- `cancelled_at`: Cancellation timestamp (if applicable)

**Example Response**:
```json
{
  "data": [
    {
      "commitment_id": "cm_7f3b9e2a1c",
      "organization_id": "619c56b5-596b-4cc4-8b04-38fe8e05c750",
      "amount": 1500000,
      "currency": "USD",
      "start_date": "2024-02-01T00:00:00Z",
      "end_date": "2025-01-31T23:59:59Z",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-30T10:15:23Z",
      "cancelled_at": null
    }
  ]
}
```

### 2. Query Billing History

**When to use**: Investigating billing discrepancies, understanding payment history

```bash
# Get billing history for a date range
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/billing/history?start_date=2024-01-01&end_date=2024-12-31"
```

**Parameters**:
- `start_date`: Beginning of range (YYYY-MM-DD format)
- `end_date`: End of range (YYYY-MM-DD format)
- `include_usage`: true/false - include detailed usage breakdowns

### 3. Get Contract Details

**When to use**: Understanding contract terms before making changes

```bash
# Get full contract information
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/contract"
```

**Response includes**:
- Contract terms and conditions
- Penalty clauses for early termination
- Escalation schedules
- Renewal terms
- Special provisions

### 4. Check Usage Summary

**When to use**: Validating if customer is meeting commitment, planning adjustments

```bash
# Get usage summary for current period
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/usage/current"

# Get usage for specific month
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/usage/2024-12"
```

## Data Validation Workflows

### Before Service Order Changes

**Step 1: Query Current State**
```bash
# Get authoritative commitment data
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/commitment/current"
```

**Step 2: Analyze Response**
- Check if commitment is currently `active`
- Note current `mmc_amount` and dates
- Verify `sync_status` is `synchronized`
- Record `commitment_handler_id` for tracking

**Step 3: Validate Proposed Changes**
- Ensure new dates don't overlap existing active commitments
- Verify new MMC amount meets minimum requirements
- Check contract terms for any restrictions

### After Service Order Changes

**Step 1: Wait for Sync** (typically 2-5 minutes after SF changes)

**Step 2: Re-query Commitment Manager**
```bash
curl -H "Authorization: Bearer $CM_TOKEN" \
     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/commitment/current"
```

**Step 3: Validate Changes Reflected**
- Compare `mmc_amount` with new Salesforce value
- Verify `contract_start_date` and `contract_end_date` match
- Check `last_updated` timestamp is recent
- Ensure `sync_status` is `synchronized`

**Step 4: Cross-Reference with Salesforce**
```bash
# Query Salesforce for comparison
sf data query -o niamh@telnyx.com --query "
  SELECT Id, Name, Min_Monthly_Commit__c, Contract_Start_Date__c, Contract_End_Date__c, 
         Rev_Ops_Approved__c, commitment_handler_id__c 
  FROM Service_Order__c 
  WHERE Mission_Control_Account__c = '{mcorgid}' 
  AND Stage__c = 'Signed'
" --json
```

## Error Handling

### Common API Errors

**404 - Organization Not Found**
```json
{"error": "Organization not found", "organization_id": "invalid-id"}
```
- **Cause**: Invalid or non-existent mcorgid
- **Solution**: Verify mcorgid format and check Salesforce records

**401 - Unauthorized**
```json
{"error": "Invalid or expired token"}
```
- **Cause**: Missing or invalid API token
- **Solution**: Refresh token from Vault/1Password

**409 - Data Conflict**
```json
{"error": "Commitment modification in progress", "retry_after": 300}
```
- **Cause**: Another process is modifying the commitment
- **Solution**: Wait specified seconds and retry

**503 - Service Unavailable** 
```json
{"error": "Commitment Manager temporarily unavailable", "estimated_recovery": "2026-01-30T15:30:00Z"}
```
- **Cause**: System maintenance or outage
- **Solution**: Check status page, notify team, retry after recovery time

### Data Discrepancy Handling

**When Salesforce ≠ Commitment Manager:**

1. **Determine Timing**: Check `last_updated` timestamps
   - If SF timestamp > CM timestamp: Wait 5 minutes for sync
   - If CM timestamp > SF timestamp: Check for failed webhook

2. **Identify Authoritative Source**:
   - Recent changes: Salesforce is source of truth
   - Billing disputes: Commitment Manager is authoritative
   - Contract terms: Check original signed contract

3. **Resolution Steps**:
   ```bash
   # Trigger manual sync (if webhook failed)
   curl -X POST -H "Authorization: Bearer $CM_TOKEN" \
        "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/sync"
   
   # Or update incorrect system
   # (Follow service-order-ops SKILL for Salesforce updates)
   ```

## Integration with Service Orders

### Safe Service Order Modification Pattern

1. **Pre-flight Check**:
   ```bash
   # Query current commitment
   CM_CURRENT=$(curl -s -H "Authorization: Bearer $CM_TOKEN" \
                     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/commitment/current")
   
   # Extract key values for comparison
   CURRENT_MMC=$(echo $CM_CURRENT | jq '.commitment.mmc_amount')
   CURRENT_END=$(echo $CM_CURRENT | jq -r '.commitment.contract_end_date')
   ```

2. **Apply Service Order Changes** (using service-order-ops SKILL)

3. **Post-change Validation**:
   ```bash
   # Wait for webhook processing
   sleep 120
   
   # Re-query and validate
   CM_UPDATED=$(curl -s -H "Authorization: Bearer $CM_TOKEN" \
                     "$COMMITMENT_MANAGER_API/organizations/{mcorgid}/commitment/current")
   
   NEW_MMC=$(echo $CM_UPDATED | jq '.commitment.mmc_amount')
   
   # Compare with expected values
   if [ "$NEW_MMC" != "$EXPECTED_MMC" ]; then
     echo "⚠️  MMC mismatch detected - manual intervention required"
   fi
   ```

## Troubleshooting Common Issues

### Sync Delays
- **Normal**: 2-5 minutes after Salesforce changes
- **Extended**: Check webhook logs in Salesforce Chatter
- **Failed**: Look for error in Service Order FeedItems

### Data Inconsistencies
- **Recent changes**: Wait additional 5 minutes
- **Persistent issues**: Check for multiple active Service Orders
- **Historical data**: May require manual correction

### API Performance
- **Slow responses**: Check system status page
- **Timeouts**: Implement retry with exponential backoff
- **Rate limits**: Implement request throttling (max 10 req/sec)

## Best Practices

1. **Always query before modifying**: Get current state from Commitment Manager first
2. **Wait and validate**: Allow time for sync after Salesforce changes  
3. **Log important queries**: Record API calls for audit trail
4. **Handle errors gracefully**: Implement proper error handling and user feedback
5. **Use commitment_handler_id**: Track specific commitments across systems
6. **Monitor sync status**: Regular validation prevents billing surprises
7. **Document discrepancies**: Record any manual corrections made

## API Reference Quick Guide

| Endpoint | Purpose | Parameters |
|----------|---------|------------|
| `/organizations/{id}/commitment/current` | Get active commitment | None |
| `/organizations/{id}/billing/history` | Historical billing | start_date, end_date |
| `/organizations/{id}/contract` | Contract details | None |
| `/organizations/{id}/usage/current` | Current period usage | None |
| `/organizations/{id}/usage/{period}` | Specific period usage | period (YYYY-MM) |
| `/organizations/{id}/sync` | Trigger manual sync | None (POST) |

Remember: Commitment Manager is the authoritative source for billing. When in doubt, trust its data and investigate why Salesforce differs.