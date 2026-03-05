#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - WORKING HIERARCHY + SLACK POSTING
Combines working folder discovery with Slack posting functionality
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
        print(f"    🔧 Running: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"    ⚠️ Command failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"    ⏰ Command timeout")
        return None

def find_meeting_content(meeting_folder_id, meeting_name):
    """Find Chat.txt or Gemini notes in meeting folder"""
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
    chat_file = None
    gemini_file = None
    
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                # Priority 1: Chat.txt (transcript)
                if 'Chat.txt' in file_name or 'chat.txt' in file_name:
                    chat_file = {'id': file_id, 'name': file_name}
                    print(f"        📝 Found transcript: {file_name}")
                
                # Priority 2: Gemini notes (fallback)
                elif 'Notes by Gemini' in file_name or 'Gemini' in file_name:
                    gemini_file = {'id': file_id, 'name': file_name}
                    print(f"        🤖 Found Gemini notes: {file_name}")
    
    # Return best available content
    if chat_file:
        return chat_file, 'transcript'
    elif gemini_file:
        return gemini_file, 'gemini'
    else:
        print(f"        ⚠️ No transcript or Gemini notes found")
        return None, None

def get_file_content(file_id, file_type):
    """Download file content"""
    print(f"        📥 Downloading {file_type}...")
    
    try:
        content_output = run_gog_command([
            'gog', 'drive', 'download',
            file_id,
            '--format', 'txt',
            '--account', 'niamh@telnyx.com'
        ])
        
        if content_output and len(content_output.strip()) > 50:
            print(f"        ✅ Content: {len(content_output)} characters")
            return content_output
        else:
            print(f"        ⚠️ Content too short")
            return None
    except Exception as e:
        print(f"        ❌ Download failed: {str(e)[:100]}")
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
    """Find Salesforce event by event name"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try exact match first
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
                return result['records'][0], 'exact'
    except:
        pass
    
    return None, None

def post_to_slack(meeting_name, content_type, content_preview, salesforce_event=None):
    """Post meeting to Slack channel"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print(f"        ⚠️ No Slack token - skipping post")
        return False
    
    # Format Slack message
    if salesforce_event:
        message = f"""🔔 *New Meeting Processed - {meeting_name}*

📄 *Content Type*: {content_type}
📝 *Preview*: {content_preview[:150]}...

🔗 *Salesforce*: Event ID `{salesforce_event['Id']}`
"""
    else:
        message = f"""🔔 *New Meeting Processed - {meeting_name}*

📄 *Content Type*: {content_type}
📝 *Preview*: {content_preview[:150]}...

⚠️ *Note*: No matching Salesforce event found
"""
    
    # Post to Slack
    try:
        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'channel': '#sales-calls',
            'text': message,
            'username': 'Call Intelligence Bot',
            'icon_emoji': ':telephone_receiver:'
        }
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(data),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"        📱 POSTED to Slack successfully")
                return True
            else:
                print(f"        ❌ Slack API error: {result.get('error', 'Unknown')}")
                return False
        else:
            print(f"        ❌ Slack HTTP error: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"        ❌ Slack posting failed: {str(e)[:100]}")
        return False

def process_todays_meetings():
    """Process meetings with Slack posting"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    today_folder_id = "1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M"  # Known 2026-03-05 folder
    
    print(f"📅 Processing date: {today}")
    print(f"📁 Using folder ID: {today_folder_id}")
    
    # Database setup
    db_path = 'v1_working_with_slack.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_type TEXT,
            content_length INTEGER,
            content_preview TEXT,
            salesforce_event_id TEXT,
            slack_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'working_with_slack'
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
    
    # Get all meeting folders from today
    print("📋 Getting meeting folders...")
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '25',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ Could not get meeting folders")
        conn.close()
        return {'processed': 0, 'found': 0, 'posted': 0}
    
    # Parse meeting folders
    lines = meeting_folders_output.strip().split('\n')
    meeting_folders = []
    for line in lines:
        if line.strip() and '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                folder_id = parts[0]
                folder_name = parts[1]
                folder_type = parts[2]
                
                if folder_type == 'folder':
                    meeting_folders.append({
                        'id': folder_id,
                        'name': folder_name
                    })
                    print(f"      📁 {folder_name}")
    
    print(f"📊 Found {len(meeting_folders)} meeting folders")
    
    # Process each meeting folder  
    processed = 0
    posted = 0
    errors = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_').replace('/', '_')}_{today}"
        
        print(f"\n🎯 Meeting: {meeting_name}")
        
        # Check if already processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            print(f"      ⏭️ SKIPPING: Already processed")
            continue
        
        try:
            # Find content in meeting folder
            content_file, content_type = find_meeting_content(meeting['id'], meeting_name)
            
            if content_file:
                # Get file content
                content = get_file_content(content_file['id'], content_type)
                
                if content:
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    
                    # Find Salesforce event
                    sf_event = None
                    if sf_token_data:
                        try:
                            sf_event, match_type = find_salesforce_event(
                                meeting_name, access_token, instance_url
                            )
                            if sf_event:
                                print(f"        🎯 Salesforce: Found event ({match_type})")
                        except Exception as e:
                            print(f"        ⚠️ Salesforce lookup failed: {str(e)[:50]}")
                    
                    # Post to Slack
                    slack_success = post_to_slack(meeting_name, content_type, content_preview, sf_event)
                    if slack_success:
                        posted += 1
                    
                    # Store in database
                    cursor.execute('''
                        INSERT OR IGNORE INTO processed_calls 
                        (dedup_key, meeting_folder_id, event_name, content_type, content_length, 
                         content_preview, salesforce_event_id, slack_posted) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (dedup_key, meeting['id'], meeting_name, content_type, len(content), 
                          content_preview, sf_event['Id'] if sf_event else None, slack_success))
                    conn.commit()
                    
                    print(f"        ✅ PROCESSED: {content_type}")
                    processed += 1
                else:
                    print(f"        ❌ Content extraction failed")
                    errors += 1
            else:
                print(f"        ❌ No usable content found")
                errors += 1
        
        except Exception as e:
            print(f"        ❌ Processing error: {str(e)[:100]}")
            errors += 1
        
        # Small delay between meetings
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("📊 WORKING WITH SLACK PROCESSING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    📁 Meeting folders found: {len(meeting_folders)}")
    print(f"    🎉 Calls processed: {processed}")
    print(f"    📱 Slack posts: {posted}")
    print(f"    ❌ Errors: {errors}")
    print(f"    🎯 Database: {db_path}")
    
    return {'processed': processed, 'found': len(meeting_folders), 'posted': posted}

def main():
    """Main processing function"""
    print("📁 V1 Enhanced Call Intelligence - WORKING WITH SLACK")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    try:
        result = process_todays_meetings()
        print(f"\n🏁 Completed at: {datetime.now()}")
        return result
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'found': 0, 'posted': 0}

if __name__ == "__main__":
    main()