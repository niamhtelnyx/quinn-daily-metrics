---
name: service-order-management
description: Manage Telnyx Service Orders in Salesforce and Commitment Manager integration. Includes validation workflows, PDF parsing, webhook monitoring, customer lookup, approval processes, and commitment tracking for both static and ramped commitments. Use when managing service orders, validating commitments, troubleshooting webhook failures, or processing service order documents.
---

# Service Order Management

## Overview

Complete Service Order management for Telnyx including Salesforce CRUD operations, Commitment Manager webhook integration, PDF document parsing, and audit workflows. Handles both static and ramped commitment types with proper validation and safety guardrails.

## Quick Start

1. **Lookup Service Orders**: `sf data query` with customer name
2. **Find actual PDF**: Check Salesforce attachments FIRST (ContentDocumentLink)
3. **Validate Customer/Org ID**: Always verify identity before updates
4. **🚨 Validate Commit Cycle**: ALWAYS check `Commit_Cycle__c` (Annual vs Monthly) 
5. **Check MC Account fields**: Use describe() to find available revenue fields
6. **Check for overlaps**: Terminate conflicting commitments first
7. **Approve carefully**: `Rev_Ops_Approved__c = true` requires explicit approval
8. **Verify webhook**: Check Chatter for 201/204 response codes

## 🚨 CRITICAL LESSONS LEARNED

### PDF Discovery: Always Check Salesforce Attachments FIRST
❌ **DON'T**: Look for sample/test PDFs in workspace directories
✅ **DO**: Query ContentDocumentLink for actual signed contracts

```bash
# Find PDFs attached to Opportunity
SELECT ContentDocumentId, ContentDocument.Title, ContentDocument.LatestPublishedVersionId
FROM ContentDocumentLink 
WHERE LinkedEntityId = 'OPPORTUNITY_ID' AND ContentDocument.FileExtension = 'pdf'
```

### 🔧 Ironclad Workflow PDF Discovery: The Hidden Location
❌ **DON'T**: Stop at ContentDocumentLink searches
✅ **DO**: Check legacy Attachments on Ironclad Workflow records

**CRITICAL DISCOVERY**: Service Order PDFs are often stored as legacy Attachments on `ironclad__Ironclad_Workflow__c` records, NOT as modern ContentDocumentLinks.

```bash
# 1. Find Ironclad Workflow first
SELECT Id, Name FROM ironclad__Ironclad_Workflow__c WHERE Name LIKE '%CustomerName%'

# 2. Check LEGACY ATTACHMENTS on workflow (this is where PDFs hide!)
SELECT Id, Name, ContentType, BodyLength FROM Attachment 
WHERE ParentId = 'WORKFLOW_ID' AND ContentType = 'application/pdf'

# 3. Download using Attachment API (not ContentVersion)
curl -H "Authorization: Bearer TOKEN" "https://instance.salesforce.com/services/data/v59.0/sobjects/Attachment/ATTACHMENT_ID/Body"
```

**Real Example**: DashQuill contract was found at `Attachment.Id = 00PQk00000PJCezMAH` on Ironclad Workflow `a15Qk00000TSfNjIAL`, not in any ContentDocumentLink searches.

### Mission Control Account Validation: Field Discovery Required
❌ **DON'T**: Assume field names without checking
✅ **DO**: Use describe() to discover available fields dynamically

```python
# Always check available fields first
mc_describe = sf.Mission_Control_Account__c.describe()
available_fields = [field['name'] for field in mc_describe['fields']]
```

### 🚨 Commit Cycle Validation: Annual vs Monthly Critical Check
❌ **DON'T**: Validate only the commitment amount without checking commit cycle
✅ **DO**: ALWAYS validate Commit_Cycle__c to prevent 12x billing errors

**CRITICAL DISCOVERY**: The `Commit_Cycle__c` field determines how `Min_Monthly_Commit__c` is interpreted!

