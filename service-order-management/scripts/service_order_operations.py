#!/usr/bin/env python3
"""
Service Order Operations - Core CRUD operations for Salesforce Service Orders
"""

import os
import requests
from datetime import datetime, timedelta
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_service_order_pdf(sf, opportunity_id):
    """Find Service Order PDF in Salesforce attachments - LESSON LEARNED: Always check SF first!"""
    
    logger.info(f"Searching for Service Order PDF for opportunity: {opportunity_id}")
    
    # Method 1: ContentDocumentLink (modern Salesforce files)
    try:
        file_query = f"""
            SELECT ContentDocumentId, ContentDocument.Title, ContentDocument.FileExtension,
                   ContentDocument.ContentSize, ContentDocument.LatestPublishedVersionId,
                   ContentDocument.CreatedDate
            FROM ContentDocumentLink 
            WHERE LinkedEntityId = '{opportunity_id}'
            AND ContentDocument.FileExtension = 'pdf'
            ORDER BY ContentDocument.CreatedDate DESC
        """
        
        file_result = sf.query(file_query)
        if file_result['records']:
            logger.info(f"Found {len(file_result['records'])} PDF file(s) via ContentDocumentLink")
            for file_rec in file_result['records']:
                doc = file_rec['ContentDocument']
                if 'service' in doc['Title'].lower() or 'contract' in doc['Title'].lower():
                    return {
                        'method': 'ContentDocumentLink',
                        'document_id': doc['LatestPublishedVersionId'],
                        'title': doc['Title'],
                        'size': doc['ContentSize'],
                        'download_url': f"sobjects/ContentVersion/{doc['LatestPublishedVersionId']}/VersionData"
                    }
            
            # Return first PDF if no obvious Service Order found
            doc = file_result['records'][0]['ContentDocument']
            return {
                'method': 'ContentDocumentLink',
                'document_id': doc['LatestPublishedVersionId'],
                'title': doc['Title'],
                'size': doc['ContentSize'],
                'download_url': f"sobjects/ContentVersion/{doc['LatestPublishedVersionId']}/VersionData"
            }
            
    except Exception as e:
        logger.warning(f"ContentDocumentLink query failed: {e}")
    
    # Method 2: Legacy Attachments (fallback)
    try:
        attachment_query = f"""
            SELECT Id, Name, ContentType, BodyLength, ParentId
            FROM Attachment
            WHERE ParentId = '{opportunity_id}'
            AND (Name LIKE '%.pdf' OR ContentType LIKE '%pdf%')
            ORDER BY CreatedDate DESC
        """
        
        attachment_result = sf.query(attachment_query)
        if attachment_result['records']:
            logger.info(f"Found {len(attachment_result['records'])} PDF attachment(s) via Attachment")
            att = attachment_result['records'][0]
            return {
                'method': 'Attachment',
                'document_id': att['Id'],
                'title': att['Name'],
                'size': att['BodyLength'],
                'download_url': f"sobjects/Attachment/{att['Id']}/Body"
            }
            
    except Exception as e:
        logger.warning(f"Attachment query failed: {e}")
    
    logger.warning("No PDF documents found in Salesforce attachments")
    return None

def download_pdf_from_salesforce(sf, pdf_info, output_filename=None):
    """Download PDF from Salesforce using the PDF info returned by find_service_order_pdf."""
    
    if not pdf_info:
        return None, "No PDF info provided"
    
    try:
        # Build download URL
        full_url = f"{sf.base_url}{pdf_info['download_url']}"
        headers = {'Authorization': f'Bearer {sf.session_id}'}
        
        logger.info(f"Downloading PDF: {pdf_info['title']} ({pdf_info['size']:,} bytes)")
        
        response = requests.get(full_url, headers=headers)
        if response.status_code == 200:
            filename = output_filename or f"{pdf_info['title'].replace(' ', '_')}.pdf"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Successfully downloaded: {filename}")
            return filename, None
        else:
            error_msg = f"Download failed: HTTP {response.status_code}"
            logger.error(error_msg)
            return None, error_msg
            
    except Exception as e:
        error_msg = f"Download error: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

