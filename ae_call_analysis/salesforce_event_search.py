#!/usr/bin/env python3
"""
Enhanced Salesforce integration - search events by meeting subject
Much more reliable than searching contacts by name
"""

import requests
import re
import os

def load_env():
    """Load environment variables"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_salesforce_token():
    """Get Salesforce OAuth2 access token"""
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

def extract_core_meeting_title(google_doc_title):
    """Extract the core meeting title from Google Doc filename"""
    
    # Pattern: "Copy of roly@meetgail.com and Ryan: 30-minute Meeting - 2026/03/03 15:59 EST - Notes by Gemini"
    # Want: "roly@meetgail.com and Ryan: 30-minute Meeting"
    
    try:
        # Remove "Copy of " prefix if present
        title = google_doc_title
        if title.startswith('Copy of '):
            title = title[8:]  # Remove "Copy of "
        
        # Remove date and "Notes by Gemini" suffix
        # Look for patterns like "- 2026/03/03" or "- Notes by Gemini"
        patterns_to_remove = [
            r'\s*-\s*\d{4}/\d{2}/\d{2}.*',  # Date and everything after
            r'\s*-\s*Notes by Gemini.*',     # Notes by Gemini and after
        ]
        
        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title)
        
        return title.strip()
        
    except Exception as e:
        print(f"Error extracting core title: {e}")
        return google_doc_title

def find_salesforce_event_by_subject(core_title, access_token):
    """Find Salesforce event by searching the subject field"""
    
    if not access_token:
        return None, "No access token"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Search for events with subject containing the core meeting title
        # Salesforce pattern: "Meeting Booked: [core_title]"
        escaped_title = core_title.replace("'", "\\'")  # Escape single quotes for SOQL
        
        # Try multiple search patterns
        search_patterns = [
            f"Subject = 'Meeting Booked: {escaped_title}'",        # Exact match
            f"Subject LIKE 'Meeting Booked: {escaped_title}%'",    # Starts with (in case of extra text)
            f"Subject LIKE '%{escaped_title}%'",                   # Contains anywhere
        ]
        
        # Also try searching by key identifiers from the title
        if '@' in core_title:
            email_part = core_title.split('@')[0] + '@' + core_title.split('@')[1].split()[0]
            search_patterns.append(f"Subject LIKE '%{email_part}%'")
        
        # Extract first name for alternate search
        if ' and ' in core_title:
            first_part = core_title.split(' and ')[0]
            if '@' in first_part:
                search_patterns.append(f"Subject LIKE '%{first_part}%'")
        
        for pattern in search_patterns:
            query = f"""
                SELECT Id, Subject, Description, WhoId, WhatId, StartDateTime, EndDateTime
                FROM Event 
                WHERE {pattern}
                AND StartDateTime >= LAST_N_DAYS:60
                ORDER BY StartDateTime DESC
                LIMIT 5
            """
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('records', [])
                
                if events:
                    # Return the first matching event with enhanced data
                    event = events[0]
                    
                    # Base event data
                    event_data = {
                        'event_id': event['Id'],
                        'subject': event.get('Subject', ''),
                        'description': event.get('Description', ''),
                        'start_time': event.get('StartDateTime', ''),
                        'end_time': event.get('EndDateTime', ''),
                        'contact_id': event.get('WhoId', ''),
                        'contact_name': '',
                        'contact_email': '',
                        'account_id': '',
                        'company_name': '',
                        'company_website': ''
                    }
                    
                    # Get contact info separately if WhoId exists
                    if event.get('WhoId'):
                        contact_query = f"""
                            SELECT Id, Name, Email, AccountId
                            FROM Contact 
                            WHERE Id = '{event['WhoId']}'
                        """
                        
                        contact_response = requests.get(search_url, params={'q': contact_query}, headers=headers, timeout=10)
                        if contact_response.status_code == 200:
                            contact_data = contact_response.json()
                            contacts = contact_data.get('records', [])
                            if contacts:
                                contact = contacts[0]
                                event_data['contact_name'] = contact.get('Name', '')
                                event_data['contact_email'] = contact.get('Email', '')
                                event_data['account_id'] = contact.get('AccountId', '')
                                
                                # Get account info if AccountId exists
                                if contact.get('AccountId'):
                                    account_query = f"""
                                        SELECT Id, Name, Website
                                        FROM Account 
                                        WHERE Id = '{contact['AccountId']}'
                                    """
                                    
                                    account_response = requests.get(search_url, params={'q': account_query}, headers=headers, timeout=10)
                                    if account_response.status_code == 200:
                                        account_data = account_response.json()
                                        accounts = account_data.get('records', [])
                                        if accounts:
                                            account = accounts[0]
                                            event_data['company_name'] = account.get('Name', '')
                                            event_data['company_website'] = account.get('Website', '')
                    
                    return event_data, f"✅ Found event: {event['Subject']}"
        
        return None, f"⚠️ No event found for meeting: {core_title}"
        
    except Exception as e:
        return None, f"❌ Event search error: {e}"

def update_salesforce_event_with_urls(event_id, fellow_url, google_doc_url, access_token):
    """Update Salesforce event with Fellow recording URL and Google Doc URL"""
    
    if not access_token or not event_id:
        return False, "Missing access token or event ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_id}"
        
        # Create enhanced description with both URLs
        description_lines = [
            "Call Intelligence Analysis",
            "",
            f"📞 Fellow Recording: {fellow_url}" if fellow_url else "",
            f"📝 Google Meet Notes: {google_doc_url}" if google_doc_url else "",
            "",
            f"✅ Processed by V2 Enhanced Intelligence - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        description = "\n".join(line for line in description_lines if line)
        
        update_data = {
            'Description': description
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)
        
        if response.status_code == 204:
            return True, f"✅ Updated event {event_id}"
        else:
            return False, f"❌ Event update failed: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Event update error: {e}"

def test_event_search():
    """Test the enhanced Salesforce event search"""
    print("🎯 Testing Enhanced Salesforce Event Search")
    print("=" * 60)
    
    load_env()
    
    # Test cases
    test_cases = [
        "Copy of roly@meetgail.com and Ryan: 30-minute Meeting - 2026/03/03 15:59 EST - Notes by Gemini",
        "Copy of sruthi@eltropy.com and Rob: 30-minute Meeting - 2026/02/25 09:23 EST - Notes by Gemini",
        "Copy of Ken <> Ryan - 2026/03/02 13:15 EST - Notes by Gemini"
    ]
    
    # Get Salesforce token
    access_token, auth_msg = get_salesforce_token()
    print(f"🏢 Salesforce: {auth_msg}")
    
    if not access_token:
        return
    
    for google_doc_title in test_cases:
        print(f"\n📄 Testing: {google_doc_title}")
        print("-" * 40)
        
        # Extract core title
        core_title = extract_core_meeting_title(google_doc_title)
        print(f"📋 Core title: {core_title}")
        
        # Search for event
        event_data, search_msg = find_salesforce_event_by_subject(core_title, access_token)
        print(f"🔍 Search: {search_msg}")
        
        if event_data:
            print(f"✅ Event found:")
            print(f"   📅 Event ID: {event_data['event_id']}")
            print(f"   📋 Subject: {event_data['subject']}")
            print(f"   👤 Contact: {event_data['contact_name']}")
            print(f"   📧 Email: {event_data['contact_email']}")
            print(f"   🏢 Company: {event_data['company_name']}")
            print(f"   🌐 Website: {event_data['company_website']}")

if __name__ == "__main__":
    from datetime import datetime
    test_event_search()