```python
# ALWAYS check commit cycle before validation
commit_cycle_query = """
    SELECT Min_Monthly_Commit__c, Commit_Cycle__c, Commit_Cycle_Text__c
    FROM Service_Order__c 
    WHERE Id = 'SO_ID'
"""

# Validation logic
if commit_cycle == 'Annual':
    # Min_Monthly_Commit__c stores ANNUAL amount
    annual_commitment = so['Min_Monthly_Commit__c']
    monthly_equivalent = annual_commitment / 12
elif commit_cycle == 'Monthly':
    # Min_Monthly_Commit__c stores MONTHLY amount  
    monthly_commitment = so['Min_Monthly_Commit__c']
    annual_equivalent = monthly_commitment * 12
```

**Real Example**: Go Spark Text had:
- **Contract**: "$10,000 (the 'Minimum Annual Commitment')"
- **SO Commit_Cycle__c**: "Annual"  
- **SO Min_Monthly_Commit__c**: "10000.00"
- **Result**: ✅ CORRECT ($10,000 annual = $833.33/month)

**Common Error Pattern**:
- **Contract**: "$10,000 annual"
- **SO misconfig**: Commit_Cycle__c = "Monthly", Min_Monthly_Commit__c = "10000.00" 
- **Result**: ❌ CRITICAL ERROR (Would bill $120,000/year instead of $10,000/year)

```bash
# Quick commit cycle check
SELECT Name, Min_Monthly_Commit__c, Commit_Cycle__c, Commit_Cycle_Text__c
FROM Service_Order__c 
WHERE Opportunity__c = 'OPPORTUNITY_ID'
```

## Core Workflows

### 1. Service Order Lookup & Status Check

```bash
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, commitment_handler_id__c, Opportunity__c, Mission_Control_Account__c FROM Service_Order__c WHERE Name LIKE '%CUSTOMER_NAME%'" --json
```

**Status Assessment**:
- `commitment_handler_id__c = NULL`: Not sent to Commitment Manager
- `Stage__c = Signed`: Active / ready to send
- `Stage__c = Terminated`: Done
- `Rev_Ops_Approved__c = true`: Webhook triggered

### 2. Customer/Org ID Validation (MANDATORY)

⚠️ **CRITICAL**: When both customer name AND org ID provided, ALWAYS validate they match:

```bash
# Step 1: Get Mission Control Account from Service Order
sf data query -o niamh@telnyx.com --query "SELECT Mission_Control_Account__c FROM Service_Order__c WHERE Name LIKE '%CUSTOMER%' LIMIT 1" --json

# Step 2: Get Organization ID from MC Account
sf data query -o niamh@telnyx.com --query "SELECT Organization_ID__c FROM Mission_Control_Account__c WHERE Id = 'MC_ACCOUNT_ID'" --json

# Step 3: Compare with provided org ID
# ✅ MATCH = Proceed | ❌ MISMATCH = STOP + Alert
```

### 3. Commitment Type Detection & Management

**Query Service Order Details** (determines commitment type):
```bash
sf data query -o niamh@telnyx.com --query "SELECT Id FROM Service_Order_Details__c WHERE Service_Order__c = 'SO_ID' LIMIT 1" --json
```

- **Records found** = RAMPED commitment (complex workflow)
- **No records** = STATIC commitment (simple workflow)

#### Static Commitments
- Single flat amount from main SO `Min_Monthly_Commit__c`
- Webhook reads main SO fields directly
- Simple date changes: Update main SO start date only

#### Ramped Commitments  
- Multiple amounts over time via `Service_Order_Details__c` child records
- Webhook reads detail record normalized fields
- Complex date changes: Update BOTH main SO AND all detail records

### 4. Overlap Management & Termination

Check for overlapping commitments before activation:
```bash
# Terminate conflicting SO
sf data update record -o niamh@telnyx.com -s Service_Order__c -i OLD_SO_ID -v "Stage__c=Terminated" --json

# Verify termination webhook (expect 204)
sf data query -o niamh@telnyx.com --query "SELECT Body, CreatedDate FROM FeedItem WHERE ParentId = 'SO_ID' ORDER BY CreatedDate DESC LIMIT 3" --json
```

