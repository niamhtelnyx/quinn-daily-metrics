#!/usr/bin/env python3
"""
Find the correct fields available on Event object
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

def get_auth_token():
    """Get auth token"""
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
    
    if response.status_code == 200:
        return response.json()['access_token'], None
    else:
        return None, f"Auth failed: {response.status_code}"

def check_event_fields(access_token):
    """Check what fields are available on Event object"""
    print("🔍 CHECKING AVAILABLE EVENT FIELDS")
    
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    describe_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/describe"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(describe_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        fields = data.get('fields', [])
        
        # Look for fields related to assignment/ownership
        relevant_fields = []
        for field in fields:
            field_name = field.get('name', '')
            field_type = field.get('type', '')
            field_label = field.get('label', '')
            
            if any(keyword in field_name.lower() for keyword in ['assign', 'owner', 'created', 'user']):
                relevant_fields.append({
                    'name': field_name,
                    'type': field_type, 
                    'label': field_label
                })
        
        print(f"📋 RELEVANT FIELDS ON EVENT OBJECT:")
        for field in relevant_fields:
            print(f"   • {field['name']} ({field['type']}) - {field['label']}")
            
        return relevant_fields
    else:
        print(f"❌ Describe failed: {response.status_code} - {response.text}")
        return []

def test_corrected_query(access_token):
    """Test query with correct fields"""
    print("\n🔧 TESTING CORRECTED QUERY")
    
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
    
    # Use only OwnerId (which should exist) instead of AssignedToId
    event_name = "Dayforce <> Telnyx"
    subject = "Meeting Booked: " + event_name
    corrected_query = f"SELECT Id, Subject, WhoId, OwnerId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"   Corrected query: {corrected_query}")
    
    response = requests.get(search_url, params={'q': corrected_query}, headers=headers, timeout=10)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        events = data.get('records', [])
        print(f"   ✅ Query works! Found {len(events)} events")
        
        if events:
            event = events[0]
            print(f"   Event details:")
            for key, value in event.items():
                print(f"     {key}: {value}")
        
        return True
    else:
        print(f"   ❌ Query failed: {response.text}")
        return False

def main():
    print("🚀 DEBUGGING EVENT FIELD ISSUES")
    print("=" * 50)
    
    access_token, auth_error = get_auth_token()
    if auth_error:
        print(f"❌ {auth_error}")
        return
    
    print("✅ Got auth token\n")
    
    # Check available fields
    fields = check_event_fields(access_token)
    
    # Test corrected query
    test_corrected_query(access_token)

if __name__ == "__main__":
    main()
