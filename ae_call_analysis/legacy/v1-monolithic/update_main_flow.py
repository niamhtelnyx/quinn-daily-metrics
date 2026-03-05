#!/usr/bin/env python3
"""
Update the main processing flow to use the correct logic functions
"""

# Read the file
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
    lines = f.readlines()

# Find the start and end of the processing section
start_line = None
end_line = None

for i, line in enumerate(lines):
    if "Processing ENHANCED:" in line:
        start_line = i
    elif start_line is not None and ("processed_count += 1" in line or "log_message(f\"✅ ENHANCED:" in line):
        end_line = i + 1
        break

if start_line is None or end_line is None:
    print("❌ Could not find processing section boundaries")
    exit(1)

print(f"Found processing section: lines {start_line+1} to {end_line}")

# Build the new processing section
new_processing = [
    '        log_message(f"🆕 Processing CORRECT: {title[:60]}...")\n',
    '        \n',
    '        # Step 1: Extract event name from Google Drive title\n',
    '        event_name = extract_event_name_from_google_title(title)\n',
    '        if not event_name:\n',
    '            log_message(f"   ❌ Could not extract event name from: {title}")\n',
    '            continue\n',
    '        \n',
    '        log_message(f"   🎯 Event name: \'{event_name}\'")\n',
    '        \n',
    '        # Step 2: Get Google Doc content\n',
    '        content, content_msg = get_google_doc_content(call_id)\n',
    '        if not content:\n',
    '            log_message(f"   📝 Content: {content_msg}")\n',
    '            continue\n',
    '        \n',
    '        # Step 3: Find Salesforce event by exact subject\n',
    '        event_data, event_msg = find_salesforce_event_by_exact_subject(event_name, access_token)\n',
    '        log_message(f"   🔍 Event: {event_msg}")\n',
    '        \n',
    '        if not event_data:\n',
    '            continue\n',
    '            \n',
    '        # Step 4: Get contact from event\n',
    '        contact_data, contact_msg = get_contact_from_event(event_data["contact_id"], access_token)\n',
    '        log_message(f"   👤 Contact: {contact_msg}")\n',
    '        \n',
    '        if not contact_data:\n',
    '            continue\n',
    '        \n',
    '        # Step 5: Run AI analysis\n',
    '        prospect_name = contact_data["contact_name"]\n',
    '        company_name = contact_data.get("company_name", "")\n',
    '        company_website = contact_data.get("company_website", "")\n',
    '        \n',
    '        ai_analysis = analyze_call_with_ai(content, prospect_name, company_name, company_website)\n',
    '        ai_success = ai_analysis.get("status") == "success"\n',
    '        log_message(f"   🤖 AI Analysis: {\'success\' if ai_success else \'failed\'}")\n',
    '        \n',
    '        # Step 6: Post to Slack\n',
    '        slack_success = False\n',
    '        if ai_analysis.get("main_post"):\n',
    '            main_post = ai_analysis["main_post"]\n',
    '            slack_success, slack_msg = post_to_slack_bot_api(main_post)\n',
    '            log_message(f"   📱 Slack Main: {slack_msg}")\n',
    '            \n',
    '            # Post thread reply\n',
    '            if slack_success and ai_analysis.get("thread_reply"):\n',
    '                ts_match = re.search(r"ts: ([\\d.]+)", slack_msg)\n',
    '                if ts_match:\n',
    '                    parent_ts = ts_match.group(1)\n',
    '                    thread_reply = ai_analysis["thread_reply"]\n',
    '                    thread_success, thread_msg = post_thread_reply_to_slack(thread_reply, parent_ts)\n',
    '                    log_message(f"   📱 Slack Thread: {thread_msg}")\n',
    '        \n',
    '        # Step 7: Update Salesforce event with AI analysis\n',
    '        google_drive_url = f"https://docs.google.com/document/d/{call_id}/edit"\n',
    '        ai_text = ai_analysis.get("summary", ai_analysis.get("main_post", ""))\n',
    '        \n',
    '        sf_success = False\n',
    '        if event_data["event_id"]:\n',
    '            try:\n',
    '                domain = os.getenv("SF_DOMAIN", "telnyx")\n',
    '                update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_data[\'event_id\']}")\n',
    '                \n',
    '                description = f"""Call Analysis - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n',
    '\n',
    '📁 Google Drive Notes: {google_drive_url}\n',
    '\n',
    '🤖 AI ANALYSIS:\n',
    '{ai_text}\n',
    '\n',
    '✅ Processed by V1 Enhanced Intelligence"""\n',
    '                \n',
    '                update_data = {"Description": description}\n',
    '                headers = {\n',
    '                    "Authorization": f"Bearer {access_token}",\n',
    '                    "Content-Type": "application/json"\n',
    '                }\n',
    '                \n',
    '                response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)\n',
    '                sf_success = response.status_code == 204\n',
    '                log_message(f"   🏢 SF Update: {\'✅ Updated event\' if sf_success else \'❌ Failed\'}")\n',
    '                \n',
    '            except Exception as e:\n',
    '                log_message(f"   🏢 SF Update: ❌ Error: {e}")\n',
    '        \n',
    '        # Step 8: Track in database\n',
    '        mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success)\n',
    '        processed_count += 1\n',
    '        \n',
    '        prospect_display = f"{prospect_name} ({company_name})" if company_name else prospect_name\n',
    '        log_message(f"✅ CORRECT: {prospect_display} (Slack: {\'✅\' if slack_success else \'❌\'}, SF: {\'✅\' if sf_success else \'❌\'})")\n'
]

# Replace the section
new_lines = lines[:start_line] + new_processing + lines[end_line:]

# Write back
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
    f.writelines(new_lines)

print(f"✅ Updated main processing flow (replaced lines {start_line+1}-{end_line})")