### 5. Service Order Approval (⚠️ REQUIRES EXPLICIT APPROVAL)

```bash
# Set approval flag (triggers MMC_webhook flow)
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Rev_Ops_Approved__c=true" --json
```

**MMC_webhook Flow Triggers**:
- `Stage__c = Signed`
- `Mission_Control_Account__c ≠ null`
- `Rev_Ops_Approved__c = true` AND isChanged

### 6. Webhook Verification

```bash
# Check Chatter for webhook response
sf data query -o niamh@telnyx.com --query "SELECT Body, CreatedDate FROM FeedItem WHERE ParentId = 'SO_ID' ORDER BY CreatedDate DESC LIMIT 3" --json
```

**Response Codes**:
- **201** = Commitment created successfully
- **204** = Terminated/updated successfully
- **4xx/5xx** = Error requiring investigation

### 7. Date Change Workflows

#### Static Commitment Date Change:
```bash
# 1. Terminate existing
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Stage__c=Terminated" --json

# 2. Update start date + reset approval
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Stage__c=Signed Contract_Start_Date__c=2026-02-01 Rev_Ops_Approved__c=false" --json

# 3. Re-approve
sf data update record -o niamh@telnyx.com -s Service_Order__c -i SO_ID -v "Rev_Ops_Approved__c=true" --json
```

#### Ramped Commitment Date Change:
```bash
# Same as static, PLUS update each Service Order Detail record:
sf data update record -o niamh@telnyx.com -s Service_Order_Details__c -i DETAIL_ID -v "Commit_Start_Date__c=2026-02-01" --json
```

### 8. Commitment Manager Validation

```bash
# Get ALL commitments (active and cancelled)
curl -H "username: commitment_webhook" -H "webhook_api_key: @R[7;rb\`P*JD5<^UpUns1\$aa" "https://api.telnyx.com/v2/commitment_manager/webhook/commitments?include_cancelled=true&organization_id=ORG_ID"
```

**Active Commitment Logic**:
- **ACTIVE** if: `cancelled_at = null` AND `period_end > now`
- **INACTIVE** if: `cancelled_at ≠ null` OR `period_end < now`

### 9. Audit Webhook Failures

```bash
# Find SOs with potential webhook failures
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Mission_Control_Account__r.Organization_ID__c FROM Service_Order__c WHERE Rev_Ops_Approved__c = true AND Stage__c = 'Signed' AND commitment_handler_id__c = null" --json
```

### 🆕 10. Mission Control Account Validation (Enhanced)

**🔍 STEP 1: Field Discovery (CRITICAL)**
Never assume field names exist. Always check available fields first:

```python
# Discover available MC Account fields
mc_describe = sf.Mission_Control_Account__c.describe()
available_fields = [field['name'] for field in mc_describe['fields']]

# Look for revenue/status fields dynamically
revenue_fields = [f for f in available_fields if 'revenue' in f.lower()]
status_fields = [f for f in available_fields if 'status' in f.lower()]
```

**🎯 STEP 2: Build Dynamic Query**

```python
# Start with guaranteed fields
base_fields = ['Id', 'Name', 'Organization_ID__c', 'CreatedDate']

# Add revenue fields if available
potential_revenue_fields = [
    'Monthly_Revenue__c', 'Lifetime_Revenue__c', 'MTD_Revenue__c',
    'YTD_Revenue__c', 'Previous_Month_Revenue__c'
]

query_fields = base_fields[:]
for field in potential_revenue_fields:
    if field in available_fields:
        query_fields.append(field)
```

**⚡ STEP 3: Validate Organization ID**

```python
# Get Service Order's MC Account
so_mc_query = f"SELECT Mission_Control_Account__r.Organization_ID__c FROM Service_Order__c WHERE Id = '{so_id}'"

# Find all MC Accounts for this Salesforce Account
mc_query = f"SELECT {', '.join(query_fields)} FROM Mission_Control_Account__c WHERE Account__c = '{account_id}'"

# Validate org ID matches and check for duplicates
```

