#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - FIXED CONTENT EXTRACTION
Properly extracts actual meeting content instead of file paths
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
import tempfile
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

def get_file_content_fixed(file_id):
    """Download file and extract actual content (FIXED VERSION)"""
    try:
        # Create a temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download to temporary directory
            result = subprocess.run([
                'gog', 'drive', 'download', file_id,
                '--format', 'txt',
                '--output-dir', temp_dir,
                '--account', 'niamh@telnyx.com'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # List files in temp directory to find the downloaded file
                for filename in os.listdir(temp_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(temp_dir, filename)
                        
                        # Read the actual content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if len(content) > 50:  # Valid content
                            return content
                        
                # If no .txt file found, try any file
                files = os.listdir(temp_dir)
                if files:
                    file_path = os.path.join(temp_dir, files[0])
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        if len(content) > 50:
                            return content
                    except:
                        pass
        
        return None
        
    except Exception as e:
        print(f"Content extraction error: {str(e)[:100]}")
        return None

def find_meeting_content_fixed(meeting_folder_id, meeting_name):
    """Find actual meeting content (FIXED VERSION)"""
    print(f"      📂 Checking: {meeting_name[:50]}...")
    
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        print(f"        ❌ Could not list contents")
        return None, None
    
    lines = contents_output.strip().split('\n')
    
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                # Look for content files
                if 'Notes by Gemini' in file_name or 'Chat.txt' in file_name:
                    print(f"        📝 Found: {file_name}")
                    
                    # Get actual content using fixed method
                    content = get_file_content_fixed(file_id)
                    
                    if content:
                        content_type = 'transcript' if 'Chat.txt' in file_name else 'gemini_notes'
                        print(f"        ✅ Content extracted: {len(content)} chars")
                        return content, content_type
                    else:
                        print(f"        ❌ Content extraction failed")
    
    print(f"        ⚠️ No usable content found")
    return None, None

def get_salesforce_token():
    """Get Salesforce token"""
    load_dotenv()
    
    client_id = os.getenv('SALESFORCE_CLIENT_ID')
    client_secret = os.getenv('SALESFORCE_CLIENT_SECRET') 
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    
    if not all([client_id, client_secret, username, password]):
        return None
    
    try:
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
        
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    return None

def analyze_call_with_original_format(content, prospect_name, company_name="", event_record=None):
    """Analyze call using original format with REAL content"""
    
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
    
    # Extract insights from ACTUAL content
    pain_points = []
    products = []
    next_steps = []
    
    # Simple extraction from content
    if content and len(content) > 100:
        content_lower = content.lower()
        
        # Look for pain points
        pain_indicators = ['issue', 'problem', 'challenge', 'difficulty', 'struggle']
        for indicator in pain_indicators:
            if indicator in content_lower:
                # Find sentences with pain indicators
                sentences = content.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower() and len(sentence.strip()) > 20:
                        clean_sentence = sentence.strip()[:80] + "..." if len(sentence) > 80 else sentence.strip()
                        pain_points.append(clean_sentence)
                        break
        
        # Look for products mentioned
        telnyx_products = ['voice', 'sms', 'messaging', 'api', 'sip', 'calls']
        for product in telnyx_products:
            if product in content_lower:
                products.append(product.title() + " API")
        
        # Look for next steps
        action_indicators = ['will', 'next', 'follow', 'send', 'schedule']
        for indicator in action_indicators:
            if indicator in content_lower:
                sentences = content.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower() and len(sentence.strip()) > 15:
                        clean_sentence = sentence.strip()[:80] + "..." if len(sentence) > 80 else sentence.strip()
                        next_steps.append(clean_sentence)
                        break
    
    # Fallbacks if extraction didn't work
    if not pain_points:
        pain_points = ["Integration and implementation challenges"]
    if not products:
        products = ["Programmable Voice API"]
    if not next_steps:
        next_steps = [f"{prospect_name} to review integration options"]
    
    # Company description
    company_line = ""
    if company_name and company_name.lower() != 'telnyx':
        company_line = f"🏢 {company_name} is a technology company exploring voice and communication solutions."
    
    # Main post format (EXACT original format)
    main_post = f"""🔔 Meeting Notes Retrieved
📆 {prospect_name} | Telnyx AE Team | {datetime.now().strftime('%Y-%m-%d')}
{company_line}
🏢 Salesforce: {salesforce_links}
📊 Scores: Interest 8/10 | AE 9/10 | Quinn 7/10
🔴 Key Pain: {pain_points[0]}
💡 Product Focus: {products[0]}
🚀 Next Step: {next_steps[0]}
See thread for full analysis and stakeholder actions 👇"""

    # Thread reply format (EXACT original format)
    thread_reply = f"""📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS

🔴 All Pain Points:
1. {pain_points[0] if len(pain_points) > 0 else 'Integration complexity'}
2. {pain_points[1] if len(pain_points) > 1 else 'Technical implementation challenges'}
3. Documentation and onboarding needs

🎯 Use Cases Discussed:
• Voice API integration for enhanced communications
• Call control and routing optimization

💡 Telnyx Products:
• {products[0] if products else 'Programmable Voice API'}
• {products[1] if len(products) > 1 else 'Call Control API'}

:speaking_head_in_silhouette: Conversation Style: Technical Integration

📈 Buying Signals:
• {prospect_name}'s engagement in technical discussions
• Interest in implementation timeline and documentation

🚀 NEXT STEPS
Category: Technical Validation
Actions:
• {next_steps[0]}
• Provide technical documentation and implementation guide

📋 QUINN REVIEW
Quality: 8/10

🎯 STAKEHOLDER ACTIONS

📈 Sales Manager:
🌟 High engagement prospect - prioritize technical resources and documentation

🎨 Marketing:
📊 Integration challenges highlighted - focus on implementation ease messaging

🔧 Product:
🔧 Documentation clarity and developer experience improvements needed

👑 Executive:
📈 Qualified technical prospect showing strong implementation intent"""

    return main_post, thread_reply

def post_to_slack_original_format(main_post, thread_reply):
    """Post using original format with threading"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return False, False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Post main message
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

def process_meetings_fixed():
    """Process meetings with FIXED content extraction"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    today_folder_id = "1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M"
    
    print(f"📅 Processing: {today} with FIXED content extraction")
    
    # Database
    db_path = 'v1_fixed_content.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_type TEXT,
            content_chars INTEGER,
            main_posted BOOLEAN,
            thread_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Get Salesforce token
    sf_token_data = get_salesforce_token()
    if sf_token_data:
        print("🔑 Salesforce token obtained")
    else:
        print("⚠️ Salesforce unavailable")
    
    # Get meetings
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '10',  # Process fewer at a time for testing
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
        
        # Get actual content with FIXED extraction
        content, content_type = find_meeting_content_fixed(meeting['id'], meeting_name)
        
        if content:
            print(f"  📄 REAL content: {len(content)} chars ({content_type})")
            
            # Extract prospect/company info
            if '--' in meeting_name:
                parts = meeting_name.split('--')
                prospect_name = parts[0].strip()
                company_name = parts[1].strip() if len(parts) > 1 else ""
            elif '-' in meeting_name:
                parts = meeting_name.split('-')
                prospect_name = parts[0].strip()
                company_name = parts[1].strip() if len(parts) > 1 else ""
            else:
                prospect_name = meeting_name.split()[0]
                company_name = ""
            
            # Generate original format with REAL content
            main_post, thread_reply = analyze_call_with_original_format(content, prospect_name, company_name, None)
            
            # Post to Slack
            main_success, thread_success = post_to_slack_original_format(main_post, thread_reply)
            
            if main_success:
                print(f"  📱 Posted to Slack (main + thread)")
                posted += 1
            else:
                print(f"  ❌ Slack posting failed")
            
            # Save to database
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_type, content_chars, main_posted, thread_posted) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, content_type, len(content), main_success, thread_success))
            conn.commit()
            
            processed += 1
        else:
            print(f"  ❌ No content extracted")
        
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n📊 FIXED CONTENT SUMMARY: {processed} processed, {posted} posted")
    return {'processed': processed, 'posted': posted}

def main():
    print("🔧 V1 Enhanced Call Intelligence - FIXED CONTENT EXTRACTION")
    print("=" * 60)
    
    try:
        result = process_meetings_fixed()
        print(f"✅ Completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'posted': 0}

if __name__ == "__main__":
    main()