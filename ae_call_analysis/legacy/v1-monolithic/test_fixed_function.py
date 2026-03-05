#!/usr/bin/env python3
"""
Test the fixed find_salesforce_event_by_exact_subject function
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

def find_salesforce_event_by_exact_subject_FIXED(event_name, access_token):
    """FIXED version of the function"""
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # EXACT subject match - FIXED: removed non-existent AssignedToId field
        subject = "Meeting Booked: " + event_name
        query = f"SELECT Id, Subject, WhoId, OwnerId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('records', [])
            if events:
                event = events[0]
                return {
                    'event_id': event['Id'],
                    'contact_id': event['WhoId'], 
                    'ae_user_id': event.get('OwnerId'),  # FIXED: use OwnerId instead
                    'subject': event['Subject']
                }, f"✅ Found event: {event['Subject']}"
            else:
                return None, f"❌ No event found: Meeting Booked: {event_name}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Event search error: {e}"

def main():
    print("🚀 TESTING FIXED FUNCTION")
    print("=" * 40)
    
    access_token, auth_error = get_auth_token()
    if auth_error:
        print(f"❌ {auth_error}")
        return
    
    print("✅ Got auth token")
    
    # Test with known event
    test_events = [
        "Dayforce <> Telnyx",
        "Telnyx // Voxtelesys"
    ]
    
    for event_name in test_events:
        print(f"\n🔍 Testing: '{event_name}'")
        result, message = find_salesforce_event_by_exact_subject_FIXED(event_name, access_token)
        
        print(f"   Result: {message}")
        if result:
            print(f"   Event ID: {result['event_id']}")
            print(f"   Contact ID: {result['contact_id']}")
            print(f"   AE User ID: {result['ae_user_id']}")

if __name__ == "__main__":
    main()
