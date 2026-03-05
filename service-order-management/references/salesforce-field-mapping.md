# Salesforce Field Mapping Reference

## Service Order Object Structure

### Service_Order__c (Main Object)

| Field API Name | Type | Description | Editable | Notes |
|---|---|---|---|---|
| `Id` | ID | Salesforce Record ID | No | System generated |
| `Name` | Text | Service Order Name | Yes | Usually customer name + SO number |
| `Stage__c` | Picklist | Contract Stage | Yes | Signed, Terminated, etc. |
| `Contract_Start_Date__c` | Date | Contract Start Date | Yes | When commitment billing begins |
| `Contract_End_Date__c` | Date | Contract End Date | No | **FORMULA FIELD** (Start + Duration) |
| `Contract_Duration__c` | Number | Contract Duration (months) | Yes | Usually 36 months |
| `Min_Monthly_Commit__c` | Currency | Monthly Commitment | Yes | For static commitments only |
| `Rev_Ops_Approved__c` | Checkbox | Revenue Ops Approval | Yes | **Triggers webhook when true** |
| `commitment_handler_id__c` | Text | Commitment Manager ID | No | Populated by webhook response |
| `Opportunity__c` | Lookup | Related Opportunity | Yes | Parent opportunity record |
| `Mission_Control_Account__c` | Lookup | Mission Control Account | Yes | Links to org ID |

### Service_Order_Details__c (Child Object - Ramped Only)

| Field API Name | Type | Description | Editable | Notes |
|---|---|---|---|---|
| `Id` | ID | Salesforce Record ID | No | System generated |
| `Name` | Text | Detail Record Name | Yes | Auto-generated |
| `Service_Order__c` | Lookup | Parent Service Order | Yes | Required relationship |
| `Cycle_Number__c` | Number | Ramp Sequence | Yes | 1, 2, 3, etc. |
| `Commit_Amount__c` | Currency | Monthly Amount | Yes | Commitment for this cycle |
| `Commit_Duration__c` | Number | Duration (months) | Yes | How long this level lasts |
| `Commit_Start_Date__c` | Date | Base Start Date | Yes | **EDITABLE** - Use for date changes |
| `Commit_End_Date__c` | Date | Base End Date | Yes | **EDITABLE** - Use for date changes |
| `Commit_Start_Date_Normalized__c` | Date | Webhook Start Date | No | **READ-ONLY** - Webhook data source |
| `Commit_End_Date_Normalized__c` | Date | Webhook End Date | No | **READ-ONLY** - Webhook data source |

## Mission Control Account Relationship

### Mission_Control_Account__c

| Field API Name | Type | Description | Notes |
|---|---|---|---|
| `Id` | ID | Salesforce Record ID | Links to Service Orders |
| `Name` | Text | Account Name | Customer organization name |
| `Organization_ID__c` | Text | Telnyx Organization ID | **Key for Commitment Manager** |

## Webhook Data Sources

### Static Commitments
Webhook reads directly from main `Service_Order__c` record:

```json
{
  "organization_id": "Mission_Control_Account__r.Organization_ID__c",
  "monthly_commitment_amount": "Min_Monthly_Commit__c", 
  "period_start": "Contract_Start_Date__c",
  "period_end": "Contract_End_Date__c"
}
```

### Ramped Commitments
Webhook reads from `Service_Order_Details__c` normalized fields:

```json
{
  "organization_id": "Service_Order__r.Mission_Control_Account__r.Organization_ID__c",
  "commitments": [
    {
      "monthly_commitment_amount": "Commit_Amount__c",
      "period_start": "Commit_Start_Date_Normalized__c", 
      "period_end": "Commit_End_Date_Normalized__c"
    }
  ]
}
```

## SOQL Query Patterns

### Basic Service Order Lookup
```sql
SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, 
       Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, 
       commitment_handler_id__c, Opportunity__c, Mission_Control_Account__c,
       Mission_Control_Account__r.Name, Mission_Control_Account__r.Organization_ID__c
FROM Service_Order__c 
WHERE Name LIKE '%CUSTOMER%'
```

### Service Order Details (Ramped)
```sql
SELECT Id, Name, Cycle_Number__c, Commit_Amount__c, Commit_Duration__c,
       Commit_Start_Date__c, Commit_End_Date__c, 
       Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c
FROM Service_Order_Details__c 
WHERE Service_Order__c = 'SO_ID' 
ORDER BY Cycle_Number__c
```

### Webhook Failure Audit
```sql  
SELECT Id, Name, Mission_Control_Account__r.Organization_ID__c
FROM Service_Order__c 
WHERE Rev_Ops_Approved__c = true 
  AND Stage__c = 'Signed'
  AND commitment_handler_id__c = null
```

### Webhook History (via Chatter)
```sql
SELECT Id, Body, CreatedDate, Type 
FROM FeedItem 
WHERE ParentId = 'SO_ID' 
  AND (Body LIKE '%webhook%' OR Body LIKE '%201%' OR Body LIKE '%204%')
ORDER BY CreatedDate DESC
```

