#!/usr/bin/env python3
"""
Debug Quinn handoffs - check actual dates and sample records
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

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

def debug_handoffs():
    """Debug handoffs query"""
    token = get_salesforce_token()
    if not token:
        return
        
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    instance_url = f"https://{domain}.my.salesforce.com"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # First, check what TODAY means in Salesforce
    print("\n🔍 Checking TODAY query...")
    today_query = """SELECT Id, Name, CreatedDate, Owner_Name__c, Owner_Email__c 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND Owner_Email__c = 'quinn@telnyx.com' 
AND CreatedDate = TODAY 
ORDER BY CreatedDate DESC
LIMIT 10"""
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': today_query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            records = results.get('records', [])
            print(f"✅ TODAY query: {len(records)} records (showing first 10 of {results.get('totalSize', '?')} total)")
            
            if records:
                print("\n📋 Sample records:")
                for i, record in enumerate(records[:5], 1):
                    created = record.get('CreatedDate', 'N/A')
                    name = record.get('Name', 'N/A')
                    print(f"  {i}. {name} - {created}")
            else:
                print("No records found")
        else:
            print(f"❌ Query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Query error: {str(e)}")
    
    # Check recent handoffs (last 7 days)
    print("\n🔍 Checking last 7 days...")
    recent_query = """SELECT Id, Name, CreatedDate, Owner_Name__c 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND CreatedDate >= LAST_N_DAYS:7 
ORDER BY CreatedDate DESC
LIMIT 10"""
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': recent_query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            records = results.get('records', [])
            print(f"✅ Last 7 days: {len(records)} records (showing first 10 of {results.get('totalSize', '?')} total)")
            
            if records:
                print("\n📋 Recent records:")
                for i, record in enumerate(records[:5], 1):
                    created = record.get('CreatedDate', 'N/A')
                    name = record.get('Name', 'N/A')
                    print(f"  {i}. {name} - {created}")
        else:
            print(f"❌ Query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Query error: {str(e)}")
    
    # Check if Quinn exists at all
    print("\n🔍 Checking if Quinn Taylor exists...")
    quinn_query = """SELECT Id, Name, CreatedDate 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
ORDER BY CreatedDate DESC
LIMIT 5"""
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': quinn_query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            records = results.get('records', [])
            print(f"✅ Quinn records total: {results.get('totalSize', '?')}")
            
            if records:
                print("\n📋 Latest Quinn records:")
                for i, record in enumerate(records, 1):
                    created = record.get('CreatedDate', 'N/A')
                    name = record.get('Name', 'N/A')
                    print(f"  {i}. {name} - {created}")
        else:
            print(f"❌ Query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Query error: {str(e)}")

def main():
    """Main execution function"""
    print("🔍 Debugging Quinn handoffs query...")
    
    # Source environment variables
    env_file = "/Users/niamhcollins/clawd/ae_call_analysis/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    debug_handoffs()

if __name__ == "__main__":
    main()