#!/usr/bin/env python3
"""
Implement the CORRECT logic as specified by Niamh - no more creativity!
"""

def implement_correct_salesforce_logic():
    # Read current file
    with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
        content = f.read()
    
    # Add the correct functions EXACTLY as specified
    correct_functions = '''

def extract_event_name_from_google_title(title):
    """Extract event name from Google Drive title: 'Copy of {event name} - {time} - Notes by Gemini'"""
    import re
    pattern = r'^Copy of (.+?) - \\d{4}/\\d{2}/\\d{2} .+ - Notes by Gemini'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return None

def find_salesforce_event_by_exact_subject(event_name, access_token):
    """Find Salesforce event by exact subject: 'Meeting Booked: {event name}'"""
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # EXACT subject match - fix syntax error
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

def update_event_with_ai_analysis(event_id, ai_analysis, google_drive_url, access_token):
    """Update Salesforce event with AI analysis"""
    if not access_token or not event_id:
        return None, "Missing access token or event ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_id}"
        
        description = f"""Call Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 Google Drive Notes: {google_drive_url}

🤖 AI ANALYSIS:
{ai_analysis}

✅ Processed by V1 Enhanced Intelligence"""
        
        update_data = {'Description': description}
        
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

def process_call_correct_logic(call, content):
    """Process call using EXACT logic specified by Niamh"""
    call_id = call['id']
    title = call.get('name', '')
    
    log_message(f"🆕 Processing CORRECT: {title[:60]}...")
    
    # Step 1: Extract event name from Google Drive title
    event_name = extract_event_name_from_google_title(title)
    if not event_name:
        log_message(f"   ❌ Could not extract event name from: {title}")
        return False
    
    log_message(f"   🎯 Event name: '{event_name}'")
    
    # Step 2: Get Salesforce access
    access_token, sf_msg = get_salesforce_access_token()
    if not access_token:
        log_message(f"   🏢 Salesforce: {sf_msg}")
        return False
    
    # Step 3: Find Salesforce event by exact subject
    event_data, event_msg = find_salesforce_event_by_exact_subject(event_name, access_token)
    log_message(f"   🔍 Event: {event_msg}")
    
    if not event_data:
        return False
    
    # Step 4: Get contact from event
    contact_data, contact_msg = get_contact_from_event(event_data['contact_id'], access_token)
    log_message(f"   👤 Contact: {contact_msg}")
    
    if not contact_data:
        return False
    
    # Step 5: Get AE from event
    ae_data, ae_msg = get_ae_from_event(event_data['ae_user_id'], access_token)
    log_message(f"   👔 AE: {ae_msg}")
    
    # Step 6: AI Analysis
    prospect_name = contact_data['contact_name']
    company_name = contact_data.get('company_name', '')
    company_website = contact_data.get('company_website', '')
    
    ai_result = analyze_call_with_ai(content, prospect_name, company_name, company_website)
    
    if ai_result.get('status') not in ['success', None]:
        log_message(f"   🤖 AI Analysis: failed")
        return False
    
    log_message(f"   🤖 AI Analysis: success")
    
    # Step 7: Post to Slack
    main_post = ai_result.get('main_post', 'AI analysis completed')
    thread_reply = ai_result.get('thread_reply', '')
    
    slack_result, slack_ts = post_to_slack_bot_api(main_post)
    slack_status = "✅" if slack_result else "❌"
    
    if slack_result:
        log_message(f"   📱 Slack: ✅ Posted (ts: {slack_ts})")
        if thread_reply:
            post_to_slack_bot_api(thread_reply, thread_ts=slack_ts)
    else:
        log_message(f"   📱 Slack: ❌ Failed")
    
    # Step 8: Update Salesforce event
    google_drive_url = f"https://docs.google.com/document/d/{call_id}/edit"
    ai_text = ai_result.get('summary', main_post)
    
    update_result, update_msg = update_event_with_ai_analysis(
        event_data['event_id'], ai_text, google_drive_url, access_token
    )
    sf_status = "✅" if update_result else "❌"
    log_message(f"   🏢 SF Update: {update_msg}")
    
    # Summary
    prospect_display = f"{prospect_name} ({company_name})" if company_name else prospect_name
    log_message(f"✅ CORRECT: {prospect_display} (Slack: {slack_status}, SF: {sf_status})")
    
    return True

'''
    
    # Find the main loop and replace the processing logic
    # Look for where calls get processed
    start_pattern = "log_message(f\"🆕 Processing ENHANCED:"
    end_pattern = "log_message(f\"✅ ENHANCED:"
    
    start_idx = content.find(start_pattern)
    if start_idx == -1:
        print("❌ Could not find processing start")
        return
    
    end_idx = content.find(end_pattern, start_idx)
    if end_idx == -1:
        print("❌ Could not find processing end")
        return
    
    # Find end of the line
    end_line = content.find('\n', end_idx)
    if end_line == -1:
        end_line = len(content)
    
    # Replace with new logic
    new_processing = '''        
        # Use CORRECT logic as specified by Niamh
        if process_call_correct_logic(call, content):
            processed_count += 1'''
    
    before = content[:start_idx]  
    after = content[end_line:]
    
    new_content = before + new_processing + correct_functions + after
    
    # Write back
    with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Applied CORRECT logic as specified by Niamh")

if __name__ == "__main__":
    implement_correct_salesforce_logic()
