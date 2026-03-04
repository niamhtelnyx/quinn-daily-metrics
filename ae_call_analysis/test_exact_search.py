#!/usr/bin/env python3
"""
Test exact Salesforce event search with known subjects
"""

import requests
import os

def load_env():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_salesforce_token():
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    
    if not client_id or not client_secret:
        return None, "Salesforce credentials missing"
    
    try:
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=auth_data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token'), "✅ Salesforce authenticated"
        else:
            return None, f"❌ Salesforce auth failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Salesforce error: {e}"

def test_exact_subject_search(access_token):
    """Test search with the exact subjects we found"""
    
    # Exact subjects from debug output
    exact_subjects = [
        "Meeting Booked: roly@meetgail.com and Ryan: 30-minute Meeting",
        "Meeting Booked: sruthi@eltropy.com and Rob: 30-minute Meeting"
    ]
    
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    for subject in exact_subjects:
        print(f"\n🔍 Testing exact search: {subject}")
        
        # Try exact match search
        escaped_subject = subject.replace("'", "\\'")
        query = f"""
            SELECT Id, Subject, Description, WhoId, StartDateTime
            FROM Event 
            WHERE Subject = '{escaped_subject}'
            LIMIT 1
        """
        
        try:
            response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('records', [])
                
                if events:
                    event = events[0]
                    
                    print(f"✅ Found event!")
                    print(f"   📅 Event ID: {event['Id']}")
                    print(f"   📋 Subject: {event['Subject']}")
                    print(f"   📄 Description: {event.get('Description', 'None')[:100]}...")
                    print(f"   👤 Contact ID: {event.get('WhoId', 'None')}")
                    print(f"   📅 Start Time: {event.get('StartDateTime', 'None')}")
                    
                    # If we found the event, try to get contact info separately
                    if event.get('WhoId'):
                        contact_query = f"SELECT Id, Name, Email, AccountId FROM Contact WHERE Id = '{event['WhoId']}'"
                        contact_response = requests.get(search_url, params={'q': contact_query}, headers=headers, timeout=10)
                        if contact_response.status_code == 200:
                            contact_data = contact_response.json()
                            contacts = contact_data.get('records', [])
                            if contacts:
                                contact = contacts[0]
                                print(f"   👤 Contact Name: {contact.get('Name', 'N/A')}")
                                print(f"   📧 Email: {contact.get('Email', 'N/A')}")
                                print(f"   🆔 Account ID: {contact.get('AccountId', 'N/A')}")
                else:
                    print(f"❌ No event found with exact subject")
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🎯 Testing Exact Salesforce Subject Search")
    print("=" * 50)
    
    load_env()
    
    access_token, auth_msg = get_salesforce_token()
    print(f"🏢 Salesforce: {auth_msg}")
    
    if access_token:
        test_exact_subject_search(access_token)

if __name__ == "__main__":
    main()