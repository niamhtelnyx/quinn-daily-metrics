"""
Commitment Database Query Skill

Query the Telnyx Commitment Manager API to retrieve commitment data
for verification and validation against service orders.

Updated to automatically resolve Salesforce Mission Control Account IDs
to proper UUID organization IDs.
"""

import json
import requests
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

def resolve_salesforce_org_id_sync(sf_account_id: str) -> Dict[str, Any]:
    """
    Resolve Salesforce Mission Control Account ID to UUID organization ID (synchronous)
    
    Args:
        sf_account_id: Salesforce Mission Control Account ID (e.g., a0TQk00000TcP5CMAV)
        
    Returns:
        Dict with resolution result and UUID organization_id
    """
    try:
        import subprocess
        
        # Query Mission Control Account for Organization_ID__c directly via sf CLI
        cmd = [
            'sf', 'data', 'query',
            '-o', 'niamh@telnyx.com',
            '--query', f"SELECT Id, Name, Organization_ID__c FROM Mission_Control_Account__c WHERE Id = '{sf_account_id}'",
            '--json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return {
                "resolution_successful": False,
                "error": f"sf CLI error: {result.stderr}",
                "salesforce_account_id": sf_account_id
            }
        
        sf_result = json.loads(result.stdout)
        mc_accounts = sf_result.get("result", {}).get("records", [])
        
        if not mc_accounts:
            return {
                "resolution_successful": False,
                "error": f"Mission Control Account {sf_account_id} not found in Salesforce",
                "salesforce_account_id": sf_account_id
            }
        
        mc_account = mc_accounts[0]
        uuid_org_id = mc_account.get("Organization_ID__c")
        
        if not uuid_org_id:
            return {
                "resolution_successful": False,
                "error": f"Organization_ID__c field is empty for Mission Control Account {sf_account_id}",
                "salesforce_account_id": sf_account_id,
                "mission_control_account": mc_account
            }
        
        return {
            "resolution_successful": True,
            "salesforce_account_id": sf_account_id,
            "uuid_organization_id": uuid_org_id,
            "mission_control_account": mc_account,
            "resolved_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "resolution_successful": False,
            "error": f"Error resolving Salesforce org ID: {str(e)}",
            "salesforce_account_id": sf_account_id
        }

def query_commitment_database(organization_id: str, include_cancelled: bool = True) -> Dict[str, Any]:
    """
    Query the commitment database for a given organization
    
    Args:
        organization_id: UUID organization ID (e.g., b156dd5f-9fd9-4829-a4e6-e8294cbc2ca8)
        include_cancelled: Include cancelled commitments in results
    
    Returns:
        Dict with commitment data and query status
    """
    
    # API Configuration
    api_base = "https://api.telnyx.com/v2/commitment_manager/webhook"
    username = os.getenv("COMMITMENT_MANAGER_USERNAME", "commitment_webhook")
    api_key = os.getenv("COMMITMENT_MANAGER_API_KEY", "@R[7;rb`P*JD5<^UpUns1$aa")
    
    # Headers
    headers = {
        "username": username,
        "webhook_api_key": api_key,
        "Content-Type": "application/json"
    }
    
    # Query parameters
    params = {
        "organization_id": organization_id,
        "include_cancelled": str(include_cancelled).lower()
    }
    
    try:
        # Query commitments
        url = f"{api_base}/commitments"
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            commitments = data.get("data", [])
            
            # Process and categorize commitments
            active_commitments = []
            cancelled_commitments = []
            
            for commitment in commitments:
                if commitment.get("status") == "active":
                    active_commitments.append(commitment)
                else:
                    cancelled_commitments.append(commitment)
            
            return {
                "success": True,
                "organization_id": organization_id,
                "total_commitments": len(commitments),
                "active_count": len(active_commitments),
                "cancelled_count": len(cancelled_commitments),
                "active_commitments": active_commitments,
                "cancelled_commitments": cancelled_commitments if include_cancelled else [],
                "query_timestamp": datetime.utcnow().isoformat() + "Z",
                "api_response_status": response.status_code
            }
            
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Organization not found",
                "organization_id": organization_id,
                "message": f"No commitments found for organization {organization_id}",
                "query_timestamp": datetime.utcnow().isoformat() + "Z",
                "api_response_status": response.status_code
            }
            
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Authentication failed",
                "message": "Invalid commitment manager credentials",
                "query_timestamp": datetime.utcnow().isoformat() + "Z",
                "api_response_status": response.status_code
            }
            
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}",
                "message": response.text,
                "organization_id": organization_id,
                "query_timestamp": datetime.utcnow().isoformat() + "Z",
                "api_response_status": response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "Network error",
            "message": str(e),
            "organization_id": organization_id,
            "query_timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "Query error", 
            "message": str(e),
            "organization_id": organization_id,
            "query_timestamp": datetime.utcnow().isoformat() + "Z"
        }