## Update Patterns

### Terminate Service Order
```python
sf.Service_Order__c.update(so_id, {'Stage__c': 'Terminated'})
```

### Update Start Date (Static)
```python
so_update = {
    'Contract_Start_Date__c': '2026-02-01',
    'Stage__c': 'Signed', 
    'Rev_Ops_Approved__c': False  # Reset approval
}
sf.Service_Order__c.update(so_id, so_update)
```

### Update Start Date (Ramped)
```python
# Update main SO
sf.Service_Order__c.update(so_id, {
    'Contract_Start_Date__c': '2026-02-01',
    'Stage__c': 'Signed',
    'Rev_Ops_Approved__c': False
})

# Update EACH detail record
for detail_id in detail_ids:
    sf.Service_Order_Details__c.update(detail_id, {
        'Commit_Start_Date__c': calculated_date
    })
```

### Approve Service Order (Trigger Webhook)
```python
sf.Service_Order__c.update(so_id, {'Rev_Ops_Approved__c': True})
```

## MMC_webhook Flow Logic

The Salesforce Flow `MMC_webhook` triggers on Service Order updates when:

1. **`Stage__c` = "Signed"**
2. **`Mission_Control_Account__c` ≠ null**  
3. **`Rev_Ops_Approved__c` = true AND isChanged**

### Flow Behavior:
- Reads commitment data based on SO type (static vs ramped)
- Sends HTTP request to Commitment Manager API
- Posts response to Chatter (FeedItem)
- Updates `commitment_handler_id__c` on success

## Field Security & Permissions

### Integration User Profile
Required permissions for service account:

**Object Access:**
- Service_Order__c: Read, Edit
- Service_Order_Details__c: Read, Edit
- Mission_Control_Account__c: Read
- FeedItem: Read, Create

**Field Access:**
- All Service Order fields: Read/Write
- Mission_Control_Account__c.Organization_ID__c: Read
- NO delete permissions on any object

### Field-Level Security
Integration user can only write to:
- Service_Order__c: All fields except Contract_End_Date__c
- Service_Order_Details__c: Editable fields only (not normalized fields)

## Common Relationships

### Service Order → Opportunity → Account
```sql
SELECT Service_Order__r.Name, 
       Opportunity.Name,
       Opportunity.Account.Name
FROM Service_Order__c
```

### Service Order → Mission Control Account
```sql
SELECT Name,
       Mission_Control_Account__r.Name,
       Mission_Control_Account__r.Organization_ID__c  
FROM Service_Order__c
```

### Service Order Details → Service Order
```sql
SELECT Service_Order__r.Name,
       Service_Order__r.Contract_Start_Date__c,
       Cycle_Number__c,
       Commit_Amount__c
FROM Service_Order_Details__c
ORDER BY Service_Order__r.Name, Cycle_Number__c
```

## Data Integrity Rules

### Validation Rules
1. **Contract_End_Date__c is read-only** - Never update directly
2. **Rev_Ops_Approved__c requires Stage = Signed** - Cannot approve terminated SOs
3. **Mission_Control_Account__c required** - Must link to MC Account for webhook

### Business Logic
1. **Only one active commitment per org** - Terminate overlapping commitments
2. **Ramped details must be sequential** - Cycle numbers should increment
3. **Normalized dates auto-calculate** - Don't update manually

## Error Handling

### Common Update Errors
| Error | Cause | Solution |
|---|---|---|
| `INVALID_FIELD` Contract_End_Date__c | Trying to update formula field | Update Contract_Start_Date__c and Contract_Duration__c instead |
| `FIELD_INTEGRITY_EXCEPTION` | Missing required fields | Ensure Mission_Control_Account__c is populated |
| `INSUFFICIENT_ACCESS` | Field-level security | Use integration user with proper permissions |

### Webhook Errors (via Chatter)
| Response Code | Meaning | Action |
|---|---|---|
| 201 | Created successfully | Verify commitment_handler_id populated |
| 204 | Updated/terminated | Normal for terminations |
| 400 | Bad request | Check data format and required fields |
| 401 | Unauthorized | Validate API credentials |
| 500 | Server error | Check Commitment Manager API status |

## Best Practices

### Data Management
1. **Always validate customer/org ID** before updates
2. **Check for existing commitments** before creating new ones
3. **Terminate conflicting commitments** before activation
4. **Verify webhook responses** after approval/termination

### Query Optimization
1. **Use LIMIT clauses** for large result sets
2. **Index on frequently queried fields** (Name, Stage__c, etc.)
3. **Avoid unnecessary field retrievals** in SELECT statements
4. **Use bulk operations** for multiple updates

### Error Prevention
1. **Never update Contract_End_Date__c** directly
2. **Reset Rev_Ops_Approved__c** when changing dates
3. **Update ALL detail records** for ramped date changes
4. **Check commitment type** before applying update logic