def get_salesforce_client():
    """Authenticate to Salesforce using OAuth2 Client Credentials flow."""
    try:
        from simple_salesforce import Salesforce
        import requests
    except ImportError:
        raise ImportError("Install simple-salesforce and requests: pip install simple-salesforce requests")
    
    # Environment variables for OAuth2 Client Credentials
    client_id = os.environ.get('SF_CLIENT_ID')
    client_secret = os.environ.get('SF_CLIENT_SECRET') 
    domain = os.environ.get('SF_DOMAIN', 'telnyx')
    
    if not client_id or not client_secret:
        raise ValueError("Salesforce OAuth2 credentials required: SF_CLIENT_ID, SF_CLIENT_SECRET")
    
    # OAuth2 token endpoint  
    if domain == "login":
        token_url = f"https://login.salesforce.com/services/oauth2/token"
    else:
        # Custom domain (like telnyx)
        token_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
    
    logger.info(f"Authenticating to Salesforce via OAuth2 Client Credentials ({domain})")
    
    # Request access token using client credentials grant
    response = requests.post(token_url, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    })
    
    if response.status_code != 200:
        raise ValueError(f"Salesforce OAuth2 failed: {response.status_code} - {response.text}")
    
    token_data = response.json()
    access_token = token_data['access_token']
    instance_url = token_data['instance_url']
    
    logger.info(f"Connected to Salesforce: {instance_url}")
    
    return Salesforce(
        instance_url=instance_url,
        session_id=access_token
    )

def lookup_service_orders(customer_name):
    """Lookup Service Orders by customer name."""
    sf = get_salesforce_client()
    
    query = f"""
        SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, 
               Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, 
               commitment_handler_id__c, Opportunity__c, Mission_Control_Account__c,
               Mission_Control_Account__r.Name, Mission_Control_Account__r.Organization_ID__c
        FROM Service_Order__c 
        WHERE Name LIKE '%{customer_name}%'
        ORDER BY LastModifiedDate DESC
    """
    
    result = sf.query(query)
    return result['records']

def validate_customer_org_id(customer_name, provided_org_id):
    """Validate that customer name matches provided org ID with robust field checking."""
    sf = get_salesforce_client()
    
    # Step 1: Get Mission Control Account from Service Order
    so_query = f"""
        SELECT Mission_Control_Account__c 
        FROM Service_Order__c 
        WHERE Name LIKE '%{customer_name}%' 
        LIMIT 1
    """
    
    so_result = sf.query(so_query)
    if not so_result['records']:
        return False, f"No Service Orders found for customer: {customer_name}"
    
    mc_account_id = so_result['records'][0]['Mission_Control_Account__c']
    if not mc_account_id:
        return False, f"No Mission Control Account linked to Service Orders for: {customer_name}"
    
    # Step 2: Discover available fields on Mission Control Account
    try:
        mc_describe = sf.Mission_Control_Account__c.describe()
        available_fields = [field['name'] for field in mc_describe['fields']]
        logger.info(f"Available MC Account fields: {len(available_fields)}")
    except Exception as e:
        logger.warning(f"Could not describe MC Account object: {e}")
        available_fields = ['Id', 'Name', 'Organization_ID__c']  # Fallback to minimum fields
    
    # Step 3: Build query with available fields
    query_fields = ['Organization_ID__c', 'Name']  # Essential fields
    optional_fields = ['Account__c', 'Status__c']  # Optional but useful
    
    for field in optional_fields:
        if field in available_fields:
            query_fields.append(field)
    
    mc_query = f"""
        SELECT {', '.join(query_fields)}
        FROM Mission_Control_Account__c 
        WHERE Id = '{mc_account_id}'
    """
    
    try:
        mc_result = sf.query(mc_query)
        if not mc_result['records']:
            return False, f"Mission Control Account not found: {mc_account_id}"
        
        mc_record = mc_result['records'][0]
        actual_org_id = mc_record.get('Organization_ID__c')
        account_name = mc_record.get('Name', 'Unknown')
        
        # Step 4: Compare
        if actual_org_id == provided_org_id:
            return True, f"✅ MATCH: {customer_name} ({account_name}) = {actual_org_id}"
        else:
            return False, f"""🚨 ORG ID MISMATCH:
            - Provided: {provided_org_id}
            - Actual: {actual_org_id}
            - Customer: {customer_name} ({account_name})
            
            VERIFY CORRECT ORG ID BEFORE PROCEEDING"""
            
    except Exception as e:
        return False, f"Error querying Mission Control Account: {str(e)}"

