"""
Resolve Mission Control Account Skill

This skill finds and validates the correct Mission Control Account for a Service Order
using revenue analysis, prior Service Order history, and confidence scoring.
"""

import json
import subprocess
from typing import Dict, List, Any, Optional

def resolve_mission_control_account(account_id: str, service_order_id: str = None) -> Dict[str, Any]:
    """
    Resolve Mission Control Account for an Account with confidence scoring
    
    Args:
        account_id: Salesforce Account ID
        service_order_id: Optional current Service Order ID
        
    Returns:
        Dict with resolution results and confidence assessment
    """
    
    # Step 1: Get all Mission Control Accounts for this Account
    mc_accounts = get_mission_control_accounts(account_id)
    
    if not mc_accounts:
        return {
            'success': False,
            'scenario': 'no_mc_accounts',
            'message': 'No Mission Control Accounts found for this Account. User must provide org ID.',
            'action_required': 'request_org_id',
            'account_id': account_id
        }
    
    if len(mc_accounts) == 1:
        # Single MC Account - validate and build confidence
        mc_account = mc_accounts[0]
        confidence = assess_single_mc_account_confidence(mc_account, account_id)
        
        return {
            'success': True,
            'scenario': 'single_mc_account',
            'recommended_mc_account': mc_account,
            'confidence_score': confidence['score'],
            'confidence_factors': confidence['factors'],
            'message': f"I believe this is the right org ID based on {confidence['summary']}",
            'action_required': 'user_validation'
        }
    
    else:
        # Multiple MC Accounts - rank by confidence
        ranked_accounts = rank_mc_accounts_by_confidence(mc_accounts, account_id)
        
        if ranked_accounts[0]['confidence_score'] >= 0.8:
            # High confidence in top choice
            return {
                'success': True,
                'scenario': 'multiple_high_confidence',
                'recommended_mc_account': ranked_accounts[0],
                'alternatives': ranked_accounts[1:3],  # Show top alternatives
                'message': f"I believe this is the right org ID based on {ranked_accounts[0]['confidence_summary']}",
                'action_required': 'user_validation'
            }
        else:
            # Lower confidence - present options
            return {
                'success': True,
                'scenario': 'multiple_low_confidence', 
                'candidates': ranked_accounts[:3],  # Top 3 candidates
                'message': f"I believe it should be 1 of these {len(ranked_accounts[:3])} org IDs - here's what each one has going for it making it a contender",
                'action_required': 'user_selection'
            }

def get_mission_control_accounts(account_id: str) -> List[Dict[str, Any]]:
    """Get all Mission Control Accounts for an Account"""
    
    query = f"""
    SELECT Id, Name, Organization_ID__c, Account__c, Lifetime_Revenue__c, Monthly_Revenue__c, CreatedDate
    FROM Mission_Control_Account__c 
    WHERE Account__c = '{account_id}'
    ORDER BY Lifetime_Revenue__c DESC NULLS LAST, CreatedDate DESC
    """
    
    try:
        result = subprocess.run([
            'sf', 'data', 'query',
            '-o', 'niamh@telnyx.com',
            '--query', query,
            '--json'
        ], capture_output=True, text=True, check=True)
        
        response = json.loads(result.stdout)
        return response.get('result', {}).get('records', [])
        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        return []

