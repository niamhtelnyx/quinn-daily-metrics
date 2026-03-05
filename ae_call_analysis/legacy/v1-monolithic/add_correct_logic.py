#!/usr/bin/env python3
"""
Add the correct logic functions to V1_GOOGLE_DRIVE_ENHANCED.py
"""

# Read the original file
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
    content = f.read()

# Find where to insert the new functions (after existing functions, before main())
insert_point = content.find('def main():')
if insert_point == -1:
    print("❌ Could not find main() function")
    exit(1)

# New functions with correct logic
new_functions = '''
def extract_event_name_from_google_title(title):
    """Extract event name from: Copy of {event name} - {time} - Notes by Gemini"""
    import re
    pattern = r'^Copy of (.+?) - \\d{4}/\\d{2}/\\d{2} .+ - Notes by Gemini'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return None

def find_salesforce_event_by_exact_subject(event_name, access_token):
    """Find Salesforce event by exact subject: Meeting Booked: {event name}"""
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # EXACT subject match
        subject = "Meeting Booked: " + event_name
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
                    'ae_user_id': event.get('AssignedToId') or event.get('OwnerId'),
                    'subject': event['Subject']
                }, f"✅ Found event: {event['Subject']}"
            else:
                return None, f"❌ No event found: Meeting Booked: {event_name}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
    except Exception as e:
        return None, f"❌ Event search error: {e}"

def get_contact_from_event(contact_id, access_token):
    """Get contact details from contact ID"""
    if not access_token or not contact_id:
        return None, "Missing access token or contact ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx') 
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Website FROM Contact WHERE Id = '{contact_id}'"
        
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
                    'company_name': account.get('Name'),
                    'company_website': account.get('Website')
                }, f"✅ Found contact: {contact['Name']}"
            else:
                return None, f"❌ No contact found: {contact_id}"
        else:
            return None, f"❌ Contact lookup failed: {response.status_code}"
    except Exception as e:
        return None, f"❌ Contact lookup error: {e}"

def get_ae_from_event(user_id, access_token):
    """Get AE details from user ID"""  
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
                    'ae_name': user['Name'],
                    'ae_email': user.get('Email')
                }, f"✅ Found AE: {user['Name']}"
            else:
                return None, f"❌ No AE found: {user_id}"
        else:
            return None, f"❌ AE lookup failed: {response.status_code}"
    except Exception as e:
        return None, f"❌ AE lookup error: {e}"

'''

# Insert the functions before main()
new_content = content[:insert_point] + new_functions + content[insert_point:]

# Write back
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
    f.write(new_content)

print("✅ Added correct logic functions")
