#!/usr/bin/env python3
"""
SINGLE FOLDER VERSION: Simplified search for new Gemini files
All files are now in one folder: 1fsZIplnjbbMr85dAA2-9ZdTZlX_KiYs3
Much simpler and faster than multi-folder crawling
"""
import sys
sys.path.append('.')
from V1_GOOGLE_DRIVE_ENHANCED import *

def get_recent_gemini_calls_single_folder(folder_id, hours_back=2):
    """SIMPLE FAST: Search single folder only - no subfolder complexity"""
    import time
    start_time = time.time()
    
    try:
        all_calls = []
        
        log_message(f"🔍 SINGLE FOLDER: Searching one folder for Gemini files (last {hours_back}h)")
        log_message(f"📁 Single target folder: {folder_id}")
        
        # Simple folder listing - all files are in this one folder
        search_cmd = f'gog drive ls --parent {folder_id} --max 100 --plain --account niamh@telnyx.com'
        log_message(f"🔧 Running simple folder search: {search_cmd}")
        
        output, error = run_gog_command(search_cmd)
        
        if error:
            log_message(f"⚠️ Folder search error: {error}")
            return [], f"Folder search error: {error}"
        
        if not output or 'ID' not in output:
            log_message(f"📄 No files found in folder")
            return [], "No files found in target folder"
        
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        log_message(f"📄 Found {len(lines)-1} total files in folder")
        
        gemini_files = 0
        recent_files = 0
        
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
                    gemini_files += 1
                    
                    # Check if recent
                    if is_recent_call(modified_time, hours_back):
                        recent_files += 1
                        all_calls.append({
                            'id': file_id,
                            'title': file_name,
                            'modified_date': modified_time,
                            'parent_folder': folder_id
                        })
                        log_message(f"✅ RECENT: {file_name[:50]}...")
                    else:
                        log_message(f"⏭️ OLD: {file_name[:30]}...")
        
        total_time = time.time() - start_time
        log_message(f"📊 SINGLE FOLDER SUMMARY: Found {recent_files} recent calls out of {gemini_files} Gemini files")
        log_message(f"⏱️ Search time: {total_time:.1f}s")
        
        return all_calls, f"Found {recent_files} recent calls (single folder, {total_time:.1f}s)"
        
    except Exception as e:
        log_message(f"💥 Error in single folder search: {str(e)}")
        import traceback
        log_message(f"💥 Traceback: {traceback.format_exc()}")
        return [], f"Single folder search error: {str(e)}"

def run_single_folder_automation():
    """Run automation with single folder Google Drive processing"""
    log_message("🚀 V1 SINGLE FOLDER Call Intelligence - Simplified & Fast")
    
    # Get recent Google Drive calls (single folder version)
    calls, status = get_recent_gemini_calls_single_folder(TARGET_FOLDER_ID, hours_back=2)
    log_message(f"📁 Google Drive: {status}")
    
    if not calls:
        log_message("😴 No calls found")
        return
    
    processed_count = 0
    
    # Get Salesforce token once
    access_token, auth_msg = get_salesforce_token()
    log_message(f"🏢 Salesforce: {auth_msg}")
    
    if not access_token:
        log_message("❌ Cannot proceed without Salesforce auth")
        return
    
    for call in calls:  # Process all found calls
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        # Enhanced deduplication check
        event_name = extract_event_name_from_google_title(title)
        if not event_name:
            log_message(f"❌ Could not extract event name from: {title}")
            continue
            
        dedup_key = create_dedup_key(event_name, title)
        
        if is_event_processed(dedup_key):
            log_message(f"⏭️ SKIPPING: '{event_name}' already processed (dedup: {dedup_key})")
            continue
        
        if is_call_processed(call_id):
            log_message(f"⏭️ SKIPPING: Doc {call_id} already processed")
            continue
            
        log_message(f"🆕 Processing SINGLE FOLDER: {title[:60]}...")
        log_message(f"   🎯 Event name: '{event_name}'")
        
        # Get content
        content, content_msg = get_google_doc_content(call_id)
        if not content:
            log_message(f"   📝 Content: {content_msg}")
            continue
        log_message(f"       ✅ Content retrieved successfully")
        
        # Find Salesforce event
        event_data, event_msg = find_salesforce_event_by_exact_subject(event_name, access_token)
        log_message(f"   🔍 Event: {event_msg}")
        
        if not event_data:
            continue
            
        # Get contact from event
        contact_data, contact_msg = get_contact_from_event(event_data["contact_id"], access_token)
        log_message(f"   👤 Contact: {contact_msg}")
        
        if not contact_data:
            continue
        
        # Run AI analysis
        prospect_name = contact_data["contact_name"]
        company_name = contact_data.get("company_name", "")
        company_website = contact_data.get("company_website", "")
        
        salesforce_ids = {
            'contact_id': contact_data.get('contact_id'),
            'account_id': contact_data.get('account_id'), 
            'event_id': event_data.get('event_id')
        }
        
        ai_analysis = analyze_call_with_ai(content, prospect_name, company_name, company_website, salesforce_ids)
        ai_success = ai_analysis.get("status") == "success"
        log_message(f"   🤖 AI Analysis: {'success' if ai_success else 'failed'}")
        
        # Post to Slack
        slack_success = False
        if ai_analysis.get("main_post"):
            main_post = ai_analysis["main_post"]
            slack_success, slack_msg = post_to_slack_bot_api(main_post)
            log_message(f"   📱 Slack Main: {slack_msg}")
            
            # Post thread reply
            if slack_success and ai_analysis.get("thread_reply"):
                ts_match = re.search(r"ts: ([\d.]+)", slack_msg)
                if ts_match:
                    parent_ts = ts_match.group(1)
                    thread_reply = ai_analysis["thread_reply"]
                    thread_success, thread_msg = post_thread_reply_to_slack(thread_reply, parent_ts)
                    log_message(f"   📱 Slack Thread: {thread_msg}")
        
        # Update Salesforce event
        google_drive_url = f"https://docs.google.com/document/d/{call_id}/edit"
        ai_text = ai_analysis.get("summary", ai_analysis.get("main_post", ""))
        
        sf_success = False
        if event_data["event_id"]:
            try:
                domain = os.getenv("SF_DOMAIN", "telnyx")
                update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_data['event_id']}"
                
                description = f"""Call Analysis - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📁 Google Drive Notes: {google_drive_url}

🤖 AI ANALYSIS:
{ai_text}

✅ Processed by V1 Enhanced Intelligence"""
                
                update_data = {"Description": description}
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)
                
                if response.status_code == 204:
                    sf_success = True
                    log_message(f"   🏢 SF Update: ✅ Updated event")
                else:
                    log_message(f"   🏢 SF Update: ❌ HTTP {response.status_code}")
                
            except Exception as e:
                log_message(f"   🏢 SF Update: ❌ Error: {e}")
        
        # Track in database
        mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success, dedup_key)
        processed_count += 1
        
        prospect_display = f"{prospect_name} ({company_name})" if company_name else prospect_name
        log_message(f"✅ SINGLE FOLDER: {prospect_display} (Slack: {'✅' if slack_success else '❌'}, SF: {'✅' if sf_success else '❌'})")
        log_message(f"✅ ENHANCED: {prospect_name} (Slack: {'✅' if slack_success else '❌'}, SF: {'✅' if sf_success else '❌'}, AI: {'✅' if ai_success else '❌'})")
    
    log_message(f"🎉 V1 SINGLE FOLDER processed {processed_count} calls")

if __name__ == "__main__":
    try:
        run_single_folder_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)