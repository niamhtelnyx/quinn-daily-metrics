#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - PROPER HIERARCHY PROCESSING
Processes the correct Meeting Notes/YYYY-MM-DD/Meeting Name/ structure
Priority: Chat.txt (transcript) > Notes by Gemini.gdoc
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

def find_meeting_content(meeting_folder_id, meeting_name):
    """Find transcript or Gemini notes in meeting folder"""
    print(f"      🔍 Checking contents of: {meeting_name}")
    
    # List contents of the meeting folder
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        print(f"      ❌ Could not list contents")
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
                
                # Check for Chat.txt (priority)
                if 'Chat.txt' in file_name:
                    chat_file = {'id': file_id, 'name': file_name}
                    print(f"      📝 Found transcript: {file_name}")
                
                # Check for Gemini notes (fallback)
                elif 'Notes by Gemini' in file_name or 'Gemini' in file_name:
                    gemini_file = {'id': file_id, 'name': file_name}
                    print(f"      🤖 Found Gemini notes: {file_name}")
    
    # Return transcript if available, otherwise Gemini notes
    if chat_file:
        return chat_file, 'transcript'
    elif gemini_file:
        return gemini_file, 'gemini'
    else:
        print(f"      ⚠️ No transcript or Gemini notes found")
        return None, None

def get_file_content(file_id, file_type):
    """Download and extract content from file"""
    print(f"      📥 Downloading {file_type} content...")
    
    try:
        content_output = run_gog_command([
            'gog', 'drive', 'download',
            file_id,
            '--format', 'txt',
            '--account', 'niamh@telnyx.com'
        ])
        
        if content_output and len(content_output.strip()) > 100:
            print(f"      ✅ Content extracted: {len(content_output)} characters")
            return content_output
        else:
            print(f"      ⚠️ Content too short or empty")
            return None
    except Exception as e:
        print(f"      ❌ Content extraction failed: {str(e)[:100]}")
        return None

def process_todays_meetings():
    """Process meetings from today's date folder hierarchy"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Processing date: {today}")
    print(f"🔍 Looking for: Meeting Notes/{today}/[Meeting Folders]/")
    
    # Database setup
    db_path = 'v1_proper_hierarchy.db'
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
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'meeting_hierarchy'
        )
    ''')
    conn.commit()
    
    # Step 1: Find Meeting Notes folder
    print("🔍 Finding Meeting Notes folder...")
    meeting_notes_output = run_gog_command([
        'gog', 'drive', 'search',
        'Meeting Notes',
        '--max', '5',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_notes_output:
        print("❌ Could not find Meeting Notes folder")
        conn.close()
        return
    
    # Find the Meeting Notes folder ID
    meeting_notes_id = None
    lines = meeting_notes_output.strip().split('\n')
    for line in lines[1:]:  # Skip header
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2 and 'Meeting Notes' in parts[1]:
                meeting_notes_id = parts[0]
                print(f"📁 Found Meeting Notes folder: {parts[1]} ({meeting_notes_id})")
                break
    
    if not meeting_notes_id:
        print("❌ Meeting Notes folder not found in search results")
        conn.close()
        return
    
    # Step 2: Find today's date folder
    print(f"📅 Looking for {today} folder in Meeting Notes...")
    date_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_notes_id,
        '--max', '20',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not date_folders_output:
        print("❌ Could not list Meeting Notes contents")
        conn.close()
        return
    
    # Find today's folder
    today_folder_id = None
    lines = date_folders_output.strip().split('\n')
    for line in lines:
        if today in line:
            parts = line.split(None, 1)
            if len(parts) >= 2:
                today_folder_id = parts[0]
                print(f"🎯 Found today's folder: {parts[1]} ({today_folder_id})")
                break
    
    if not today_folder_id:
        print(f"❌ No folder found for {today} in Meeting Notes")
        # Show what folders we did find
        print("📂 Available folders:")
        for line in lines[:5]:
            if line.strip():
                print(f"    {line}")
        conn.close()
        return
    
    # Step 3: Get all meeting folders for today
    print(f"📋 Getting meeting folders from {today}...")
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '15',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meeting folders found for today")
        conn.close()
        return
    
    # Parse meeting folders
    lines = meeting_folders_output.strip().split('\n')
    meeting_folders = []
    for line in lines:
        if line.strip():
            parts = line.split(None, 1)
            if len(parts) >= 2:
                folder_id = parts[0]
                folder_name = parts[1]
                meeting_folders.append({
                    'id': folder_id,
                    'name': folder_name
                })
                print(f"      📁 {folder_name}")
    
    print(f"📊 Found {len(meeting_folders)} meeting folders")
    
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
        content_file, content_type = find_meeting_content(meeting['id'], meeting_name)
        
        if not content_file:
            print(f"      ❌ No usable content found")
            continue
        
        # Get file content
        content = get_file_content(content_file['id'], content_type)
        
        if content:
            # Store in database
            content_preview = content[:200] + "..." if len(content) > 200 else content
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_type, content_preview) 
                VALUES (?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, content_type, content_preview))
            conn.commit()
            
            print(f"      ✅ Processed: {content_type} ({len(content)} chars)")
            processed += 1
        else:
            print(f"      ❌ Content extraction failed")
        
        # Small delay between meetings
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("📊 HIERARCHY PROCESSING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    📁 Meeting folders found: {len(meeting_folders)}")
    print(f"    🎉 Calls processed: {processed}")
    print(f"    🎯 Database: {db_path}")
    
    return {'processed': processed, 'found': len(meeting_folders)}

def main():
    """Main processing function"""
    print("📁 V1 Enhanced Call Intelligence - PROPER HIERARCHY")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    try:
        result = process_todays_meetings()
        return result
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        return {'processed': 0, 'found': 0}

if __name__ == "__main__":
    main()