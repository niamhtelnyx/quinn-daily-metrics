#!/usr/bin/env python3
"""
Commitment Manager Validator - Validate commitments and audit webhook failures
"""

import requests
import json
from datetime import datetime, timedelta
import logging
from service_order_operations import get_salesforce_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Commitment Manager API credentials
CM_USERNAME = "commitment_webhook"
CM_API_KEY = "@R[7;rb`P*JD5<^UpUns1$aa"
CM_BASE_URL = "https://api.telnyx.com/v2/commitment_manager/webhook"

def get_commitments(organization_id, include_cancelled=True):
    """Get all commitments for an organization from Commitment Manager."""
    
    headers = {
        "username": CM_USERNAME,
        "webhook_api_key": CM_API_KEY
    }
    
    params = {
        "organization_id": organization_id,
        "include_cancelled": str(include_cancelled).lower()
    }
    
    try:
        response = requests.get(
            f"{CM_BASE_URL}/commitments",
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API request failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"Request error: {str(e)}"

def analyze_commitment_status(commitments):
    """Analyze commitment status (active vs inactive)."""
    
    now = datetime.utcnow()
    active_commitments = []
    inactive_commitments = []
    
    for commitment in commitments:
        commitment_id = commitment.get('id')
        period_end_str = commitment.get('period_end')
        cancelled_at = commitment.get('cancelled_at')
        
        # Parse period end date
        try:
            if period_end_str:
                period_end = datetime.fromisoformat(period_end_str.replace('Z', '+00:00'))
            else:
                period_end = None
        except:
            period_end = None
        
        # Determine status
        is_cancelled = cancelled_at is not None
        is_expired = period_end and period_end < now
        
        if not is_cancelled and not is_expired:
            active_commitments.append(commitment)
        else:
            inactive_commitments.append({
                **commitment,
                'inactive_reason': 'cancelled' if is_cancelled else 'expired'
            })
    
    return active_commitments, inactive_commitments

def audit_webhook_failures():
    """Find Service Orders with potential webhook failures."""
    
    print("🔍 AUDITING SERVICE ORDER WEBHOOK FAILURES")
    print("=" * 60)
    
    sf = get_salesforce_client()
    
    # Query Service Orders that might have webhook failures
    query = """
        SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, 
               Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, 
               commitment_handler_id__c, Mission_Control_Account__c,
               Mission_Control_Account__r.Name, Mission_Control_Account__r.Organization_ID__c
        FROM Service_Order__c 
        WHERE Rev_Ops_Approved__c = true 
        AND Stage__c = 'Signed'
        AND commitment_handler_id__c = null
        ORDER BY LastModifiedDate DESC
        LIMIT 20
    """
    
    print("📋 Querying Service Orders with potential webhook failures...")
    print("   Criteria: Rev_Ops_Approved = true, Stage = Signed, commitment_handler_id = null")
    print()
    
    result = sf.query(query)
    records = result['records']
    
    if not records:
        print("✅ No Service Orders found with webhook failure indicators")
        return []
    
    print(f"⚠️  Found {len(records)} Service Orders with potential webhook failures:")
    print()
    
    webhook_failures = []
    
    for i, record in enumerate(records, 1):
        so_id = record['Id']
        so_name = record['Name']
        account_name = record.get('Mission_Control_Account__r', {}).get('Name', 'Unknown')
        org_id = record.get('Mission_Control_Account__r', {}).get('Organization_ID__c')
        start_date = record.get('Contract_Start_Date__c', '')[:10] if record.get('Contract_Start_Date__c') else 'Not set'
        commit_amount = record.get('Min_Monthly_Commit__c', 0)
        
        print(f"{i:2d}. {so_name}")
        print(f"    Account: {account_name}")
        print(f"    Org ID: {org_id}")
        print(f"    Start Date: {start_date}")
        print(f"    Commit: ${commit_amount:,.2f}" if commit_amount else "    Commit: $0.00")
        
        # Check webhook history
        webhook_status = check_so_webhook_status(sf, so_id)
        print(f"    Webhook: {webhook_status['message']}")
        
        webhook_failures.append({
            'so_id': so_id,
            'so_name': so_name,
            'account_name': account_name,
            'org_id': org_id,
            'start_date': start_date,
            'commit_amount': commit_amount,
            'webhook_status': webhook_status
        })
        
        print()
    
    return webhook_failures

def check_so_webhook_status(sf, so_id):
    """Check webhook status for a specific Service Order."""
    
    try:
        feed_query = f"""
            SELECT Id, Body, CreatedDate, Type 
            FROM FeedItem 
            WHERE ParentId = '{so_id}' 
            AND (Body LIKE '%webhook%' OR Body LIKE '%201%' OR Body LIKE '%204%' OR Body LIKE '%4%' OR Body LIKE '%5%')
            ORDER BY CreatedDate DESC 
            LIMIT 5
        """
        
        feed_result = sf.query(feed_query)
        feed_records = feed_result['records']
        
        if not feed_records:
            return {
                'status': 'no_activity',
                'message': 'No webhook activity found',
                'has_failure': True
            }
        
        # Analyze webhook responses
        for feed in feed_records:
            body = feed.get('Body', '')
            created_date = feed.get('CreatedDate', '')[:19] if feed.get('CreatedDate') else ''
            
            # Success indicators
            if '201' in body or '204' in body:
                code = '201' if '201' in body else '204'
                return {
                    'status': 'success',
                    'message': f'SUCCESS ({code}) - {created_date}',
                    'has_failure': False,
                    'response_code': code
                }
            
            # Error indicators
            error_codes = ['400', '401', '403', '404', '500', '502', '503']
            for error_code in error_codes:
                if error_code in body:
                    return {
                        'status': 'failed',
                        'message': f'FAILED ({error_code}) - {created_date}',
                        'has_failure': True,
                        'response_code': error_code
                    }
        
        return {
            'status': 'unclear',
            'message': f'Activity found but unclear - {feed_records[0].get("CreatedDate", "")[:19]}',
            'has_failure': True
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Query error: {str(e)}',
            'has_failure': True
        }

def validate_commitment_in_cm(organization_id):
    """Validate commitments in Commitment Manager for an organization."""
    
    print(f"🔍 Validating commitments for org: {organization_id}")
    print("=" * 50)
    
    # Get commitments from CM API
    success, result = get_commitments(organization_id, include_cancelled=True)
    
    if not success:
        print(f"❌ Failed to fetch commitments: {result}")
        return None
    
    commitments = result.get('data', []) if isinstance(result, dict) else result
    
    if not commitments:
        print("📭 No commitments found for this organization")
        return {
            'active_commitments': 0,
            'inactive_commitments': 0,
            'total_commitments': 0
        }
    
    # Analyze commitment status
    active, inactive = analyze_commitment_status(commitments)
    
    print(f"📊 COMMITMENT SUMMARY:")
    print(f"   Total: {len(commitments)}")
    print(f"   Active: {len(active)}")
    print(f"   Inactive: {len(inactive)}")
    print()
    
    # Show active commitments
    if active:
        print("✅ ACTIVE COMMITMENTS:")
        for i, commitment in enumerate(active, 1):
            period_end = commitment.get('period_end', 'Unknown')[:10]
            amount = commitment.get('monthly_commitment_amount', 0)
            commitment_id = commitment.get('id', 'Unknown')
            
            print(f"   {i}. ID: {commitment_id}")
            print(f"      Amount: ${amount:,.2f}/month")
            print(f"      Expires: {period_end}")
        print()
    
    # Show inactive commitments
    if inactive:
        print("❌ INACTIVE COMMITMENTS:")
        for i, commitment in enumerate(inactive, 1):
            reason = commitment.get('inactive_reason', 'unknown')
            period_end = commitment.get('period_end', 'Unknown')[:10]
            cancelled_at = commitment.get('cancelled_at')
            if cancelled_at:
                cancelled_date = cancelled_at[:10]
            else:
                cancelled_date = 'N/A'
            commitment_id = commitment.get('id', 'Unknown')
            
            print(f"   {i}. ID: {commitment_id}")
            print(f"      Reason: {reason}")
            print(f"      Period End: {period_end}")
            if reason == 'cancelled':
                print(f"      Cancelled: {cancelled_date}")
        print()
    
    return {
        'active_commitments': len(active),
        'inactive_commitments': len(inactive),
        'total_commitments': len(commitments),
        'active_details': active,
        'inactive_details': inactive
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python commitment_manager_validator.py <command> [args...]")
        print("Commands:")
        print("  audit                     - Audit webhook failures")
        print("  validate <organization_id> - Validate commitments for org")
        print("  commitments <org_id>      - Get all commitments for org")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "audit":
        failures = audit_webhook_failures()
        
        # Summary
        failed_webhooks = [so for so in failures if so['webhook_status']['has_failure']]
        successful_webhooks = [so for so in failures if not so['webhook_status']['has_failure']]
        
        print("📊 WEBHOOK AUDIT SUMMARY")
        print("=" * 30)
        print(f"❌ Webhook Failures: {len(failed_webhooks)}")
        print(f"✅ Webhooks OK: {len(successful_webhooks)}")
        print(f"📝 Total Checked: {len(failures)}")
        
        if failed_webhooks:
            print("\\n🚨 SERVICE ORDERS NEEDING ATTENTION:")
            for so in failed_webhooks:
                print(f"• {so['so_name']} ({so['account_name']})")
        
    elif command == "validate" and len(sys.argv) >= 3:
        org_id = sys.argv[2]
        result = validate_commitment_in_cm(org_id)
        if result:
            print(f"Validation complete for org: {org_id}")
        
    elif command == "commitments" and len(sys.argv) >= 3:
        org_id = sys.argv[2]
        success, result = get_commitments(org_id)
        if success:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result}")
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)