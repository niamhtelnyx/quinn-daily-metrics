#!/usr/bin/env python3
"""
DEFINITIVE SALESFORCE LOGIC (as specified by Niamh)

Google Drive: "Copy of {event name} - {event time} - Notes by Gemini"
Salesforce: "Meeting Booked: {event name}"

Process:
1. Extract {event name} from Google Drive document title
2. Search Salesforce for event: WHERE subject = "Meeting Booked: {event name}"
3. Extract WhoId (contact) and AssignedToId (AE) from event
4. Lookup contact + account details using contact ID  
5. Lookup AE details using user ID
6. Update event record with AI analysis
"""
import re
import requests
import os
from datetime import datetime

def extract_event_name_from_title(title):
    """Extract event name from Google Drive document title"""
    # Pattern: "Copy of {event name} - {event time} - Notes by Gemini"
    pattern = r'^Copy of (.+?) - \d{4}/\d{2}/\d{2} .+ - Notes by Gemini'
    match = re.search(pattern, title)
    
    if match:
        event_name = match.group(1).strip()
        return event_name
    else:
        return None

def find_salesforce_event_by_name(event_name, access_token):
    """Find Salesforce event by exact subject match"""
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Exact subject match
        subject = f"Meeting Booked: {event_name}"
        query = f"SELECT Id, Subject, WhoId, OwnerId, AssignedToId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
        
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
                    'ae_user_id': event.get('AssignedToId') or event.get('OwnerId'),  # Fallback to OwnerId
                    'subject': event['Subject']
                }, f"✅ Found event: {event['Subject']}"
            else:
                return None, f"❌ No event found with subject: {subject}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Event search error: {e}"

def get_contact_details(contact_id, access_token):
    """Get contact + account details using contact ID"""
    if not access_token or not contact_id:
        return None, "Missing access token or contact ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Description, Account.Website FROM Contact WHERE Id = '{contact_id}'"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('records', [])
            if contacts:
                contact = contacts[0]
                account = contact.get('Account', {})
                return {
                    'contact_id': contact['Id'],
                    'contact_name': contact['Name'],
                    'contact_email': contact.get('Email'),
                    'account_id': contact.get('AccountId'),
                    'company_name': account.get('Name'),
                    'company_website': account.get('Website'),
                    'company_description': account.get('Description')
                }, f"✅ Found contact: {contact['Name']}"
            else:
                return None, f"❌ No contact found with ID: {contact_id}"
        else:
            return None, f"❌ Contact lookup failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Contact lookup error: {e}"

def get_ae_details(user_id, access_token):
    """Get AE details using user ID"""
    if not access_token or not user_id:
        return None, "Missing access token or user ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        query = f"SELECT Id, Name, Email FROM User WHERE Id = '{user_id}'"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('records', [])
            if users:
                user = users[0]
                return {
                    'ae_id': user['Id'],
                    'ae_name': user['Name'],
                    'ae_email': user.get('Email')
                }, f"✅ Found AE: {user['Name']}"
            else:
                return None, f"❌ No user found with ID: {user_id}"
        else:
            return None, f"❌ AE lookup failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ AE lookup error: {e}"

def update_salesforce_event_with_analysis(event_id, ai_analysis, google_drive_url, access_token):
    """Update event record with AI analysis"""
    if not access_token or not event_id:
        return None, "Missing access token or event ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_id}"
        
        description = f"""Call Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 Google Drive Notes: {google_drive_url}

🤖 AI ANALYSIS:
{ai_analysis}

✅ Processed by V1 Enhanced Intelligence (Google Drive)"""
        
        update_data = {
            'Description': description
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)
        
        if response.status_code == 204:
            return event_id, f"✅ Updated event {event_id}"
        else:
            return None, f"❌ Event update failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Event update error: {e}"

# Test with Voxtelesys example
def test_correct_logic():
    title = "Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini"
    
    print("🔍 TESTING CORRECT SALESFORCE LOGIC")
    print("-" * 60)
    
    # Step 1: Extract event name
    event_name = extract_event_name_from_title(title)
    print(f"1️⃣ Extracted event name: '{event_name}'")
    
    # Step 2: Build expected Salesforce subject
    if event_name:
        sf_subject = f"Meeting Booked: {event_name}"
        print(f"2️⃣ Expected SF subject: '{sf_subject}'")
        
        # This should match your actual Salesforce event!
        print(f"3️⃣ Should find your event: 'Meeting Booked: Telnyx // Voxtelesys'")
    else:
        print("❌ Failed to extract event name")

if __name__ == "__main__":
    test_correct_logic()
