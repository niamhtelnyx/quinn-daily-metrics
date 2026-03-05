#!/usr/bin/env python3
"""
V1 Production Date System - Safe Deployment Version
Processes Google Drive with new date hierarchy, gracefully handles missing Salesforce config
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

def get_meeting_folders_in_date(date_folder_id, max_meetings=20):
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
        
        parts = line.split('\t')
        if len(parts) >= 3:
            file_id = parts[0]
            file_name = parts[1]
            file_type = parts[2]
            
            if file_type == "file" and "Notes by Gemini" in file_name:
                gemini_files.append({
                    'id': file_id,
                    'name': file_name
                })
    
    return gemini_files

def get_google_drive_content(file_id):
    """Get content from Google Drive file using gog CLI"""
    cmd = [
        'gog', 'drive', 'download',
        file_id,
        '--format', 'txt',
        '--account', 'niamh@telnyx.com'
    ]
    
    # gog download returns file path, we need to read the content
    output = run_gog_command(cmd, timeout=15)
    if not output:
        return None
    
    # Extract file path from output
    try:
        for line in output.split('\n'):
            if line.startswith('path\t'):
                file_path = line.split('\t')[1]
                # Read the downloaded file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Clean up the downloaded file
                import os
                try:
                    os.remove(file_path)
                except:
                    pass
                return content
    except Exception as e:
        log_message(f"Error reading downloaded file: {str(e)}", False)
        return None
    
    return None

def extract_event_name_from_meeting_folder(folder_name):
    """Extract clean event name from meeting folder name"""
    return folder_name.strip()

def check_salesforce_config():
    """Check if Salesforce configuration is available"""
    required_vars = ['SALESFORCE_DOMAIN', 'SALESFORCE_CLIENT_ID', 'SALESFORCE_CLIENT_SECRET']
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.lower() in ['none', 'null', '']:
            log_message(f"⚠️  Salesforce config missing: {var}")
            return False
    
    log_message("✅ Salesforce config available")
    return True

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('v1_date_production.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT UNIQUE,
            dedup_key TEXT,
            event_name TEXT,
            prospect_name TEXT,
            company_name TEXT,
            processed_at TEXT,
            source TEXT,
            slack_posted BOOLEAN,
            ai_analysis TEXT,
            content_length INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def is_already_processed(call_id, dedup_key):
    """Check if call is already processed"""
    conn = sqlite3.connect('v1_date_production.db')
    cursor = conn.cursor()
    
    # Check both call_id and dedup_key for comprehensive deduplication
    cursor.execute(
        'SELECT COUNT(*) FROM processed_calls WHERE call_id = ? OR dedup_key = ?',
        (call_id, dedup_key)
    )
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

def mark_as_processed(call_id, dedup_key, event_name, content_length):
    """Mark call as processed (simplified for safe deployment)"""
    conn = sqlite3.connect('v1_date_production.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (call_id, dedup_key, event_name, prospect_name, company_name, processed_at, source, slack_posted, ai_analysis, content_length)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (call_id, dedup_key, event_name, 'DISCOVERY_MODE', 'DISCOVERY_MODE', 
          datetime.now().isoformat(), 'google_drive_date_hierarchy', False, '{}', content_length))
    
    conn.commit()
    conn.close()

def process_date_hierarchy_safe(main_folder_id="1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY", days_back=1, max_meetings_per_day=15):
    """Safe processing for date hierarchy - discovery mode without external APIs"""
    
    log_message("🚀 V1 DATE PRODUCTION SAFE - Google Drive Discovery Mode")
    log_message(f"📁 Main Meeting Notes folder: {main_folder_id}")
    log_message(f"📅 Processing last {days_back} days, max {max_meetings_per_day} meetings per day")
    
    # Initialize database
    init_database()
    
    # Check Salesforce config but continue without it
    salesforce_available = check_salesforce_config()
    if not salesforce_available:
        log_message("⚠️  Running in DISCOVERY MODE - no Salesforce integration")
    
    # Get recent date folders
    date_folders = get_recent_date_folders(main_folder_id, days_back)
    
    if not date_folders:
        log_message("❌ No recent date folders found")
        return
    
    total_meetings_found = 0
    total_gemini_files = 0
    total_processed = 0
    total_content_chars = 0
    
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
            
            if not gemini_files:
                log_message(f"      ❌ No Gemini files found", False)
                continue
                
            log_message(f"      📝 Found {len(gemini_files)} Gemini files", False)
            total_gemini_files += len(gemini_files)
            
            # Extract event name from meeting folder name
            event_name = extract_event_name_from_meeting_folder(meeting['name'])
            log_message(f"      🎯 Event: '{event_name}'", False)
            
            # Process each Gemini file (usually just one)
            for gemini_file in gemini_files:
                log_message(f"      📄 File: {gemini_file['name'][:50]}{'...' if len(gemini_file['name']) > 50 else ''}", False)
                
                # Create dedup key
                date_str = date_folder['name']
                dedup_key = f"{event_name.lower().strip()}_{date_str}"
                
                # Check if already processed
                if is_already_processed(gemini_file['id'], dedup_key):
                    log_message(f"      ⏭️ SKIPPING: Already processed (dedup: {dedup_key[:60]}...)", False)
                    continue
                
                log_message(f"🆕 Processing: '{event_name}'", False)
                
                # Get Google Drive content
                log_message(f"      🔍 Getting content for doc ID: {gemini_file['id']}", False)
                content = get_google_drive_content(gemini_file['id'])
                
                if not content:
                    log_message(f"      ❌ Failed to get content", False)
                    continue
                
                content_length = len(content)
                total_content_chars += content_length
                log_message(f"      📝 Content length: {content_length} characters", False)
                log_message(f"      ✅ Content retrieved successfully", False)
                
                # Mark as processed (discovery mode)
                mark_as_processed(
                    gemini_file['id'], 
                    dedup_key, 
                    event_name,
                    content_length
                )
                
                total_processed += 1
                log_message(f"      ✅ Discovery processing complete", False)
    
    log_message(f"\n📊 DATE PRODUCTION SAFE SUMMARY:")
    log_message(f"   📅 Date folders processed: {len(date_folders)}")
    log_message(f"   📁 Meeting folders found: {total_meetings_found}")
    log_message(f"   📝 Gemini files found: {total_gemini_files}")
    log_message(f"   🎉 Calls processed: {total_processed}")
    log_message(f"   📄 Total content: {total_content_chars:,} characters")
    log_message(f"   🎯 Deduplication database: v1_date_production.db")

if __name__ == "__main__":
    process_date_hierarchy_safe()