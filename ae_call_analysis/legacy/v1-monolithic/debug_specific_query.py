#!/usr/bin/env python3
"""
Debug the specific Salesforce query that's failing
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

def test_queries():
    print("🔍 TESTING SPECIFIC SALESFORCE QUERIES")
    
    # Get auth token (same as working contact search)
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    
    auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response = requests.post(auth_url, data=auth_data, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Auth failed: {response.status_code} - {response.text}")
        return
    
    access_token = response.json()['access_token']
    print("✅ Got access token")
    
    # Test 1: Old working contact search
    search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    test_query = "SELECT Id, Name FROM Contact LIMIT 1"
    print(f"\n1️⃣ Testing simple contact query...")
    response = requests.get(search_url, params={'q': test_query}, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Contact query works")
    
    # Test 2: Simple event query
    test_query2 = "SELECT Id, Subject FROM Event LIMIT 1"
    print(f"\n2️⃣ Testing simple event query...")
    response = requests.get(search_url, params={'q': test_query2}, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Event query works")
        events = response.json().get('records', [])
        print(f"Found {len(events)} events")
    
    # Test 3: Event query with WHERE clause
    test_subject = "Meeting Booked: Dayforce <> Telnyx"
    test_query3 = f"SELECT Id, Subject, WhoId FROM Event WHERE Subject = '{test_subject}' LIMIT 1"
    print(f"\n3️⃣ Testing event query with WHERE...")
    print(f"Query: {test_query3}")
    response = requests.get(search_url, params={'q': test_query3}, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("✅ Event WHERE query works")
        events = response.json().get('records', [])
        print(f"Found {len(events)} events")

if __name__ == "__main__":
    test_queries()