def check_commitment_type(so_id):
    """Determine if Service Order is static or ramped commitment."""
    sf = get_salesforce_client()
    
    # Check for Service Order Details records
    query = f"""
        SELECT Id, Name, Cycle_Number__c, Commit_Amount__c, 
               Commit_Duration__c, Commit_Start_Date__c, Commit_End_Date__c,
               Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c
        FROM Service_Order_Details__c 
        WHERE Service_Order__c = '{so_id}' 
        ORDER BY Cycle_Number__c
    """
    
    result = sf.query(query)
    details = result['records']
    
    if details:
        return 'ramped', details
    else:
        return 'static', []

def terminate_service_order(so_id):
    """Terminate a Service Order."""
    sf = get_salesforce_client()
    
    logger.info(f"Terminating Service Order: {so_id}")
    
    try:
        result = sf.Service_Order__c.update(so_id, {'Stage__c': 'Terminated'})
        logger.info(f"Successfully terminated SO: {so_id}")
        return True, "Service Order terminated successfully"
    except Exception as e:
        logger.error(f"Failed to terminate SO {so_id}: {e}")
        return False, str(e)

def approve_service_order(so_id, require_confirmation=True):
    """Approve Service Order (triggers webhook). Requires explicit confirmation."""
    if require_confirmation:
        confirmation = input(f"⚠️  APPROVE Service Order {so_id}? This triggers webhook to Commitment Manager. (y/N): ")
        if confirmation.lower() not in ['y', 'yes']:
            return False, "Approval cancelled by user"
    
    sf = get_salesforce_client()
    
    logger.info(f"Approving Service Order: {so_id}")
    
    try:
        result = sf.Service_Order__c.update(so_id, {'Rev_Ops_Approved__c': True})
        logger.info(f"Successfully approved SO: {so_id}")
        return True, "Service Order approved successfully"
    except Exception as e:
        logger.error(f"Failed to approve SO {so_id}: {e}")
        return False, str(e)

def update_start_date(so_id, new_start_date, commitment_type='static', details=None):
    """Update Service Order start date. Handles both static and ramped commitments."""
    sf = get_salesforce_client()
    
    logger.info(f"Updating start date for SO {so_id} to {new_start_date}")
    
    try:
        # Update main Service Order
        so_update = {
            'Contract_Start_Date__c': new_start_date,
            'Stage__c': 'Signed',
            'Rev_Ops_Approved__c': False
        }
        
        result = sf.Service_Order__c.update(so_id, so_update)
        logger.info(f"Updated main SO start date")
        
        # For ramped commitments, update each detail record
        if commitment_type == 'ramped' and details:
            logger.info(f"Updating {len(details)} Service Order Detail records")
            
            # Calculate date offsets for each detail record
            base_date = datetime.strptime(new_start_date, '%Y-%m-%d')
            
            for i, detail in enumerate(details):
                # Preserve original offset from contract start
                detail_id = detail['Id']
                
                # For now, assume monthly cycles starting from base date
                detail_start_date = base_date.replace(day=1) + timedelta(days=30 * i)
                detail_start_str = detail_start_date.strftime('%Y-%m-%d')
                
                detail_update = {
                    'Commit_Start_Date__c': detail_start_str
                }
                
                sf.Service_Order_Details__c.update(detail_id, detail_update)
                logger.info(f"Updated detail record {detail_id}: {detail_start_str}")
        
        return True, f"Start date updated successfully (type: {commitment_type})"
        
    except Exception as e:
        logger.error(f"Failed to update start date for SO {so_id}: {e}")
        return False, str(e)