def format_commitment_summary(commitment_data: Dict[str, Any]) -> str:
    """Format commitment data for human-readable summary"""
    
    if not commitment_data.get("success"):
        return f"❌ Query failed: {commitment_data.get('message', 'Unknown error')}"
    
    org_id = commitment_data["organization_id"]
    active_count = commitment_data["active_count"]
    cancelled_count = commitment_data["cancelled_count"]
    
    summary = [f"🏢 Organization: {org_id}"]
    summary.append(f"📊 Total Commitments: {commitment_data['total_commitments']} (Active: {active_count}, Cancelled: {cancelled_count})")
    
    # Active commitments detail
    if active_count > 0:
        summary.append(f"\n✅ ACTIVE COMMITMENTS ({active_count}):")
        for i, commitment in enumerate(commitment_data["active_commitments"], 1):
            amount = commitment.get("amount", 0)
            amount_dollars = amount / 100 if isinstance(amount, (int, float)) and amount > 0 else 0  # Convert cents to dollars
            start_date = commitment.get("start_date", "Unknown")[:10] if commitment.get("start_date") else "Unknown"
            end_date = commitment.get("end_date", "Unknown")[:10] if commitment.get("end_date") else "Unknown"
            commitment_id = commitment.get("commitment_id", "Unknown")
            
            summary.append(f"  {i}. ${amount_dollars:,.0f}/month | {start_date} → {end_date}")
            summary.append(f"     ID: {commitment_id} | Status: {commitment.get('status', 'Unknown')}")
    
    # Cancelled commitments summary
    if cancelled_count > 0:
        summary.append(f"\n🗑️ CANCELLED COMMITMENTS ({cancelled_count}):")
        for i, commitment in enumerate(commitment_data["cancelled_commitments"], 1):
            amount = commitment.get("amount", 0)
            amount_dollars = amount / 100 if isinstance(amount, (int, float)) and amount > 0 else 0
            cancelled_date = commitment.get("cancelled_at", "Unknown")[:10] if commitment.get("cancelled_at") else "Unknown"
            commitment_id = commitment.get("commitment_id", "Unknown")
            
            summary.append(f"  {i}. ${amount_dollars:,.0f}/month | Cancelled: {cancelled_date}")
            summary.append(f"     ID: {commitment_id}")
    
    return "\n".join(summary)

# A2A skill interface
def handle_commitment_database_query_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """A2A interface for commitment-database-query skill"""
    
    try:
        organization_id = payload.get('organization_id') or payload.get('mcorgid')
        include_cancelled = payload.get('include_cancelled', True)
        format_type = payload.get('format', 'structured')  # structured or summary
        
        if not organization_id:
            return {
                'success': False,
                'error': 'organization_id (or mcorgid) is required'
            }
        
        # Auto-resolve Salesforce Mission Control Account ID to UUID if needed
        resolved_org_id = organization_id
        resolution_info = None
        
        # Check if this looks like a Salesforce ID (starts with 'a0T')
        if organization_id.startswith('a0T') and len(organization_id) == 18:
            # This is a Salesforce Mission Control Account ID, resolve it
            resolution_result = resolve_salesforce_org_id_sync(organization_id)
            
            if resolution_result["resolution_successful"]:
                resolved_org_id = resolution_result["uuid_organization_id"]
                resolution_info = {
                    "auto_resolved": True,
                    "original_salesforce_id": organization_id,
                    "resolved_uuid_org_id": resolved_org_id,
                    "mission_control_account": resolution_result["mission_control_account"]
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to resolve Salesforce org ID: {resolution_result["error"]}',
                    'original_organization_id': organization_id,
                    'resolution_attempted': True,
                    'resolution_details': resolution_result
                }
        
        # Query the commitment database with the resolved UUID
        result = query_commitment_database(resolved_org_id, include_cancelled)
        
        # Add resolution info if we auto-resolved
        if resolution_info:
            result['org_id_resolution'] = resolution_info
        
        # Format response based on requested format
        if format_type == 'summary':
            result['formatted_summary'] = format_commitment_summary(result)
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Skill execution error: {str(e)}'
        }

# Example usage
if __name__ == '__main__':
    # Test query
    result = query_commitment_database('a0TQk00000TcP5CMAV', True)
    print(json.dumps(result, indent=2, default=str))
    print("\n" + "="*50)
    print(format_commitment_summary(result))