#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - CORRECT HIERARCHY PROCESSING
Uses the actual 2026-03-05 folder structure found via search
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
    """Run gog command with timeout and retries"""
    for attempt in range(2):
        try:
            print(f"    🔧 Running: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"    ⚠️ Command failed (attempt {attempt + 1}): {result.stderr}")
                if attempt == 0:
                    time.sleep(2)
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Command timeout (attempt {attempt + 1})")
            if attempt == 0:
                time.sleep(2)
    return None

def get_salesforce_token():
    """Get Salesforce token with proper error handling"""
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
        error_details = response.text if response.text else "No error details"
        raise Exception(f"Salesforce auth failed: {response.status_code} - {error_details}")
    
    return response.json()

def find_meeting_content_in_folder(meeting_folder_id, meeting_name):
    """Find Chat.txt or Gemini notes in a meeting folder"""
    print(f"      📂 Checking: {meeting_name}")
    
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        print(f"      ❌ Could not list folder contents")
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
                
                if 'Chat.txt' in file_name:
                    chat_file = {'id': file_id, 'name': file_name}
                    print(f"        📝 Found transcript: {file_name}")
                elif 'Notes by Gemini' in file_name or 'Gemini' in file_name:
                    gemini_file = {'id': file_id, 'name': file_name}
                    print(f"        🤖 Found Gemini notes: {file_name}")
    
    # Priority: Chat.txt > Gemini notes
    if chat_file:
        return chat_file, 'transcript'
    elif gemini_file:
        return gemini_file, 'gemini'
    else:
        print(f"        ⚠️ No usable content found")
        return None, None

def process_todays_meetings():
    """Process meetings using the actual folder structure"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Processing date: {today}")
    
    # Database setup
    db_path = 'v1_correct_hierarchy.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_type TEXT,
            content_preview TEXT,
            salesforce_status TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'date_folder_hierarchy'
        )
    ''')
    conn.commit()
    
    # Step 1: Find today's date folder by searching
    print(f"🔍 Finding {today} folder...")
    search_output = run_gog_command([
        'gog', 'drive', 'search',
        today,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not search_output:
        print("❌ Could not search for today's folder")
        conn.close()
        return {'processed': 0, 'found': 0}
    
    # Find the date folder (type: folder)
    today_folder_id = None
    lines = search_output.strip().split('\n')
    for line in lines[1:]:  # Skip header
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3 and parts[1] == today and parts[2] == 'folder':
                today_folder_id = parts[0]
                print(f"🎯 Found today's date folder: {today} ({today_folder_id})")
                break
    
    if not today_folder_id:
        print(f"❌ No date folder found for {today}")
        conn.close()
        return {'processed': 0, 'found': 0}
    
    # Step 2: Get meeting folders from today's date folder
    print(f"📋 Getting meeting subfolders from {today}...")
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '20',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meeting folders found in today's date folder")
        conn.close()
        return {'processed': 0, 'found': 0}
    
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
                
                if folder_type == 'folder':  # Only process folders
                    meeting_folders.append({
                        'id': folder_id,
                        'name': folder_name
                    })
                    print(f"      📁 {folder_name}")
    
    print(f"📊 Found {len(meeting_folders)} meeting folders")
    
    # Step 3: Try to get Salesforce token (optional for now)
    sf_token_data = None
    try:
        sf_token_data = get_salesforce_token()
        print("🔑 Salesforce token obtained")
    except Exception as e:
        print(f"⚠️ Salesforce unavailable: {str(e)[:100]}")
    
    # Step 4: Process each meeting folder
    processed = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_')}_{today}"
        
        print(f"\n🎯 Meeting: {meeting_name}")
        
        # Check if already processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            print(f"      ⏭️ SKIPPING: Already processed")
            continue
        
        # Find content in meeting folder
        content_file, content_type = find_meeting_content_in_folder(meeting['id'], meeting_name)
        
        if content_file:
            # Try to get file content
            try:
                content_output = run_gog_command([
                    'gog', 'drive', 'download',
                    content_file['id'],
                    '--format', 'txt',
                    '--account', 'niamh@telnyx.com'
                ])
                
                if content_output and len(content_output.strip()) > 50:
                    content_preview = content_output[:300] + "..." if len(content_output) > 300 else content_output
                    sf_status = "available" if sf_token_data else "unavailable"
                    
                    # Store in database
                    cursor.execute('''
                        INSERT OR IGNORE INTO processed_calls 
                        (dedup_key, meeting_folder_id, event_name, content_type, content_preview, salesforce_status) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (dedup_key, meeting['id'], meeting_name, content_type, content_preview, sf_status))
                    conn.commit()
                    
                    print(f"        ✅ Processed: {content_type} ({len(content_output)} chars)")
                    processed += 1
                    
                    # TODO: Add Salesforce matching when token works
                    if sf_token_data:
                        print(f"        🔍 Would match with Salesforce: {meeting_name[:50]}...")
                
                else:
                    print(f"        ⚠️ Content too short or empty")
            
            except Exception as e:
                print(f"        ❌ Content extraction failed: {str(e)[:100]}")
        
        else:
            print(f"        ❌ No usable content found in folder")
        
        # Small delay
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("📊 CORRECT HIERARCHY PROCESSING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    📁 Meeting folders found: {len(meeting_folders)}")
    print(f"    🎉 Calls processed: {processed}")
    print(f"    🔑 Salesforce: {'Available' if sf_token_data else 'Unavailable'}")
    print(f"    🎯 Database: {db_path}")
    
    return {'processed': processed, 'found': len(meeting_folders)}

def main():
    """Main processing function"""
    print("📁 V1 Enhanced Call Intelligence - CORRECT HIERARCHY")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    try:
        result = process_todays_meetings()
        return result
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'found': 0}

if __name__ == "__main__":
    main()