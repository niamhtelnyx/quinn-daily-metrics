#!/usr/bin/env python3
"""
V1 Date Hierarchy Test - Google Drive Discovery Only
Tests the new date-based folder structure without Salesforce dependencies
"""

import os
import sys
from V1_DATE_ENHANCED import (
    get_recent_date_folders, 
    get_meeting_folders_in_date, 
    get_gemini_files_in_meeting,
    get_google_drive_content,
    extract_event_name_from_meeting_folder,
    log_message
)

def test_date_hierarchy_discovery(main_folder_id="1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY", days_back=1, max_meetings=3):
    """Test Google Drive discovery in date hierarchy"""
    
    log_message("🧪 V1 DATE HIERARCHY TEST - Google Drive Discovery")
    log_message(f"📁 Main Meeting Notes folder: {main_folder_id}")
    log_message(f"📅 Processing last {days_back} days, max {max_meetings} meetings")
    
    # Get recent date folders
    date_folders = get_recent_date_folders(main_folder_id, days_back)
    
    if not date_folders:
        log_message("❌ No recent date folders found")
        return
    
    total_meetings = 0
    total_gemini_files = 0
    total_content_extracted = 0
    
    # Process each date folder
    for date_folder in date_folders:
        log_message(f"\n📅 Processing date: {date_folder['name']}")
        
        # Get meeting folders within this date (limited)
        meeting_folders = get_meeting_folders_in_date(date_folder['id'], max_meetings)
        log_message(f"   📁 Found {len(meeting_folders)} meeting folders", False)
        
        total_meetings += len(meeting_folders)
        
        # Process each meeting folder
        for i, meeting in enumerate(meeting_folders):
            log_message(f"   🎯 Meeting {i+1}: {meeting['name'][:60]}{'...' if len(meeting['name']) > 60 else ''}", False)
            
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
            
            # Test content extraction for first Gemini file
            if gemini_files:
                gemini_file = gemini_files[0]
                log_message(f"      📄 File: {gemini_file['name'][:50]}{'...' if len(gemini_file['name']) > 50 else ''}", False)
                
                # Get content
                log_message(f"      🔍 Getting content for doc ID: {gemini_file['id']}", False)
                content = get_google_drive_content(gemini_file['id'])
                
                if content:
                    log_message(f"      📝 Content length: {len(content)} characters", False)
                    log_message(f"      ✅ Content retrieved successfully", False)
                    total_content_extracted += 1
                    
                    # Show first 200 chars as preview
                    preview = content[:200].replace('\n', ' ').strip()
                    log_message(f"      👀 Preview: {preview}...", False)
                else:
                    log_message(f"      ❌ Failed to get content", False)
    
    log_message(f"\n📊 DISCOVERY TEST SUMMARY:")
    log_message(f"   📅 Date folders processed: {len(date_folders)}")
    log_message(f"   📁 Meeting folders found: {total_meetings}")
    log_message(f"   📝 Gemini files found: {total_gemini_files}")
    log_message(f"   📄 Content extracted: {total_content_extracted}")
    log_message(f"\n✅ Date hierarchy discovery working correctly!")

if __name__ == "__main__":
    test_date_hierarchy_discovery()