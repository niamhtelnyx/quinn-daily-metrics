# Ironclad Workflow PDF Discovery

## Critical Discovery: Legacy Attachments vs Modern Files

**Problem**: Standard ContentDocumentLink searches fail to find Service Order contract PDFs.

**Solution**: Service Order PDFs are often stored as **legacy Attachments** on Ironclad Workflow records.

## Proven Search Method

Based on successful DashQuill case study (`006Qk00000V92VOIAZ`):

### Step 1: Find Ironclad Workflow Record

```python
def find_ironclad_workflow_for_customer(sf, customer_name, opportunity_id=None):
    """Find Ironclad Workflow records for a customer."""
    
    # Search by customer name in workflow name
    workflow_query = f"""
        SELECT Id, Name, CreatedDate, CreatedBy.Name, LastModifiedDate, LastModifiedBy.Name
        FROM ironclad__Ironclad_Workflow__c
        WHERE Name LIKE '%{customer_name}%'
        ORDER BY CreatedDate DESC
        LIMIT 10
    """
    
    workflows = sf.query(workflow_query)['records']
    
    # If opportunity provided, also try to find workflows created around same time
    if opportunity_id and not workflows:
        # Get opportunity creation date for timeline search
        opp_query = f"""
            SELECT CreatedDate FROM Opportunity WHERE Id = '{opportunity_id}'
        """
        opp_result = sf.query(opp_query)
        if opp_result['records']:
            opp_date = opp_result['records'][0]['CreatedDate'][:10]  # YYYY-MM-DD
            
            # Search for workflows created around the same time
            timeline_query = f"""
                SELECT Id, Name FROM ironclad__Ironclad_Workflow__c
                WHERE CreatedDate >= {opp_date}T00:00:00Z
                AND CreatedDate <= {opp_date}T23:59:59Z
                ORDER BY CreatedDate DESC
                LIMIT 5
            """
            workflows = sf.query(timeline_query)['records']
    
    return workflows
```

### Step 2: Search Legacy Attachments on Workflow

```python
def find_contract_pdf_on_workflow(sf, workflow_id, customer_name):
    """Search for contract PDF as legacy Attachment on Ironclad Workflow."""
    
    # Search for PDF attachments on the workflow record
    attachment_query = f"""
        SELECT Id, Name, ContentType, BodyLength, CreatedDate, CreatedBy.Name,
               LastModifiedDate, Description
        FROM Attachment
        WHERE ParentId = '{workflow_id}'
        AND (ContentType = 'application/pdf' OR Name LIKE '%.pdf')
        ORDER BY CreatedDate DESC
    """
    
    attachments = sf.query(attachment_query)['records']
    
    contract_pdfs = []
    
    for attachment in attachments:
        # Check if this looks like a Service Order contract
        name = attachment['Name'].lower()
        is_contract = any(keyword in name for keyword in [
            'service order', customer_name.lower(), 'contract', 
            'agreement', 'signed', customer_name.lower().replace(' ', '')
        ])
        
        if is_contract:
            contract_pdfs.append({
                'attachment_id': attachment['Id'],
                'name': attachment['Name'],
                'size_bytes': attachment['BodyLength'],
                'created': attachment['CreatedDate'],
                'creator': attachment.get('CreatedBy', {}).get('Name', 'Unknown'),
                'workflow_id': workflow_id
            })
    
    return contract_pdfs
```

### Step 3: Download Legacy Attachment

```python
def download_attachment_pdf(sf, attachment_id, filename=None):
    """Download PDF from legacy Attachment (not ContentVersion)."""
    
    if not filename:
        filename = f"contract_{attachment_id[-8:]}.pdf"
    
    try:
        # Use Attachment Body API (different from ContentVersion)
        download_url = f"{sf.base_url}sobjects/Attachment/{attachment_id}/Body"
        headers = {'Authorization': f'Bearer {sf.session_id}'}
        
        response = requests.get(download_url, headers=headers)
        
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            return filename, True
        else:
            print(f"Download failed: HTTP {response.status_code}")
            return None, False
            
    except Exception as e:
        print(f"Download error: {e}")
        return None, False
```

## Complete Search Workflow

```python
def comprehensive_contract_pdf_search(sf, opportunity_id, customer_name):
    """Complete PDF search across all Salesforce storage methods."""
    
    found_pdfs = []
    
    # Method 1: Modern files on opportunity
    try:
        modern_query = f"""
            SELECT ContentDocumentId, ContentDocument.Title, ContentDocument.LatestPublishedVersionId
            FROM ContentDocumentLink 
            WHERE LinkedEntityId = '{opportunity_id}' 
            AND ContentDocument.FileExtension = 'pdf'
        """
        modern_files = sf.query(modern_query)['records']
        found_pdfs.extend(modern_files)
    except:
        pass
    
    # Method 2: Legacy attachments on opportunity  
    try:
        legacy_query = f"""
            SELECT Id, Name FROM Attachment 
            WHERE ParentId = '{opportunity_id}' AND Name LIKE '%.pdf'
        """
        legacy_files = sf.query(legacy_query)['records']
        found_pdfs.extend(legacy_files)
    except:
        pass
    
    # Method 3: Ironclad Workflow attachments (CRITICAL!)
    workflows = find_ironclad_workflow_for_customer(sf, customer_name, opportunity_id)
    
    for workflow in workflows:
        workflow_pdfs = find_contract_pdf_on_workflow(sf, workflow['Id'], customer_name)
        found_pdfs.extend(workflow_pdfs)
        
        # If we found PDFs on this workflow, return them
        if workflow_pdfs:
            print(f"✅ Found contract PDFs in Ironclad Workflow: {workflow['Name']}")
            return workflow_pdfs
    
    return found_pdfs
```

## Real Example: DashQuill Success Case

**Opportunity**: `006Qk00000V92VOIAZ` (DashQuill: New Customer - 2025-10-29 - abash - $1500)

**Search Results**:
- ❌ ContentDocumentLink on opportunity: 0 PDFs
- ❌ Legacy attachments on opportunity: 0 PDFs  
- ❌ ContentDocumentLink on Ironclad Workflow: 0 PDFs
- ✅ **Legacy attachments on Ironclad Workflow**: **FOUND**

**Successful Location**:
- **Ironclad Workflow**: `a15Qk00000TSfNjIAL` ("Service Order with DashQuill")
- **Attachment ID**: `00PQk00000PJCezMAH`
- **File Name**: "Service Order with DashQuill (699f277ba6) (2).pdf"
- **Size**: 213.7 KB
- **Status**: Signed and validated

## Key Takeaways

1. **Legacy Attachments are still used** for contract storage in Ironclad workflows
2. **ContentDocumentLink searches miss these PDFs** completely
3. **Attachment.Body API** is different from ContentVersion download
4. **Customer name in workflow name** is the primary search key
5. **Multiple attachment types** may exist - look for largest PDF with contract keywords

## Search Priority Order

1. ✅ **Ironclad Workflow legacy attachments** (highest success rate)
2. ContentDocumentLink on opportunity (modern files)
3. Legacy attachments on opportunity 
4. ContentDocumentLink on Service Order records
5. Legacy attachments on Service Order records

This method has a **proven success rate** and should be the primary PDF discovery approach for Service Order management.