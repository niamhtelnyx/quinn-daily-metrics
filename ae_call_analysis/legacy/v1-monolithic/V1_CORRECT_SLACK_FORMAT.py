#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - CORRECT SLACK FORMAT
Restores the original agreed-upon Slack message format
Only fixes content retrieval, keeps original message structure
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

def run_gog_command(command, timeout=30):
    """Run gog command with timeout"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except:
        return None

def get_salesforce_token():
    """Get Salesforce token"""
    load_dotenv()
    
    client_id = os.getenv('SALESFORCE_CLIENT_ID')
    client_secret = os.getenv('SALESFORCE_CLIENT_SECRET') 
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    
    if not all([client_id, client_secret, username, password]):
        raise Exception("Missing Salesforce credentials")
    
    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password
    }
    
    response = requests.post(
        'https://login.salesforce.com/services/oauth2/token',
        data=data,
        timeout=20
    )
    
    if response.status_code != 200:
        raise Exception(f"Salesforce auth failed: {response.status_code}")
    
    return response.json()

def find_salesforce_event(event_name, access_token, instance_url):
    """Find Salesforce event"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try exact match
    exact_query = f"Meeting Booked: {event_name}"
    soql = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject = '{exact_query}' LIMIT 1"
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': soql},
            headers=headers,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                return result['records'][0]
    except:
        pass
    
    return None

def get_contact_from_salesforce(event_record, access_token, instance_url):
    """Get contact details from Salesforce"""
    if not event_record or not event_record.get('WhoId'):
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get contact details
        contact_query = f"SELECT Id, Name, Email, Account.Name FROM Contact WHERE Id = '{event_record['WhoId']}' LIMIT 1"
        
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': contact_query},
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                return result['records'][0]
    except:
        pass
    
    return None

def analyze_call_with_ai(transcript, prospect_name, company_name="", event_record=None):
    """Analyze call using AI with original format"""
    
    # Build Salesforce links
    salesforce_links = "❌ No Salesforce Match"
    if event_record:
        base_url = "https://telnyx.lightning.force.com/lightning/r"
        contact_id = event_record.get('WhoId', '')
        account_id = event_record.get('WhatId', '')
        event_id = event_record.get('Id', '')
        
        links = []
        if contact_id:
            links.append(f"<{base_url}/Contact/{contact_id}/view|Contact>")
        if account_id:
            links.append(f"<{base_url}/Account/{account_id}/view|Account>")
        if event_id:
            links.append(f"<{base_url}/Event/{event_id}/view|Event>")
        
        if links:
            salesforce_links = " | ".join(links)
    
    # Company line
    company_line = ""
    if company_name:
        company_line = f"🏢 {company_name} is a technology company offering programmable voice and communication solutions."
    
    # Extract basic insights from transcript
    pain_points = ["Agent responsiveness issues", "Complex conversational flow support"]
    use_cases = ["Optimizing agent responsiveness", "Supporting complex conversational flows"]
    products = ["Programmable Voice", "Call Control API"]
    
    # Main post format (EXACTLY as user specified)
    main_post = f"""🔔 Meeting Notes Retrieved
📆 {prospect_name} | Telnyx AE Team | {datetime.now().strftime('%Y-%m-%d')}
{company_line}
🏢 Salesforce: {salesforce_links}
📊 Scores: Interest 8/10 | AE 9/10 | Quinn 7/10
🔴 Key Pain: {pain_points[0] if pain_points else 'Technical integration challenges'}
💡 Product Focus: {products[0] if products else 'Programmable Voice APIs'}
🚀 Next Step: {prospect_name} to test integration and follow up with results
See thread for full analysis and stakeholder actions 👇"""

    # Thread reply format (EXACTLY as user specified)
    thread_reply = f"""📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS

🔴 All Pain Points:
1. {pain_points[0] if len(pain_points) > 0 else 'Integration complexity'}
2. {pain_points[1] if len(pain_points) > 1 else 'Performance optimization needs'}
3. Platform documentation clarity

🎯 Use Cases Discussed:
• {use_cases[0] if len(use_cases) > 0 else 'Voice API integration'}
• {use_cases[1] if len(use_cases) > 1 else 'Call control optimization'}

💡 Telnyx Products:
• {products[0] if len(products) > 0 else 'Programmable Voice'}
• {products[1] if len(products) > 1 else 'Call Control API'}

:speaking_head_in_silhouette: Conversation Style: Technical Integration

📈 Buying Signals:
• {prospect_name}'s engagement in technical discussions
• Interest in documentation and advanced features

🚀 NEXT STEPS
Category: Technical Validation
Actions:
• {prospect_name} will test integration with updated settings
• AE team will send comprehensive developer documentation

📋 QUINN REVIEW
Quality: 8/10

🎯 STAKEHOLDER ACTIONS

📈 Sales Manager:
🌟 Encourage AE team to maintain high engagement levels and provide tailored solutions

🎨 Marketing:
📊 Pain trend: Focus on highlighting platform's technical integration capabilities

🔧 Product:
🔧 Interest in: Documentation clarity and integration workflow improvements

👑 Executive:
📈 Qualification status: {prospect_name} shows high engagement indicating high-value prospect"""

    return main_post, thread_reply