**💰 STEP 4: Revenue Analysis**

```python
# Extract revenue data safely
monthly_revenue = mc.get('Monthly_Revenue__c', 0) or 0
lifetime_revenue = mc.get('Lifetime_Revenue__c', 0) or 0

# Calculate commitment vs usage ratio
if monthly_revenue > 0:
    ratio = proposed_commitment / monthly_revenue
    # Assess risk based on ratio
```

## Safety Guardrails

1. **NEVER** set `Rev_Ops_Approved__c = true` without explicit approval
2. **ALWAYS** validate customer/org ID match before any updates
3. **ALWAYS** check for overlapping commitments before activation
4. **ALWAYS** verify webhook response after approval/termination
5. **NEVER** update `Contract_End_Date__c` (formula field)
6. **NEVER** update normalized fields on Service Order Details

## PDF Service Order Processing

### 🎯 STEP 1: ALWAYS Find Actual PDF in Salesforce - COMPLETE SEARCH STRATEGY

❌ **WRONG APPROACH**: Looking for sample/test PDFs in workspace
✅ **CORRECT APPROACH**: Systematic search across all Salesforce storage methods

**CRITICAL LESSON**: PDFs may be stored as **legacy Attachments** on Ironclad Workflow records, not modern ContentDocumentLinks!

#### **Search Order (Follow This Sequence):**

```python
# Method 1: ContentDocumentLink (modern files on Opportunity)
file_query = f"""
    SELECT ContentDocumentId, ContentDocument.Title, ContentDocument.LatestPublishedVersionId
    FROM ContentDocumentLink 
    WHERE LinkedEntityId = '{opportunity_id}' AND ContentDocument.FileExtension = 'pdf'
    ORDER BY ContentDocument.CreatedDate DESC
"""

# Method 2: Legacy Attachments (opportunity level)
attachment_query = f"""
    SELECT Id, Name, ContentType, BodyLength
    FROM Attachment WHERE ParentId = '{opportunity_id}' AND Name LIKE '%.pdf'
"""

# Method 3: 🔧 IRONCLAD WORKFLOW SEARCH (CRITICAL!)
# Find Ironclad Workflow record first
ironclad_workflow_query = f"""
    SELECT Id, Name
    FROM ironclad__Ironclad_Workflow__c
    WHERE Name LIKE '%{customer_name}%'
    LIMIT 5
"""

# Then search for LEGACY ATTACHMENTS on Ironclad Workflow
ironclad_attachment_query = f"""
    SELECT Id, Name, ContentType, BodyLength, CreatedDate, CreatedBy.Name
    FROM Attachment
    WHERE ParentId = '{workflow_id}'
    AND (ContentType = 'application/pdf' OR Name LIKE '%.pdf')
    ORDER BY CreatedDate DESC
"""

# Method 4: ContentDocumentLink on Ironclad Workflow (if modern files)
ironclad_files_query = f"""
    SELECT ContentDocumentId, ContentDocument.Title
    FROM ContentDocumentLink 
    WHERE LinkedEntityId = '{workflow_id}' 
    AND ContentDocument.FileExtension = 'pdf'
"""

# Method 5: Service Order direct attachments
so_attachment_query = f"""
    SELECT Id, Name, ContentType, BodyLength
    FROM Attachment WHERE ParentId = '{service_order_id}' AND Name LIKE '%.pdf'
"""
```

#### **🔍 Ironclad Workflow PDF Discovery (PROVEN METHOD)**

Based on successful DashQuill case, PDFs are often stored as **legacy Attachments** on Ironclad Workflow records:

```python
def find_ironclad_contract_pdf(sf, opportunity_id, customer_name):
    """
    Find contract PDF in Ironclad Workflow - PROVEN METHOD
    This approach successfully located DashQuill contract
    """
    
    # Step 1: Find Ironclad Workflow record
    workflow_query = f"""
        SELECT Id, Name
        FROM ironclad__Ironclad_Workflow__c
        WHERE Name LIKE '%{customer_name}%'
        ORDER BY CreatedDate DESC
        LIMIT 5
    """
    
    workflows = sf.query(workflow_query)['records']
    
    for workflow in workflows:
        workflow_id = workflow['Id']
        
        # Step 2: Check for LEGACY ATTACHMENTS (key discovery!)
        attachment_query = f"""
            SELECT Id, Name, ContentType, BodyLength, CreatedDate
            FROM Attachment
            WHERE ParentId = '{workflow_id}'
            AND ContentType = 'application/pdf'
            ORDER BY CreatedDate DESC
        """
        
        attachments = sf.query(attachment_query)['records']
        
        # Step 3: Look for Service Order contract patterns
        for attachment in attachments:
            if any(keyword in attachment['Name'].lower() for keyword in 
                   ['service order', customer_name.lower(), 'contract']):
                return attachment  # Found it!
    
    return None
```

#### **📥 Download from Legacy Attachment**

```python
# Download legacy attachment (different from ContentVersion)
download_url = f"{sf.base_url}sobjects/Attachment/{attachment_id}/Body"
headers = {'Authorization': f'Bearer {sf.session_id}'}
response = requests.get(download_url, headers=headers)
```

### 📥 STEP 2: Download and Parse PDF

```python
# Download from ContentVersion
version_url = f"{sf.base_url}sobjects/ContentVersion/{version_id}/VersionData"
headers = {'Authorization': f'Bearer {sf.session_id}'}
response = requests.get(version_url, headers=headers)
```

### 📋 STEP 3: Extract Contract Details

For processing extracted PDF content, see **references/pdf-parsing-guide.md** for:
- PDF extraction methods (pdftotext, pdfplumber, PyMuPDF)
- Commitment schedule parsing (static vs ramped)
- OCR artifact handling
- Customer information extraction
- JSON output format for integration

### 🔍 STEP 4: SERVICE ORDER vs CONTRACT VALIDATION (CRITICAL!)

**🚨 MANDATORY**: Always validate Service Order configuration matches contract terms exactly.

#### **Essential Validation Checks:**

