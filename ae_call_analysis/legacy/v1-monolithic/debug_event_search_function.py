#!/usr/bin/env python3
"""
Debug the find_salesforce_event_by_exact_subject function step by step
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
    """Get auth token same way as main system"""
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
        return None, f"Auth failed: {response.status_code} - {response.text}"

def find_salesforce_event_by_exact_subject_DEBUG(event_name, access_token):
    """EXACT copy of the function from V1_GOOGLE_DRIVE_ENHANCED.py with debug output"""
    print(f"🔍 DEBUG find_salesforce_event_by_exact_subject:")
    print(f"   event_name: '{event_name}'")
    print(f"   access_token: {'***' + access_token[-10:] if access_token else None}")
    
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        print(f"   domain: {domain}")
        print(f"   search_url: {search_url}")
        
        # EXACT subject match - fixed syntax
        subject = "Meeting Booked: " + event_name
        query = f"SELECT Id, Subject, WhoId, OwnerId, AssignedToId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
        
        print(f"   subject: '{subject}'")
        print(f"   query: {query}")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"   headers: Authorization=Bearer ***{access_token[-10:]}, Content-Type=application/json")
        print(f"   Making request...")
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        print(f"   response.status_code: {response.status_code}")
        print(f"   response.headers: {dict(response.headers)}")
        print(f"   response.text: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('records', [])
            if events:
                event = events[0]
                return {
                    'event_id': event['Id'],
                    'contact_id': event['WhoId'], 
                    'ae_user_id': event.get('AssignedToId') or event.get('OwnerId'),
                    'subject': event['Subject']
                }, f"✅ Found event: {event['Subject']}"
            else:
                return None, f"❌ No event found: Meeting Booked: {event_name}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
            
    except Exception as e:
        print(f"   EXCEPTION: {e}")
        return None, f"❌ Event search error: {e}"

def manual_query_test(access_token, event_name):
    """Test the same query manually"""
    print(f"\n🔍 MANUAL QUERY TEST:")
    
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
    
    subject = "Meeting Booked: " + event_name
    query = f"SELECT Id, Subject, WhoId, OwnerId, AssignedToId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"   Same query: {query}")
    
    response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
    
    print(f"   Manual status: {response.status_code}")
    print(f"   Manual response: {response.text}")

def main():
    print("🚀 DEBUGGING find_salesforce_event_by_exact_subject FUNCTION")
    print("=" * 70)
    
    # Test with event that we know exists
    event_name = "Dayforce <> Telnyx"
    
    print(f"Testing with: '{event_name}'")
    
    # Get auth token
    access_token, auth_error = get_auth_token()
    if auth_error:
        print(f"❌ {auth_error}")
        return
    
    print("✅ Got auth token")
    
    # Test the actual function
    print("\n" + "="*50)
    result, message = find_salesforce_event_by_exact_subject_DEBUG(event_name, access_token)
    print(f"\n📋 FUNCTION RESULT:")
    print(f"   result: {result}")
    print(f"   message: {message}")
    
    # Compare to manual query
    print("\n" + "="*50)
    manual_query_test(access_token, event_name)

if __name__ == "__main__":
    main()
