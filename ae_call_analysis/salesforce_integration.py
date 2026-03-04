#!/usr/bin/env python3
"""
Real Salesforce API Integration
Actually checks if prospects exist in Salesforce before posting
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta

def load_env():
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
load_env()

# Cache for access tokens
_sf_access_token = None
_sf_token_expires = None

def get_salesforce_access_token():
    """Get Salesforce access token using OAuth"""
    global _sf_access_token, _sf_token_expires
    
    # Return cached token if still valid
    if _sf_access_token and _sf_token_expires and datetime.now() < _sf_token_expires:
        return _sf_access_token, None
    
    try:
        sf_client_id = os.getenv('SF_CLIENT_ID')
        sf_client_secret = os.getenv('SF_CLIENT_SECRET')
        sf_domain = os.getenv('SF_DOMAIN', 'telnyx')
        
        if not all([sf_client_id, sf_client_secret]):
            return None, "Missing Salesforce credentials"
        
        # OAuth endpoint
        oauth_url = f"https://{sf_domain}.my.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': sf_client_id,
            'client_secret': sf_client_secret
        }
        
        response = requests.post(oauth_url, data=data, timeout=10)
        
        if response.status_code != 200:
            return None, f"Salesforce OAuth failed: {response.status_code}"
        
        token_data = response.json()
        _sf_access_token = token_data.get('access_token')
        
        # Cache token for 55 minutes (tokens typically last 60 minutes)
        _sf_token_expires = datetime.now() + timedelta(minutes=55)
        
        return _sf_access_token, None
        
    except Exception as e:
        return None, f"Error getting Salesforce token: {str(e)}"

def search_salesforce_prospect(prospect_name, prospect_email):
    """Actually search Salesforce for prospect records"""
    try:
        # Get access token
        access_token, error = get_salesforce_access_token()
        if not access_token:
            return None, f"Auth error: {error}"
        
        # Salesforce instance URL
        sf_domain = os.getenv('SF_DOMAIN', 'telnyx')
        instance_url = f"https://{sf_domain}.my.salesforce.com"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Search by email first (most precise)
        if prospect_email:
            soql_query = f"SELECT Id, Name, Email, Account.Name FROM Contact WHERE Email = '{prospect_email}' LIMIT 5"
        else:
            # Search by name (broader)
            clean_name = prospect_name.replace("'", "\\'")
            soql_query = f"SELECT Id, Name, Email, Account.Name FROM Contact WHERE Name LIKE '%{clean_name}%' OR Account.Name LIKE '%{clean_name}%' LIMIT 5"
        
        # Execute SOQL query
        query_url = f"{instance_url}/services/data/v52.0/query"
        params = {'q': soql_query}
        
        response = requests.get(query_url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return None, f"Salesforce query failed: {response.status_code}"
        
        query_result = response.json()
        records = query_result.get('records', [])
        
        if not records:
            return None, "No matching Salesforce records found"
        
        # Return the first match with details
        best_match = records[0]
        
        return {
            'found': True,
            'contact_id': best_match['Id'],
            'contact_name': best_match['Name'],
            'contact_email': best_match.get('Email', ''),
            'account_name': best_match.get('Account', {}).get('Name', '') if best_match.get('Account') else '',
            'record_url': f"{instance_url}/lightning/r/Contact/{best_match['Id']}/view",
            'total_matches': len(records)
        }, None
        
    except Exception as e:
        return None, f"Error searching Salesforce: {str(e)}"

def validate_salesforce_prospect(prospect_name, prospect_email):
    """Validate if prospect exists in Salesforce (for QC filtering)"""
    try:
        result, error = search_salesforce_prospect(prospect_name, prospect_email)
        
        if error:
            print(f"⚠️ Salesforce lookup error: {error}")
            return False, f"Salesforce lookup failed: {error}"
        
        if result and result.get('found'):
            contact_name = result.get('contact_name', '')
            account_name = result.get('account_name', '')
            print(f"✅ Found in Salesforce: {contact_name} at {account_name}")
            return True, f"Found: {contact_name} at {account_name}"
        
        return False, "No matching Salesforce records found"
        
    except Exception as e:
        print(f"❌ Salesforce validation error: {str(e)}")
        return False, f"Salesforce validation error: {str(e)}"

if __name__ == "__main__":
    # Test Salesforce integration
    print("=== TESTING SALESFORCE INTEGRATION ===")
    
    # Test 1: Check authentication
    token, error = get_salesforce_access_token()
    if token:
        print(f"✅ Salesforce auth successful (token: {token[:20]}...)")
    else:
        print(f"❌ Salesforce auth failed: {error}")
        exit(1)
    
    # Test 2: Search for a prospect
    test_name = "Energy Action"
    print(f"\n🔍 Searching for: {test_name}")
    
    result, error = search_salesforce_prospect(test_name, None)
    if result:
        print(f"✅ Found: {result['contact_name']} at {result['account_name']}")
        print(f"📧 Email: {result['contact_email']}")
        print(f"🔗 URL: {result['record_url']}")
    else:
        print(f"❌ Not found: {error}")
    
    # Test 3: Validation function
    print(f"\n🛡️ QC Validation test:")
    is_valid, reason = validate_salesforce_prospect(test_name, None)
    print(f"Result: {is_valid} - {reason}")