```python
def validate_service_order_vs_contract(sf, so_id, contract_terms):
    """
    CRITICAL: Validate Service Order configuration matches contract exactly
    Must include commit cycle validation to prevent billing errors
    """
    
    # Get Service Order with ALL commitment fields
    so_describe = sf.Service_Order__c.describe()
    available_fields = [field['name'] for field in so_describe['fields']]
    
    # Build comprehensive query
    base_fields = [
        'Id', 'Name', 'Min_Monthly_Commit__c', 'Contract_Duration__c',
        'Contract_Start_Date__c', 'Contract_End_Date__c', 'Type__c'
    ]
    
    # Add commit cycle fields if available
    commit_cycle_fields = ['Commit_Cycle__c', 'Commit_Cycle_Text__c']
    for field in commit_cycle_fields:
        if field in available_fields:
            base_fields.append(field)
    
    so_query = f"SELECT {', '.join(base_fields)} FROM Service_Order__c WHERE Id = '{so_id}'"
    so = sf.query(so_query)['records'][0]
    
    validation_results = []
    
    # 1. COMMIT CYCLE VALIDATION (CRITICAL!)
    commit_cycle = so.get('Commit_Cycle__c', '').lower()
    so_amount = so.get('Min_Monthly_Commit__c', 0) or 0
    
    if commit_cycle == 'annual':
        # SO stores annual amount in Min_Monthly_Commit__c
        expected_annual = contract_terms.get('annual_commitment', 0)
        if abs(so_amount - expected_annual) >= 1:
            validation_results.append({
                'field': 'Annual Commitment',
                'so_value': f'${so_amount:,.2f}',
                'contract_value': f'${expected_annual:,.2f}',
                'status': 'MISMATCH',
                'severity': 'CRITICAL'
            })
        else:
            validation_results.append({
                'field': 'Annual Commitment',
                'so_value': f'${so_amount:,.2f}',
                'contract_value': f'${expected_annual:,.2f}',
                'status': 'MATCH',
                'severity': 'OK'
            })
    
    elif commit_cycle == 'monthly':
        # SO stores monthly amount in Min_Monthly_Commit__c
        expected_monthly = contract_terms.get('monthly_commitment', 0)
        if abs(so_amount - expected_monthly) >= 1:
            validation_results.append({
                'field': 'Monthly Commitment',
                'so_value': f'${so_amount:,.2f}',
                'contract_value': f'${expected_monthly:,.2f}',
                'status': 'MISMATCH',
                'severity': 'CRITICAL'
            })
        else:
            validation_results.append({
                'field': 'Monthly Commitment',
                'so_value': f'${so_amount:,.2f}',
                'contract_value': f'${expected_monthly:,.2f}',
                'status': 'MATCH',
                'severity': 'OK'
            })
    else:
        validation_results.append({
            'field': 'Commit Cycle',
            'so_value': commit_cycle or 'Not Set',
            'contract_value': 'Unknown',
            'status': 'ERROR',
            'severity': 'CRITICAL'
        })
    
    # 2. Duration Validation
    so_duration = so.get('Contract_Duration__c', 0) or 0
    contract_duration = contract_terms.get('duration_months', 0)
    
    if abs(so_duration - contract_duration) >= 1:
        validation_results.append({
            'field': 'Contract Duration',
            'so_value': f'{so_duration:.0f} months',
            'contract_value': f'{contract_duration} months',
            'status': 'MISMATCH',
            'severity': 'HIGH'
        })
    else:
        validation_results.append({
            'field': 'Contract Duration',
            'so_value': f'{so_duration:.0f} months',
            'contract_value': f'{contract_duration} months',
            'status': 'MATCH',
            'severity': 'OK'
        })
    
    # 3. Start Date Validation
    so_start_date = so.get('Contract_Start_Date__c')
    contract_start_date = contract_terms.get('start_date')
    
    if so_start_date and contract_start_date:
        if so_start_date != contract_start_date:
            validation_results.append({
                'field': 'Start Date',
                'so_value': so_start_date,
                'contract_value': contract_start_date,
                'status': 'MISMATCH',
                'severity': 'HIGH'
            })
        else:
            validation_results.append({
                'field': 'Start Date',
                'so_value': so_start_date,
                'contract_value': contract_start_date,
                'status': 'MATCH',
                'severity': 'OK'
            })
    
    return validation_results
```

#### **🚨 CRITICAL COMMIT CYCLE EXAMPLES:**

| **Contract Term** | **SO Commit_Cycle__c** | **SO Min_Monthly_Commit__c** | **Status** |
|-------------------|------------------------|------------------------------|------------|
| $120,000 annually | Annual | 120000.00 | ✅ **CORRECT** |
| $10,000 monthly | Monthly | 10000.00 | ✅ **CORRECT** |
| $10,000 annually | Monthly | 10000.00 | ❌ **ERROR - 12x billing!** |
| $120,000 monthly | Annual | 120000.00 | ❌ **ERROR - 1/12 billing!** |

#### **📋 Validation Report Format:**

```python
def print_validation_report(validation_results):
    """Print comprehensive validation report."""
    
    print("🔍 SERVICE ORDER vs CONTRACT VALIDATION")
    print("=" * 43)
    
    critical_errors = []
    warnings = []
    
    for result in validation_results:
        status_icon = {
            'MATCH': '✅',
            'MISMATCH': '❌', 
            'ERROR': '🚨'
        }.get(result['status'], '⚠️')
        
        print(f"   {status_icon} {result['field']}:")
        print(f"      Service Order: {result['so_value']}")
        print(f"      Contract: {result['contract_value']}")
        print(f"      Status: {result['status']}")
        
        if result['severity'] == 'CRITICAL':
            critical_errors.append(result)
        elif result['severity'] == 'HIGH':
            warnings.append(result)
    
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"   Critical Errors: {len(critical_errors)}")
    print(f"   Warnings: {len(warnings)}")
    
    if critical_errors:
        print(f"\n🚨 APPROVAL BLOCKED - Critical errors must be resolved:")
        for error in critical_errors:
            print(f"   • {error['field']}: {error['status']}")
        return False
    elif warnings:
        print(f"\n⚠️  Review warnings before approval")
        return True
    else:
        print(f"\n✅ ALL VALIDATIONS PASSED - Ready for approval")
        return True
```

