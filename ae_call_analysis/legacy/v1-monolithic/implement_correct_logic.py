#!/usr/bin/env python3
"""
Implement the correct Salesforce logic in V1_GOOGLE_DRIVE_ENHANCED.py
"""

def update_v1_enhanced():
    # Read the current file
    with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
        content = f.read()
    
    # Add the correct functions after the existing function definitions
    correct_functions = '''

# ============================================================================
# CORRECT SALESFORCE LOGIC (Definitive version)
# ============================================================================

def extract_event_name_from_title(title):
    """Extract event name from Google Drive document title"""
    import re
    # Pattern: "Copy of {event name} - {event time} - Notes by Gemini"
    pattern = r'^Copy of (.+?) - \\d{4}/\\d{2}/\\d{2} .+ - Notes by Gemini'
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
        
        # Exact subject match - escape single quotes
        subject = f"Meeting Booked: {event_name.replace("'", "\\\\'")}"
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
        
        # Clean AI analysis for Salesforce (remove markdown, etc.)
        clean_analysis = ai_analysis.replace('*', '').replace('#', '').replace('`', '')
        
        description = f"""Call Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 Google Drive Notes: {google_drive_url}

🤖 AI ANALYSIS:
{clean_analysis}

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

def process_call_with_correct_logic(call, content):
    """Process call using the correct Salesforce logic"""
    call_id = call['id']
    title = call.get('name', '')
    
    log_message(f"🆕 Processing CORRECT: {title[:60]}...")
    
    # Step 1: Extract event name from title
    event_name = extract_event_name_from_title(title)
    if not event_name:
        log_message(f"   ❌ Could not extract event name from: {title}")
        return False
    
    log_message(f"   🎯 Event name: {event_name}")
    
    # Step 2: Get Salesforce access token
    access_token, sf_msg = get_salesforce_access_token()
    if not access_token:
        log_message(f"   🏢 Salesforce: {sf_msg}")
        return False
    
    # Step 3: Find Salesforce event by exact subject match
    event_data, event_msg = find_salesforce_event_by_name(event_name, access_token)
    log_message(f"   🔍 Event search: {event_msg}")
    
    if not event_data:
        return False
    
    # Step 4: Get contact details
    contact_data, contact_msg = get_contact_details(event_data['contact_id'], access_token)
    log_message(f"   👤 Contact: {contact_msg}")
    
    if not contact_data:
        return False
    
    # Step 5: Get AE details
    ae_data, ae_msg = get_ae_details(event_data['ae_user_id'], access_token)
    log_message(f"   👔 AE: {ae_msg}")
    
    # Step 6: AI Analysis (using contact name for AI)
    prospect_name = contact_data['contact_name']
    company_name = contact_data.get('company_name', '')
    company_website = contact_data.get('company_website', '')
    
    log_message(f"   🤖 Running AI analysis for: {prospect_name}")
    ai_result = analyze_call_with_ai(content, prospect_name, company_name, company_website)
    
    if ai_result.get('status') not in ['success', None]:
        log_message(f"   🤖 AI Analysis: failed")
        return False
    
    log_message(f"   🤖 AI Analysis: success")
    
    # Step 7: Post to Slack
    main_post = ai_result.get('main_post', 'AI analysis completed')
    thread_reply = ai_result.get('thread_reply', '')
    
    slack_result, slack_ts = post_to_slack_bot_api(main_post)
    
    if slack_result:
        log_message(f"   📱 Slack Main: ✅ Posted to Slack (ts: {slack_ts})")
        
        # Post thread reply if available
        if thread_reply:
            thread_result, _ = post_to_slack_bot_api(thread_reply, thread_ts=slack_ts)
            if thread_result:
                log_message(f"   📱 Slack Thread: ✅ Posted thread reply")
    else:
        log_message(f"   📱 Slack Main: ❌ Failed to post")
    
    # Step 8: Update Salesforce event
    google_drive_url = f"https://docs.google.com/document/d/{call_id}/edit"
    ai_text = ai_result.get('summary', main_post)
    
    update_result, update_msg = update_salesforce_event_with_analysis(
        event_data['event_id'], ai_text, google_drive_url, access_token
    )
    log_message(f"   🏢 SF Update: {update_msg}")
    
    # Summary
    prospect_display = f"{prospect_name} ({company_name})" if company_name else prospect_name
    slack_status = "✅" if slack_result else "❌"
    sf_status = "✅" if update_result else "❌"
    
    log_message(f"✅ CORRECT: {prospect_display} (Slack: {slack_status}, SF: {sf_status}, AI: ✅)")
    
    return True

'''
    
    # Find the main processing loop and replace it
    # Look for the current processing logic
    start_marker = "log_message(f\"🆕 Processing ENHANCED: {title[:60]}...\")"
    end_marker = "log_message(f\"✅ ENHANCED:"
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Could not find processing loop start marker")
        return
    
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        print("❌ Could not find processing loop end marker")  
        return
    
    # Find the end of that log message line
    end_line = content.find('\n', end_idx)
    if end_line == -1:
        end_line = len(content)
    
    # Replace the processing section
    new_processing = '''        
        # Use CORRECT Salesforce logic
        if process_call_with_correct_logic(call, content):
            processed_count += 1
            
        # Track in database
        db_entry = (call_id, title, prospect_name, '', datetime.now().isoformat())
        cursor.execute("INSERT OR REPLACE INTO processed_calls (call_id, title, prospect_name, ae_name, processed_date) VALUES (?, ?, ?, ?, ?)", db_entry)'''
    
    # Build the new content
    before_processing = content[:start_idx]
    after_processing = content[end_line:]
    
    new_content = before_processing + new_processing + correct_functions + after_processing
    
    # Write the updated file
    with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Updated V1_GOOGLE_DRIVE_ENHANCED.py with correct Salesforce logic")

if __name__ == "__main__":
    update_v1_enhanced()
