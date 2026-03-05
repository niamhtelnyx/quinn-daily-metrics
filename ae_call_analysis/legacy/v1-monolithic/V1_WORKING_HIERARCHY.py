#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - WORKING HIERARCHY
Uses direct folder ID (1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M) to process today's meetings
"""

import subprocess
import time
import sqlite3
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

def process_todays_meetings():
    """Process meetings from known folder structure"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    today_folder_id = "1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M"  # Known 2026-03-05 folder
    
    print(f"📅 Processing date: {today}")
    print(f"📁 Using folder ID: {today_folder_id}")
    
    # Database setup
    db_path = 'v1_working_hierarchy.db'
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
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'working_hierarchy'
        )
    ''')
    conn.commit()
    
    # Get all meeting folders from today
    print("📋 Getting meeting folders...")
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '25',  # Get more meetings
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ Could not get meeting folders")
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
                
                if folder_type == 'folder':
                    meeting_folders.append({
                        'id': folder_id,
                        'name': folder_name
                    })
                    print(f"      📁 {folder_name}")
    
    print(f"📊 Found {len(meeting_folders)} meeting folders")
    
    # Process each meeting folder  
    processed = 0
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
                    # Store in database
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO processed_calls 
                        (dedup_key, meeting_folder_id, event_name, content_type, content_length, content_preview) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (dedup_key, meeting['id'], meeting_name, content_type, len(content), content_preview))
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
        time.sleep(0.3)
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("📊 WORKING HIERARCHY PROCESSING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    📁 Meeting folders found: {len(meeting_folders)}")
    print(f"    🎉 Calls processed: {processed}")
    print(f"    ❌ Errors: {errors}")
    print(f"    🎯 Database: {db_path}")
    
    # Show some processed meetings
    if processed > 0:
        print(f"\n📝 Recently processed meetings:")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT event_name, content_type, content_length FROM processed_calls ORDER BY processed_at DESC LIMIT 5')
        for row in cursor.fetchall():
            print(f"      • {row[0][:40]} ({row[1]}, {row[2]} chars)")
        conn.close()
    
    return {'processed': processed, 'found': len(meeting_folders)}

def main():
    """Main processing function"""
    print("📁 V1 Enhanced Call Intelligence - WORKING HIERARCHY")
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
        return {'processed': 0, 'found': 0}

if __name__ == "__main__":
    main()