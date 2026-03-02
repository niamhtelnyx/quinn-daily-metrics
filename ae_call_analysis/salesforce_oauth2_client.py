#!/usr/bin/env python3
"""
Working OAuth2 Salesforce Client for Call Intelligence
Uses the same OAuth2 approach as service-order-specialist
"""

import os
import requests
from datetime import datetime, timedelta
from simple_salesforce import Salesforce
import logging

def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env_file()

logger = logging.getLogger(__name__)

# Global client cache
_sf_client = None
_sf_token_expires = None

def get_salesforce_client():
    """
    Get authenticated Salesforce client using OAuth2 Client Credentials.
    
    Required environment variables:
    SF_CLIENT_ID: Connected App Consumer Key  
    SF_CLIENT_SECRET: Connected App Consumer Secret
    SF_DOMAIN: 'telnyx' for your custom domain
    """
    global _sf_client, _sf_token_expires
    
    # Return cached client if still valid
    if _sf_client and _sf_token_expires and datetime.utcnow() < _sf_token_expires:
        return _sf_client
    
    # Get OAuth2 credentials from environment
    client_id = os.environ.get('SF_CLIENT_ID')
    client_secret = os.environ.get('SF_CLIENT_SECRET') 
    domain = os.environ.get('SF_DOMAIN', 'telnyx')
    
    if not client_id or not client_secret:
        raise ValueError(
            "Salesforce OAuth2 credentials required. Set environment variables:\n"
            "  SF_CLIENT_ID=your_connected_app_consumer_key\n" 
            "  SF_CLIENT_SECRET=your_connected_app_consumer_secret\n"
            "  SF_DOMAIN=telnyx"
        )
    
    # OAuth2 token endpoint
    token_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
    
    print(f"🔐 Authenticating to Salesforce via OAuth2 ({domain})")
    
    # Request access token using client credentials grant
    response = requests.post(token_url, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    })
    
    if response.status_code != 200:
        print(f"❌ Salesforce OAuth2 failed: {response.status_code} - {response.text}")
        raise ValueError(f"Salesforce OAuth2 failed: {response.status_code} - {response.text}")
    
    token_data = response.json()
    access_token = token_data['access_token']
    instance_url = token_data['instance_url']
    
    # Token expires in 2 hours, refresh at 1.5 hours  
    _sf_token_expires = datetime.utcnow() + timedelta(hours=1, minutes=30)
    
    print(f"✅ Connected to Salesforce: {instance_url}")
    
    _sf_client = Salesforce(
        instance_url=instance_url,
        session_id=access_token
    )
    
    return _sf_client

def sf_query(soql_query):
    """Execute SOQL query with automatic session renewal."""
    try:
        sf = get_salesforce_client()
        return sf.query(soql_query)
    except Exception as e:
        err_str = str(e)
        if 'INVALID_SESSION_ID' in err_str or 'Session expired' in err_str:
            logger.warning("Session expired, re-authenticating...")
            global _sf_client, _sf_token_expires
            _sf_client = None
            _sf_token_expires = None
            sf = get_salesforce_client()
            return sf.query(soql_query)
        raise

def sf_update(sobject_type, record_id, data):
    """Update Salesforce record with automatic session renewal."""
    try:
        sf = get_salesforce_client()
        
        # Get the SObject for the given type
        sobject = getattr(sf, sobject_type)
        result = sobject.update(record_id, data)
        
        return {'success': True, 'id': record_id, 'result': result}
        
    except Exception as e:
        err_str = str(e)
        if 'INVALID_SESSION_ID' in err_str or 'Session expired' in err_str:
            logger.warning("Session expired, re-authenticating...")
            global _sf_client, _sf_token_expires
            _sf_client = None
            _sf_token_expires = None
            sf = get_salesforce_client()
            
            # Retry the update
            sobject = getattr(sf, sobject_type)
            result = sobject.update(record_id, data)
            return {'success': True, 'id': record_id, 'result': result}
        
        return {'success': False, 'error': str(e)}

class CallIntelligenceSalesforceClient:
    """Salesforce client specifically for Call Intelligence event lookup"""
    
    def __init__(self):
        self.sf = get_salesforce_client()
    
    def lookup_event_by_prospect(self, prospect_name, call_date=None):
        """Look up Salesforce event by prospect name"""
        
        # Search patterns for Telnyx intro calls
        search_patterns = [
            f'Meeting Booked: Telnyx Intro Call ({prospect_name})',
            f'Telnyx Intro Call ({prospect_name})',
            prospect_name
        ]
        
        for pattern in search_patterns:
            event = self._search_events_by_pattern(pattern)
            if event:
                return self._format_event_data(event)
        
        return None
    
    def _search_events_by_pattern(self, pattern):
        """Search for events matching pattern"""
        
        soql_query = f"""
        SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId,
               Who.Name, Who.Email, Who.Account.Name, Who.Account.Id,
               Owner.Name, Owner.Email
        FROM Event 
        WHERE Subject LIKE '%{pattern}%'
        ORDER BY StartDateTime DESC
        LIMIT 5
        """
        
        try:
            result = sf_query(soql_query)
            return result['records'][0] if result['records'] else None
        except Exception as e:
            print(f"❌ Salesforce query error: {e}")
            return None
    
    def _format_event_data(self, event):
        """Format event data for Call Intelligence"""
        
        return {
            'event_id': event.get('Id'),
            'subject': event.get('Subject'),
            'start_datetime': event.get('StartDateTime'),
            'contact_name': event.get('Who', {}).get('Name') if event.get('Who') else None,
            'account_name': event.get('Who', {}).get('Account', {}).get('Name') if event.get('Who') else None,
            'owner_name': event.get('Owner', {}).get('Name') if event.get('Owner') else None,
            'formatted_ae_names': event.get('Owner', {}).get('Name') if event.get('Owner') else None
        }

# Test function
def test_salesforce_connection():
    """Test Salesforce OAuth2 connection"""
    try:
        client = CallIntelligenceSalesforceClient()
        print("✅ Salesforce OAuth2 connection successful!")
        
        # Test query
        result = sf_query("SELECT Id, Name FROM Account LIMIT 1")
        print(f"✅ Test query successful: {len(result['records'])} records")
        return True
        
    except Exception as e:
        print(f"❌ Salesforce connection failed: {e}")
        return False

if __name__ == "__main__":
    test_salesforce_connection()