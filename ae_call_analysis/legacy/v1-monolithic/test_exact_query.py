#!/usr/bin/env python3
"""
Test the exact same query from the original script
"""

import os
import sys
import json
import requests
from datetime import datetime

def get_salesforce_token():
    """Get Salesforce OAuth2 access token using client credentials flow"""
    try:
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        
        if not client_id or not client_secret:
            print("❌ Salesforce credentials missing")
            return None
            
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=data, timeout=30)
        if response.status_code == 200:
            print("✅ Salesforce authenticated")
            return response.json().get('access_token')
        else:
            print(f"❌ Salesforce auth failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Salesforce auth error: {str(e)}")
        return None

def test_query():
    """Test the exact query from original script"""
    token = get_salesforce_token()
    if not token:
        return
        
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    instance_url = f"https://{domain}.my.salesforce.com"
    
    # EXACT query from original script
    query = """SELECT Id, Name, CreatedDate, Owner_Name__c, Owner_Email__c, Contact__c, Lead__c, Handoff_Type__c, Sales_Handoff_Reason__c 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND Owner_Email__c = 'quinn@telnyx.com' 
AND CreatedDate = TODAY 
ORDER BY CreatedDate DESC"""
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"🔍 Running exact query from original script...")
        print(f"Query: {query}")
        
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            records = results.get('records', [])
            total_size = results.get('totalSize', len(records))
            done = results.get('done', True)
            
            print(f"✅ Query successful")
            print(f"📊 Records returned: {len(records)}")
            print(f"📊 Total size: {total_size}")
            print(f"📊 Query done: {done}")
            
            if not done:
                print("⚠️ Query was not complete - there are more records!")
                next_records_url = results.get('nextRecordsUrl')
                if next_records_url:
                    print(f"📄 Next records URL: {next_records_url}")
            
            print(f"\n📋 Sample records:")
            for i, record in enumerate(records[:5], 1):
                created = record.get('CreatedDate', 'N/A')
                name = record.get('Name', 'N/A')
                reason = record.get('Sales_Handoff_Reason__c', 'N/A')
                print(f"  {i}. {name} - {created} - {reason}")
                
        else:
            print(f"❌ Query failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Query error: {str(e)}")

def main():
    """Main execution function"""
    
    # Source environment variables
    env_file = "/Users/niamhcollins/clawd/ae_call_analysis/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    test_query()

if __name__ == "__main__":
    main()