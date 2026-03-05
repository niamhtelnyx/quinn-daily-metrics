#!/usr/bin/env python3
"""
Google Drive operations using gog CLI
"""

import subprocess
import tempfile
import os
import re
from config import *

def run_gog_command(command, timeout=GOG_TIMEOUT):
    """Run gog command with timeout"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except:
        return None

def get_todays_folder_id():
    """Find today's date folder automatically"""
    today_date = get_today_date()
    
    print(f"🔍 Looking for today's folder: {today_date}")
    
    # List folders in main Meeting Notes folder
    output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', MAIN_MEETING_NOTES_FOLDER_ID,
        '--max', '10',
        '--plain',
        '--account', GOG_ACCOUNT
    ])
    
    if not output:
        print(f"❌ Could not list main Meeting Notes folder")
        return None
    
    # Look for folder named exactly today's date
    lines = output.strip().split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                folder_id = parts[0]
                folder_name = parts[1]
                folder_type = parts[2]
                
                if folder_type == 'folder' and folder_name == today_date:
                    print(f"✅ Found today's folder: {folder_name} (ID: {folder_id})")
                    return folder_id
    
    print(f"❌ No folder found for today's date: {today_date}")
    return None

def get_meeting_folders(today_folder_id):
    """Get list of meeting folders for today"""
    print(f"📋 Getting meeting folders...")
    
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', str(MAX_MEETINGS_PER_RUN),
        '--plain',
        '--account', GOG_ACCOUNT
    ])
    
    if not meeting_folders_output:
        return []
    
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
    return meeting_folders

def get_meeting_files(meeting_folder_id):
    """Get list of files in a meeting folder"""
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', str(MAX_FILES_PER_MEETING),
        '--plain',
        '--account', GOG_ACCOUNT
    ])
    
    if not contents_output:
        return []
    
    files = []
    lines = contents_output.strip().split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                files.append({
                    'id': parts[0],
                    'name': parts[1],
                    'type': parts[2] if len(parts) > 2 else 'file'
                })
    
    return files

def download_file_content(file_id):
    """Download file content to string"""
    try:
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download using gog command
        result = subprocess.run([
            'gog', 'drive', 'download', file_id,
            '--format', 'txt',
            '--out', temp_path,
            '--account', GOG_ACCOUNT
        ], capture_output=True, text=True, timeout=GOG_TIMEOUT)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            # Read the actual content
            try:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                
                # Clean up temp file
                os.unlink(temp_path)
                
                # Return content if it's valid (not just a path)
                if len(content) > MIN_CONTENT_LENGTH and not content.startswith('path') and '/Users/' not in content[:100]:
                    return content
                    
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                print(f"File read error: {str(e)[:50]}")
        
        return None
        
    except Exception as e:
        print(f"Download error: {str(e)[:50]}")
        return None

def find_content_files(meeting_folder_id):
    """Find Gemini notes and chat files in meeting folder"""
    files = get_meeting_files(meeting_folder_id)
    
    content_files = {
        'gemini_notes': None,
        'chat_file': None
    }
    
    for file_info in files:
        file_name = file_info['name']
        
        if 'Notes by Gemini' in file_name:
            content_files['gemini_notes'] = file_info
        elif 'Chat.txt' in file_name or 'chat.txt' in file_name:
            content_files['chat_file'] = file_info
    
    return content_files

def extract_meeting_content(meeting_folder_id, meeting_name):
    """Main function to extract content from meeting folder"""
    print(f"      📂 Checking: {meeting_name[:50]}...")
    
    # Find content files
    content_files = find_content_files(meeting_folder_id)
    
    # Try Gemini notes first
    if content_files['gemini_notes']:
        file_info = content_files['gemini_notes']
        print(f"        📝 Found Gemini notes: {file_info['name'][:50]}...")
        
        content = download_file_content(file_info['id'])
        if content:
            print(f"        ✅ Content extracted: {len(content)} chars")
            return content, 'gemini_notes'
        else:
            print(f"        ❌ Content extraction failed")
    
    # Fallback to chat file
    if content_files['chat_file']:
        file_info = content_files['chat_file']
        print(f"        💬 Found chat file: {file_info['name'][:50]}...")
        
        content = download_file_content(file_info['id'])
        if content:
            print(f"        ✅ Chat content extracted: {len(content)} chars")
            return content, 'chat_messages'
    
    print(f"        ⚠️ No usable content found")
    return None, None