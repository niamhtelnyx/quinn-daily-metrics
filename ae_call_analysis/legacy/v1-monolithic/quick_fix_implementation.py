#!/usr/bin/env python3
"""
QUICK IMPLEMENTATION FIX: Simple Google Drive processing without hanging
Focus on getting 6:00 PM run working with minimal complexity
"""

def get_recent_gemini_calls_simple(folder_id, hours_back=2):
    """SIMPLIFIED version that won't hang - focus on main folder only"""
    from datetime import datetime, timedelta
    import json
    
    try:
        log_message(f"🔍 SIMPLE: Searching main folder only to avoid hanging")
        log_message(f"📁 Target folder: {folder_id}")
        
        all_calls = []
        
        # Just search the main folder - avoid subfolder loops that cause hanging
        search_cmd = f'gog drive ls --parent {folder_id} --max 20 --plain --account niamh@telnyx.com'
        log_message(f"🔧 Running: {search_cmd}")
        
        output, error = run_gog_command(search_cmd)
        
        if error:
            log_message(f"⚠️ Error: {error}")
            return [], f"Error: {error}"
        
        if not output or 'ID' not in output:
            log_message(f"📄 No output or invalid format")
            return [], "No valid output"
        
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        log_message(f"📄 Found {len(lines)-1} items in main folder")
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for line in lines[1:]:  # Skip header
            if not line or line.startswith('#'):
                continue
                
            parts = line.split('\t')
            if len(parts) >= 5:
                file_id = parts[0]
                file_name = parts[1]
                file_type = parts[2]
                file_size = parts[3]
                modified_time = parts[4]
                
                # Look for Gemini files
                if 'Notes by Gemini' in file_name and 'folder' not in file_type:
                    log_message(f"📄 Found Gemini file: {file_name[:50]}...")
                    
                    # Simple recent check
                    try:
                        from dateutil import parser
                        mod_time = parser.parse(modified_time)
                        if mod_time > cutoff_time:
                            all_calls.append({
                                'id': file_id,
                                'title': file_name,
                                'modified_date': modified_time,
                                'parent_folder': folder_id
                            })
                            log_message(f"✅ RECENT: {file_name[:40]}...")
                        else:
                            log_message(f"⏭️ TOO OLD: {file_name[:40]}...")
                    except Exception as e:
                        log_message(f"⚠️ Date parsing error: {e}")
                        # If can't parse date, include it anyway
                        all_calls.append({
                            'id': file_id,
                            'title': file_name,
                            'modified_date': modified_time,
                            'parent_folder': folder_id
                        })
        
        log_message(f"📊 SIMPLE SUMMARY: Found {len(all_calls)} recent calls")
        return all_calls, f"Found {len(all_calls)} recent calls (simple mode)"
        
    except Exception as e:
        log_message(f"💥 Error in simple search: {e}")
        import traceback
        log_message(f"💥 Traceback: {traceback.format_exc()}")
        return [], f"Simple search error: {e}"

# Test the simple function
if __name__ == "__main__":
    import sys
    sys.path.append('.')
    from V1_GOOGLE_DRIVE_ENHANCED import log_message, run_gog_command, TARGET_FOLDER_ID
    
    calls, status = get_recent_gemini_calls_simple(TARGET_FOLDER_ID, 2)
    print(f"Result: {status}")
    print(f"Calls: {len(calls)}")
    for call in calls[:3]:
        print(f"- {call['title'][:50]}...")