def check_webhook_status(so_id):
    """Check webhook status via Chatter FeedItems."""
    sf = get_salesforce_client()
    
    try:
        query = f"""
            SELECT Id, Body, CreatedDate, Type 
            FROM FeedItem 
            WHERE ParentId = '{so_id}' 
            AND (Body LIKE '%webhook%' OR Body LIKE '%201%' OR Body LIKE '%204%' OR Body LIKE '%4%' OR Body LIKE '%5%')
            ORDER BY CreatedDate DESC 
            LIMIT 10
        """
        
        result = sf.query(query)
        records = result['records']
        
        if not records:
            return {
                'status': 'no_activity',
                'message': 'No webhook activity found',
                'last_activity': None
            }
        
        # Check latest records for success/failure indicators
        for record in records:
            body = record.get('Body', '')
            created_date = record.get('CreatedDate', '')[:19]
            
            # Success indicators
            if '201' in body or '204' in body:
                code = '201' if '201' in body else '204'
                return {
                    'status': 'success',
                    'message': f'Webhook successful (HTTP {code})',
                    'last_activity': created_date,
                    'response_code': code
                }
            
            # Error indicators
            error_codes = ['400', '401', '403', '404', '500', '502', '503']
            for error_code in error_codes:
                if error_code in body:
                    return {
                        'status': 'failed',
                        'message': f'Webhook failed (HTTP {error_code})',
                        'last_activity': created_date,
                        'response_code': error_code
                    }
        
        # Activity found but unclear
        return {
            'status': 'unclear',
            'message': 'Webhook activity found but status unclear',
            'last_activity': records[0].get('CreatedDate', '')[:19]
        }
        
    except Exception as e:
        logger.error(f"Error checking webhook status for SO {so_id}: {e}")
        return {
            'status': 'error',
            'message': f'Failed to check webhook status: {str(e)}',
            'last_activity': None
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python service_order_operations.py <command> [args...]")
        print("Commands:")
        print("  lookup <customer_name>")
        print("  validate <customer_name> <org_id>") 
        print("  check_type <so_id>")
        print("  webhook_status <so_id>")
        print("  terminate <so_id>")
        print("  update_date <so_id> <new_date>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "lookup" and len(sys.argv) >= 3:
        customer = sys.argv[2]
        orders = lookup_service_orders(customer)
        print(json.dumps(orders, indent=2))
        
    elif command == "validate" and len(sys.argv) >= 4:
        customer = sys.argv[2]
        org_id = sys.argv[3]
        valid, message = validate_customer_org_id(customer, org_id)
        print(message)
        
    elif command == "check_type" and len(sys.argv) >= 3:
        so_id = sys.argv[2]
        commitment_type, details = check_commitment_type(so_id)
        print(f"Commitment type: {commitment_type}")
        if details:
            print(f"Detail records: {len(details)}")
            
    elif command == "webhook_status" and len(sys.argv) >= 3:
        so_id = sys.argv[2]
        status = check_webhook_status(so_id)
        print(json.dumps(status, indent=2))
        
    elif command == "terminate" and len(sys.argv) >= 3:
        so_id = sys.argv[2]
        success, message = terminate_service_order(so_id)
        print(message)
        
    elif command == "update_date" and len(sys.argv) >= 4:
        so_id = sys.argv[2]
        new_date = sys.argv[3]
        # Check type first
        commitment_type, details = check_commitment_type(so_id)
        success, message = update_start_date(so_id, new_date, commitment_type, details)
        print(message)
        
    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)