#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - Date Hierarchy Processing
Processes Google Drive meeting folders organized by date

NEW STRUCTURE:
Meeting Notes/
├── 2026-03-05/                     (Date folders)
│   ├── Meeting Name 1/              (Individual meeting folders)  
│   │   ├── Gemini Notes
│   │   └── Recording (optional)
│   └── Meeting Name 2/
└── 2026-03-04/

CHANGES FROM SINGLE FOLDER:
1. Search date folders (last 2 days) instead of consolidated folder
2. Go 2 levels deep: date → meeting → files
3. Extract event name from meeting folder name
4. Process Gemini notes files within meeting folders
"""

import os
import sys
import sqlite3
import json
import requests
import re
from datetime import datetime, timedelta
import subprocess

def log_message(message, timestamp=True):
    """Log with timestamp"""
    if timestamp:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now}] {message}")
    else:
        print(f"    {message}")

def run_gog_command(cmd, timeout=30):
    """Run gog command with timeout protection"""
    try:
        log_message(f"🔧 Running: {' '.join(cmd)}", False)
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            log_message(f"❌ Command failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        log_message(f"⏰ Command timed out after {timeout}s")
        return None
    except Exception as e:
        log_message(f"❌ Command error: {str(e)}")
        return None

def get_recent_date_folders(main_folder_id, days_back=2):
    """Get date folders for the last N days"""
    log_message(f"📅 Getting date folders for last {days_back} days")
    
    # Get all folders in main directory
    cmd = [
        'gog', 'drive', 'ls', 
        '--parent', main_folder_id,
        '--max', '50',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ]
    
    output = run_gog_command(cmd)
    if not output:
        return []
    
    # Parse and filter for date folders
    date_folders = []
    target_dates = []
    
    # Generate target date strings (YYYY-MM-DD)
    for i in range(days_back):
        date_obj = datetime.now() - timedelta(days=i)
        target_dates.append(date_obj.strftime('%Y-%m-%d'))
    
    log_message(f"🎯 Looking for dates: {', '.join(target_dates)}", False)
    
    for line in output.split('\n')[1:]:  # Skip header
        if not line.strip():
            continue
        
        # Tab-separated format: ID, NAME, TYPE, SIZE, MODIFIED
        parts = line.split('\t')
        if len(parts) >= 3:
            folder_id = parts[0]
            folder_name = parts[1]
            folder_type = parts[2]
            
            # Check if it's a date folder and recent
            if folder_type == "folder" and folder_name in target_dates:
                date_folders.append({
                    'id': folder_id,
                    'name': folder_name,
                    'date': datetime.strptime(folder_name, '%Y-%m-%d')
                })
                log_message(f"📁 Found date folder: {folder_name} ({folder_id})", False)
    
    # Sort by date, newest first
    date_folders.sort(key=lambda x: x['date'], reverse=True)
    log_message(f"✅ Found {len(date_folders)} recent date folders")
    
    return date_folders

def get_meeting_folders_in_date(date_folder_id, max_meetings=50):
    """Get all meeting folders within a date folder"""
    cmd = [
        'gog', 'drive', 'ls',
        '--parent', date_folder_id,
        '--max', str(max_meetings),
        '--plain',
        '--account', 'niamh@telnyx.com'
    ]
    
    output = run_gog_command(cmd)
    if not output:
        return []
    
    meeting_folders = []
    for line in output.split('\n')[1:]:  # Skip header
        if not line.strip():
            continue
        
        # Tab-separated format: ID, NAME, TYPE, SIZE, MODIFIED
        parts = line.split('\t')
        if len(parts) >= 3:
            folder_id = parts[0]
            folder_name = parts[1]
            folder_type = parts[2]
            
            if folder_type == "folder":
                meeting_folders.append({
                    'id': folder_id,
                    'name': folder_name
                })
    
    return meeting_folders

def get_gemini_files_in_meeting(meeting_folder_id):
    """Get Gemini notes files within a meeting folder"""
    cmd = [
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain', 
        '--account', 'niamh@telnyx.com'
    ]
    
    output = run_gog_command(cmd)
    if not output:
        return []
    
    gemini_files = []
    for line in output.split('\n')[1:]:  # Skip header
        if not line.strip():
            continue
        
        # Tab-separated format: ID, NAME, TYPE, SIZE, MODIFIED
        parts = line.split('\t')
        if len(parts) >= 3:
            file_id = parts[0]
            file_name = parts[1]
            file_type = parts[2]
            
            # Look for Gemini notes files
            if file_type == "file" and "Notes by Gemini" in file_name:
                gemini_files.append({
                    'id': file_id,
                    'name': file_name
                })
    
    return gemini_files

def extract_event_name_from_meeting_folder(folder_name):
    """Extract clean event name from meeting folder name
    Examples:
    - 'samir@cenango.com and Eric- 30-minute Meeting' → 'samir@cenango.com and Eric- 30-minute Meeting'
    - 'Telnyx -- Collie' → 'Telnyx -- Collie' 
    """
    return folder_name.strip()

def process_date_hierarchy_meetings(main_folder_id="1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY", days_back=1, max_meetings_per_day=20):
    """Main processing function for date hierarchy structure"""
    
    log_message("🚀 V1 DATE HIERARCHY Call Intelligence - Processing Recent Meetings")
    log_message(f"📁 Main Meeting Notes folder: {main_folder_id}")
    log_message(f"📅 Processing last {days_back} days")
    
    # Get recent date folders
    date_folders = get_recent_date_folders(main_folder_id, days_back)
    
    if not date_folders:
        log_message("❌ No recent date folders found")
        return
    
    total_meetings_found = 0
    total_gemini_files = 0
    
    # Process each date folder
    for date_folder in date_folders:
        log_message(f"\n📅 Processing date: {date_folder['name']}")
        
        # Get meeting folders within this date (limited)
        meeting_folders = get_meeting_folders_in_date(date_folder['id'], max_meetings_per_day)
        log_message(f"   📁 Found {len(meeting_folders)} meeting folders (max {max_meetings_per_day})", False)
        
        total_meetings_found += len(meeting_folders)
        
        # Process each meeting folder
        for meeting in meeting_folders:
            log_message(f"   🎯 Meeting: {meeting['name'][:60]}{'...' if len(meeting['name']) > 60 else ''}", False)
            
            # Get Gemini files in this meeting
            gemini_files = get_gemini_files_in_meeting(meeting['id'])
            
            if gemini_files:
                log_message(f"      📝 Found {len(gemini_files)} Gemini files", False)
                total_gemini_files += len(gemini_files)
                
                # Extract event name from meeting folder name
                event_name = extract_event_name_from_meeting_folder(meeting['name'])
                log_message(f"      🎯 Event: '{event_name}'", False)
                
                # Process each Gemini file (usually just one)
                for gemini_file in gemini_files:
                    log_message(f"      📄 File: {gemini_file['name'][:50]}{'...' if len(gemini_file['name']) > 50 else ''}", False)
                    # TODO: Add actual processing logic here
                    # - Check deduplication
                    # - Extract content
                    # - Find Salesforce event
                    # - Run AI analysis
                    # - Post to Slack
            else:
                log_message(f"      ❌ No Gemini files found", False)
    
    log_message(f"\n📊 DATE HIERARCHY SUMMARY:")
    log_message(f"   📅 Date folders processed: {len(date_folders)}")
    log_message(f"   📁 Meeting folders found: {total_meetings_found}")
    log_message(f"   📝 Gemini files found: {total_gemini_files}")

if __name__ == "__main__":
    process_date_hierarchy_meetings()