## Common Pitfalls

1. ❌ **Skipping customer/org ID validation** → Risk updating wrong customer
2. ❌ **Only updating main SO start date for ramped commitments** → Webhook sends old dates
3. ❌ **Trying to update normalized fields** → Permission error
4. ❌ **Wrong object name** → Service_Order_Detail__c vs Service_Order_Details__c (PLURAL)
5. ❌ **Not validating in Commitment Manager** → Miss failed webhooks
6. ❌ **Using include_cancelled=false** → Miss audit trail
7. 🆕 **Looking for sample PDFs instead of actual contracts** → Use ContentDocumentLink to find real PDFs
8. 🆕 **Assuming Mission Control Account field names** → Always use describe() to check available fields
9. 🆕 **Hard-coding field queries without validation** → Fields like Mission_Control_Organization_Name__c may not exist
10. 🚨 **ONLY checking ContentDocumentLink for PDFs** → Miss legacy Attachments on Ironclad Workflows (CRITICAL!)
11. 🚨 **NOT validating Commit_Cycle__c in Service Order vs Contract validation** → Risk 12x billing errors (CRITICAL!)

## Domain Knowledge

- **Static SO**: Single `Min_Monthly_Commit__c` → webhook reads main SO fields
- **Ramped SO**: `Service_Order_Details__c` child records → webhook reads detail normalized fields
- **organization_id**: Comes from `Mission_Control_Account__c.Organization_ID__c`
- **MMC_webhook** flow: Record-triggered on SO update with specific criteria
- **Chatter FeedItems**: Show complete webhook request/response history
- **Contract_End_Date__c**: Formula field (Start + Duration), never update directly

## Webhook Data Sources by Type

| Commitment Type | Data Source | Date Field | Amount Field |
|---|---|---|---|
| **Static** | `Service_Order__c` | `Contract_Start_Date__c` | `Min_Monthly_Commit__c` |
| **Ramped** | `Service_Order_Details__c` | `Commit_Start_Date_Normalized__c` | `Commit_Amount__c` |

## Key Queries Reference

```bash
# Service Order Details (ramped commitments)
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Cycle_Number__c, Commit_Amount__c, Commit_Duration__c, Commit_Start_Date__c, Commit_End_Date__c, Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c FROM Service_Order_Details__c WHERE Service_Order__c = 'SO_ID' ORDER BY Cycle_Number__c" --json

# Renewal opportunity lookup
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, StageName, CloseDate FROM Opportunity WHERE AccountId = 'ACCOUNT_ID' AND Name LIKE '%Renewal%'" --json

# Mission Control Account lookup
sf data query -o niamh@telnyx.com --query "SELECT Id, Name, Organization_ID__c FROM Mission_Control_Account__c WHERE Id = 'MC_ACCOUNT_ID'" --json
```

## Resources

### scripts/
- **service_order_operations.py**: Core SO CRUD operations
- **commitment_manager_validator.py**: Webhook validation and audit
- **pdf_parser.py**: Service Order PDF extraction

### references/
- **pdf-parsing-guide.md**: Detailed PDF processing instructions
- **ironclad-pdf-discovery.md**: Proven method for finding contracts in Ironclad Workflows
- **salesforce-field-mapping.md**: Complete field reference and relationships
- **webhook-troubleshooting.md**: Common webhook issues and resolutions