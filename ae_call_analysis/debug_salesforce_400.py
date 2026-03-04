#!/usr/bin/env python3
"""
Debug the Salesforce 400 error issue
"""
import os
import requests

# Load environment
env_path = '.env'
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

def test_salesforce_auth():
    """Test Salesforce authentication"""
    print("🔍 TESTING SALESFORCE AUTH")
    
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    
    if not client_id:
        print("❌ Missing SF_CLIENT_ID")
        return None
    
    try:
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post('https://login.salesforce.com/services/oauth2/token', data=auth_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data['access_token']
            print(f"✅ Auth successful")
            return access_token
        else:
            print(f"❌ Auth failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_salesforce_query(access_token):
    """Test the problematic Salesforce query"""
    if not access_token:
        return
    
    print("\n🔍 TESTING SALESFORCE QUERY")
    
    # Test the exact query that's failing
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
    
    # Test query
    event_name = "Telnyx // Voxtelesys"
    subject = "Meeting Booked: " + event_name
    query = f"SELECT Id, Subject, WhoId, OwnerId, AssignedToId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
    
    print(f"Query: {query}")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('records', [])
            print(f"✅ Query successful, found {len(events)} events")
            for event in events:
                print(f"   Event: {event.get('Subject')}")
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Query error: {e}")

if __name__ == "__main__":
    access_token = test_salesforce_auth()
    test_salesforce_query(access_token)