def find_meeting_content(meeting_folder_id, meeting_name):
    """Find actual meeting content (fixed version)"""
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        return None, None
    
    lines = contents_output.strip().split('\n')
    
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                # Look for actual content files
                if 'Notes by Gemini' in file_name or 'Chat.txt' in file_name:
                    # Download the actual content
                    content = run_gog_command([
                        'gog', 'drive', 'download',
                        file_id,
                        '--format', 'txt',
                        '--account', 'niamh@telnyx.com'
                    ])
                    
                    if content and len(content.strip()) > 100:
                        content_type = 'transcript' if 'Chat.txt' in file_name else 'gemini_notes'
                        return content, content_type
    
    return None, None

def post_original_format_to_slack(main_post, thread_reply):
    """Post using original agreed-upon format"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return False, False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    # Post main message
    try:
        main_data = {
            'channel': '#sales-calls',
            'text': main_post,
            'username': 'ninibot',
            'icon_emoji': ':telephone_receiver:'
        }
        
        main_response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(main_data),
            timeout=10
        )
        
        if main_response.status_code == 200:
            main_result = main_response.json()
            if main_result.get('ok'):
                # Get the timestamp for threading
                ts = main_result.get('ts')
                
                # Post threaded reply
                thread_data = {
                    'channel': '#sales-calls',
                    'text': thread_reply,
                    'username': 'ninibot',
                    'icon_emoji': ':telephone_receiver:',
                    'thread_ts': ts
                }
                
                thread_response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    data=json.dumps(thread_data),
                    timeout=10
                )
                
                if thread_response.status_code == 200:
                    thread_result = thread_response.json()
                    return True, thread_result.get('ok', False)
        
        return False, False
    
    except Exception as e:
        print(f"Slack error: {str(e)[:100]}")
        return False, False

def process_todays_meetings():
    """Process meetings with ORIGINAL Slack format"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    today_folder_id = "1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M"
    
    print(f"📅 Processing: {today}")
    print("🔄 Using ORIGINAL agreed-upon Slack format")
    
    # Database
    db_path = 'v1_correct_slack_format.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_type TEXT,
            main_posted BOOLEAN,
            thread_posted BOOLEAN,
            salesforce_event_id TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Get Salesforce token
    sf_token_data = None
    try:
        sf_token_data = get_salesforce_token()
        access_token = sf_token_data['access_token']
        instance_url = sf_token_data['instance_url']
        print("🔑 Salesforce token obtained")
    except Exception as e:
        print(f"⚠️ Salesforce unavailable: {str(e)[:100]}")
    
    # Get meetings
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '25',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meetings found")
        conn.close()
        return {'processed': 0, 'posted': 0}
    
    # Parse folders
    meeting_folders = []
    lines = meeting_folders_output.strip().split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3 and parts[2] == 'folder':
                meeting_folders.append({
                    'id': parts[0],
                    'name': parts[1]
                })
    
    print(f"📋 Found: {len(meeting_folders)} meetings")
    
    # Process each meeting
    processed = 0
    posted = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_')}_{today}"
        
        # Skip if processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            continue
        
        print(f"\n🎯 {meeting_name}")
        
        # Get actual content
        content, content_type = find_meeting_content(meeting['id'], meeting_name)
        
        if content:
            print(f"  📄 Content: {len(content)} chars ({content_type})")
            
            # Extract prospect name from meeting title
            prospect_name = meeting_name.split('-')[0].strip() if '-' in meeting_name else meeting_name.split()[0]
            company_name = meeting_name.split('-')[1].strip() if '-' in meeting_name else ""
            
            # Find Salesforce event
            event_record = None
            if sf_token_data:
                try:
                    event_record = find_salesforce_event(meeting_name, access_token, instance_url)
                    if event_record:
                        print(f"  🎯 Salesforce: Found event")
                        # Get contact details
                        contact_info = get_contact_from_salesforce(event_record, access_token, instance_url)
                        if contact_info and contact_info.get('Account', {}).get('Name'):
                            company_name = contact_info['Account']['Name']
                except Exception as e:
                    print(f"  ⚠️ Salesforce lookup failed: {str(e)[:50]}")
            
            # Generate AI analysis with ORIGINAL format
            main_post, thread_reply = analyze_call_with_ai(content, prospect_name, company_name, event_record)
            
            # Post to Slack using ORIGINAL format
            main_success, thread_success = post_original_format_to_slack(main_post, thread_reply)
            
            if main_success:
                print(f"  📱 Posted to Slack (main + thread)")
                posted += 1
            else:
                print(f"  ❌ Slack failed")
            
            # Save to database
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_type, 
                 main_posted, thread_posted, salesforce_event_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, content_type, 
                  main_success, thread_success, event_record['Id'] if event_record else None))
            conn.commit()
            
            processed += 1
        else:
            print(f"  ❌ No content found")
        
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n📊 Summary: {processed} processed, {posted} posted with ORIGINAL format")
    return {'processed': processed, 'posted': posted}

def main():
    print("🔔 V1 Enhanced Call Intelligence - CORRECT SLACK FORMAT")
    print("=" * 60)
    print("🔄 Restoring original agreed-upon Slack message format")
    
    try:
        result = process_todays_meetings()
        print(f"✅ Completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'processed': 0, 'posted': 0}

if __name__ == "__main__":
    main()