def assess_single_mc_account_confidence(mc_account: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """Assess confidence for a single Mission Control Account"""
    
    confidence_score = 0.5  # Base confidence
    factors = []
    
    # Factor 1: Revenue
    revenue = mc_account.get('Lifetime_Revenue__c', 0) or 0
    if revenue > 0:
        confidence_score += 0.3
        factors.append(f"${revenue:,.0f} in revenue")
    else:
        factors.append("no revenue recorded")
    
    # Factor 2: Prior Service Orders
    prior_sos = get_prior_service_orders_with_mc_account(account_id, mc_account['Id'])
    if prior_sos:
        confidence_score += 0.2
        factors.append(f"{len(prior_sos)} prior Service Orders used this MC Account")
    else:
        factors.append("no prior Service Order history")
    
    # Factor 3: Status
    status = mc_account.get('Status__c', '')
    if status in ['Active', 'Approved']:
        confidence_score += 0.1
        factors.append(f"status is {status}")
    
    # Create summary
    summary = ', '.join(factors[:2])  # Most important factors
    
    return {
        'score': min(confidence_score, 1.0),
        'factors': factors,
        'summary': summary,
        'revenue': revenue,
        'prior_service_orders': len(prior_sos) if prior_sos else 0
    }

def rank_mc_accounts_by_confidence(mc_accounts: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
    """Rank multiple Mission Control Accounts by confidence"""
    
    ranked = []
    
    for mc_account in mc_accounts:
        confidence = assess_single_mc_account_confidence(mc_account, account_id)
        
        # Add MC account data to confidence assessment
        ranked_account = {
            **mc_account,
            'confidence_score': confidence['score'],
            'confidence_factors': confidence['factors'],
            'confidence_summary': confidence['summary'],
            'revenue': confidence['revenue'],
            'prior_service_orders': confidence['prior_service_orders']
        }
        
        ranked.append(ranked_account)
    
    # Sort by confidence score descending
    ranked.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    return ranked

def get_prior_service_orders_with_mc_account(account_id: str, mc_account_id: str) -> List[Dict[str, Any]]:
    """Get prior Service Orders that used this Mission Control Account"""
    
    query = f"""
    SELECT Id, Name, Stage__c, Mission_Control_Account__c, Contract_Start_Date__c
    FROM Service_Order__c 
    WHERE Opportunity__r.AccountId = '{account_id}'
    AND Mission_Control_Account__c = '{mc_account_id}'
    AND (Stage__c = 'Signed' OR Stage__c = 'Terminated')
    ORDER BY Contract_Start_Date__c DESC
    """
    
    try:
        result = subprocess.run([
            'sf', 'data', 'query',
            '-o', 'niamh@telnyx.com', 
            '--query', query,
            '--json'
        ], capture_output=True, text=True, check=True)
        
        response = json.loads(result.stdout)
        return response.get('result', {}).get('records', [])
        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        return []

def update_service_order_mc_account(service_order_id: str, mc_account_id: str) -> Dict[str, Any]:
    """Update Service Order with Mission Control Account"""
    
    try:
        result = subprocess.run([
            'sf', 'data', 'update', 'record',
            '-s', 'Service_Order__c',
            '-i', service_order_id,
            '-v', f'Mission_Control_Account__c={mc_account_id}',
            '-o', 'niamh@telnyx.com',
            '--json'
        ], capture_output=True, text=True, check=True)
        
        response = json.loads(result.stdout)
        
        return {
            'success': True,
            'service_order_id': service_order_id,
            'mc_account_id': mc_account_id,
            'message': 'Mission Control Account linked successfully',
            'salesforce_response': response
        }
        
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'error': f'Failed to update Service Order: {e.stderr or e.stdout}'
        }

# A2A skill interface
def handle_resolve_mission_control_account_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """A2A interface for resolve-mission-control-account skill"""
    
    try:
        account_id = payload.get('account_id')
        service_order_id = payload.get('service_order_id')
        
        if not account_id:
            return {
                'success': False,
                'error': 'account_id is required'
            }
        
        # If user provided mc_account_id for confirmation, update the SO
        confirmed_mc_account_id = payload.get('confirmed_mc_account_id')
        if confirmed_mc_account_id and service_order_id:
            return update_service_order_mc_account(service_order_id, confirmed_mc_account_id)
        
        # Otherwise, perform resolution analysis
        result = resolve_mission_control_account(account_id, service_order_id)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Skill execution error: {str(e)}'
        }

# Example usage
if __name__ == '__main__':
    # Test with PatientSync account
    result = resolve_mission_control_account('0018Z00002wSAKbQAO')
    print(json.dumps(result, indent=2, default=str))