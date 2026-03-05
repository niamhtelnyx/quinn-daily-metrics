#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - Date Hierarchy with FULL Pipeline
Same as V1_GOOGLE_DRIVE_ENHANCED.py but with new date-based Google Drive discovery

ONLY CHANGE: Google Drive query step → Date hierarchy instead of consolidated folder
SAME: Salesforce, AI analysis, Slack posting, deduplication, database tracking
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

# NEW: Date hierarchy discovery functions
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

# SAME: All V1 functionality below (unchanged)
def get_salesforce_token():
    """Get Salesforce OAuth2 access token"""
    try:
        client_id = os.getenv('SF_CLIENT_ID')
        client_secret = os.getenv('SF_CLIENT_SECRET')
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        
        if not client_id or not client_secret:
            log_message(f"❌ Salesforce credentials missing")
            return None
            
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=data, timeout=30)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            log_message(f"❌ Salesforce auth failed: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        log_message(f"⏰ Salesforce auth timeout")
        return None
    except Exception as e:
        log_message(f"❌ Salesforce auth error: {str(e)}")
        return None

def normalize_event_name(event_name):
    """Normalize event name by removing special characters and converting to uppercase"""
    import re
    # Remove common special characters and spaces, convert to uppercase
    normalized = event_name.upper()
    special_chars = [' ', '-', '<', '>', '|', '/', '&', ':', '(', ')', '.', ',']
    for char in special_chars:
        normalized = normalized.replace(char, '')
    return normalized

def find_salesforce_event_by_exact_subject(access_token, event_name):
    """Find Salesforce event using normalized subject matching"""
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        instance_url = f"https://{domain}.my.salesforce.com"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Normalize the Google Drive event name
        normalized_event = normalize_event_name(event_name)
        log_message(f"🔧 Normalized search: '{event_name}' → '{normalized_event}'", False)
        
        # Search using the normalized field
        query = f"""
        SELECT Id, Subject, WhoId, StartDateTime, EndDateTime, Subject_Normalized__c
        FROM Event 
        WHERE Subject_Normalized__c LIKE '%{normalized_event}%'
        AND CreatedDate >= YESTERDAY
        ORDER BY CreatedDate DESC 
        LIMIT 5
        """
        
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            if results['records']:
                # Return the best match (first one, most recent)
                best_match = results['records'][0]
                log_message(f"✅ NORMALIZED match found: {best_match['Subject']}", False)
                return best_match
        
        log_message(f"❌ No normalized matches found for: {event_name}", False)
        return None
        
    except requests.exceptions.Timeout:
        log_message(f"⏰ Salesforce event query timeout for: {event_name}", False)
        return None
    except Exception as e:
        log_message(f"❌ Salesforce event query error: {str(e)}", False)
        return None
    except requests.exceptions.Timeout:
        log_message(f"⏰ Salesforce event query timeout for: {event_name}", False)
        return None
    except Exception as e:
        log_message(f"❌ Salesforce event query error: {str(e)}", False)
        return None
    
    if response.status_code == 200:
        results = response.json()
        if results['records']:
            return results['records'][0]
    
    return None

def get_contact_from_event(access_token, event_record):
    """Get contact details from event WhoId"""
    if not event_record.get('WhoId'):
        return None
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        instance_url = f"https://{domain}.my.salesforce.com"
        
        who_id = event_record['WhoId']
        
        query = f"""
        SELECT Id, Name, Email, AccountId, Account.Name
        FROM Contact 
        WHERE Id = '{who_id}'
        LIMIT 1
        """
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': query},
            headers=headers,
            timeout=30
        )
    except requests.exceptions.Timeout:
        log_message(f"⏰ Salesforce contact query timeout for: {who_id}", False)
        return None
    except Exception as e:
        log_message(f"❌ Salesforce contact query error: {str(e)}", False)
        return None
    
    if response.status_code == 200:
        results = response.json()
        if results['records']:
            return results['records'][0]
    
    return None

def analyze_call_with_ai(content, prospect_name, company_name):
    """Analyze call content with AI - return None on errors to prevent Slack posting"""
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return {
                "status": "error",
                "main_post": None,
                "thread_reply": None,
                "summary": "❌ OpenAI API key missing"
            }

        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }

        prompt = f"""
Analyze this sales call transcript for a call with {prospect_name} from {company_name}.

Create a comprehensive analysis that includes:
1. Key discussion points and business context
2. Prospect needs, pain points, and current solutions
3. Technical requirements discussed
4. Timeline, budget, and decision-making process
5. Next steps and follow-up actions
6. Deal qualification and sales insights

Return your response as JSON with these fields:
- main_post: A detailed Slack post (2-3 paragraphs) for the sales team with key insights
- thread_reply: A bullet-point summary of action items and next steps
- summary: A one-sentence summary of the call outcome

Content:
{content}
"""

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a sales call analyst. Provide detailed, actionable insights from sales conversations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            try:
                analysis = json.loads(content)
                return {
                    "status": "success",
                    "main_post": analysis.get("main_post"),
                    "thread_reply": analysis.get("thread_reply"), 
                    "summary": analysis.get("summary"),
                    "full_analysis": analysis
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "main_post": None,
                    "thread_reply": None,
                    "summary": "❌ AI returned invalid JSON"
                }
        else:
            return {
                "status": "error",
                "main_post": None,  # Don't post errors to Slack
                "thread_reply": None,
                "summary": f"❌ OpenAI API error: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "main_post": None,  # Don't post errors to Slack
            "thread_reply": None,
            "summary": f"❌ AI analysis failed: {str(e)}"
        }

def post_to_slack_bot_api(message):
    """Post message to Slack using Bot API"""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')  # Fixed: was SLACK_TOKEN
        if not slack_token:
            return False, "❌ No Slack token"

        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'channel': '#sales-calls',
            'text': message,
            'username': 'ninibot',
            'icon_emoji': ':robot_face:'
        }

        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                ts = data.get('ts')
                return True, f"✅ Posted to Slack (ts: {ts})"
            else:
                error = data.get('error', 'Unknown error')
                return False, f"❌ Slack API error: {error}"
        else:
            return False, f"❌ HTTP {response.status_code}"

    except Exception as e:
        return False, f"❌ Exception: {str(e)}"

def post_slack_thread_reply(parent_ts, message):
    """Post threaded reply to Slack message"""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')  # Fixed: was SLACK_TOKEN
        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'channel': '#sales-calls',
            'text': message,
            'thread_ts': parent_ts,
            'username': 'ninibot',
            'icon_emoji': ':memo:'
        }

        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return True, "✅ Thread reply posted"
            else:
                return False, f"❌ Thread error: {data.get('error')}"
        else:
            return False, f"❌ Thread HTTP {response.status_code}"

    except Exception as e:
        return False, f"❌ Thread exception: {str(e)}"

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('v1_date_full.db')
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
            salesforce_event_id TEXT,
            content_length INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def is_already_processed(call_id, dedup_key):
    """Check if call is already processed"""
    conn = sqlite3.connect('v1_date_full.db')
    cursor = conn.cursor()
    
    # Check both call_id and dedup_key for comprehensive deduplication
    cursor.execute(
        'SELECT COUNT(*) FROM processed_calls WHERE call_id = ? OR dedup_key = ?',
        (call_id, dedup_key)
    )
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

def mark_as_processed(call_id, dedup_key, event_name, prospect_name, company_name, slack_posted, ai_analysis, salesforce_event_id=None, content_length=0):
    """Mark call as processed"""
    conn = sqlite3.connect('v1_date_full.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (call_id, dedup_key, event_name, prospect_name, company_name, processed_at, source, slack_posted, ai_analysis, salesforce_event_id, content_length)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (call_id, dedup_key, event_name, prospect_name, company_name, 
          datetime.now().isoformat(), 'google_drive_date_hierarchy_full', slack_posted, json.dumps(ai_analysis), salesforce_event_id, content_length))
    
    conn.commit()
    conn.close()

def process_date_hierarchy_full(main_folder_id="1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY", days_back=1, max_meetings_per_day=15):
    """FULL processing pipeline with new date hierarchy discovery"""
    
    log_message("🚀 V1 DATE FULL - Complete Pipeline with Date Hierarchy")
    log_message(f"📁 Main Meeting Notes folder: {main_folder_id}")
    log_message(f"📅 Processing last {days_back} days, max {max_meetings_per_day} meetings per day")
    
    # Initialize database
    init_database()
    
    # Get Salesforce access
    access_token = get_salesforce_token()
    if access_token:
        log_message("🏢 Salesforce: ✅ Authenticated")
    else:
        log_message("🏢 Salesforce: ❌ Authentication failed")
        return
    
    # NEW: Get recent date folders (changed from consolidated folder)
    date_folders = get_recent_date_folders(main_folder_id, days_back)
    
    if not date_folders:
        log_message("❌ No recent date folders found")
        return
    
    total_meetings_found = 0
    total_gemini_files = 0
    total_processed = 0
    total_slack_posted = 0
    
    # Process each date folder
    for date_folder in date_folders:
        log_message(f"\n📅 Processing date: {date_folder['name']}")
        
        # NEW: Get meeting folders within this date (changed from direct file search)
        meeting_folders = get_meeting_folders_in_date(date_folder['id'], max_meetings_per_day)
        log_message(f"   📁 Found {len(meeting_folders)} meeting folders (max {max_meetings_per_day})", False)
        
        total_meetings_found += len(meeting_folders)
        
        # Process each meeting folder
        for meeting in meeting_folders:
            log_message(f"   🎯 Meeting: {meeting['name'][:60]}{'...' if len(meeting['name']) > 60 else ''}", False)
            
            # NEW: Get Gemini files in this meeting (changed from direct file processing)
            gemini_files = get_gemini_files_in_meeting(meeting['id'])
            
            if not gemini_files:
                log_message(f"      ❌ No Gemini files found", False)
                continue
                
            log_message(f"      📝 Found {len(gemini_files)} Gemini files", False)
            total_gemini_files += len(gemini_files)
            
            # NEW: Extract event name from meeting folder name (changed from file name parsing)
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
                
                # SAME: Find Salesforce event (unchanged)
                event_record = find_salesforce_event_by_exact_subject(access_token, event_name)
                
                if not event_record:
                    log_message(f"      🔍 Event: ❌ No event found: Meeting Booked: {event_name}", False)
                    continue
                
                log_message(f"      🔍 Event: ✅ Found Salesforce event", False)
                
                # SAME: Get contact from event (unchanged)
                contact = get_contact_from_event(access_token, event_record)
                if not contact:
                    log_message(f"      👤 Contact: ❌ No contact found", False)
                    continue
                
                prospect_name = contact.get('Name', 'Unknown')
                company_name = contact.get('Account', {}).get('Name', 'Unknown Company')
                log_message(f"      👤 Contact: {prospect_name} @ {company_name}", False)
                
                # NEW: Get Google Drive content (changed method, same functionality)
                log_message(f"      🔍 Getting content for doc ID: {gemini_file['id']}", False)
                content = get_google_drive_content(gemini_file['id'])
                
                if not content:
                    log_message(f"      ❌ Failed to get content", False)
                    continue
                
                content_length = len(content)
                log_message(f"      📝 Content length: {content_length} characters", False)
                log_message(f"      ✅ Content retrieved successfully", False)
                
                # SAME: AI Analysis (unchanged)
                log_message(f"      🤖 Running AI analysis...", False)
                ai_analysis = analyze_call_with_ai(content, prospect_name, company_name)
                
                ai_success = ai_analysis.get("status") == "success"
                log_message(f"      🤖 AI Analysis: {'success' if ai_success else 'failed'}", False)
                
                # SAME: Post to Slack (unchanged)
                slack_success = False
                if ai_analysis.get("main_post"):
                    main_post = ai_analysis["main_post"]
                    slack_success, slack_msg = post_to_slack_bot_api(main_post)
                    log_message(f"      📱 Slack Main: {slack_msg}", False)
                    
                    # Post thread reply
                    if slack_success and ai_analysis.get("thread_reply"):
                        ts_match = re.search(r"ts: ([\d.]+)", slack_msg)
                        if ts_match:
                            parent_ts = ts_match.group(1)
                            thread_reply = ai_analysis["thread_reply"]
                            thread_success, thread_msg = post_slack_thread_reply(parent_ts, thread_reply)
                            log_message(f"      📝 Slack Thread: {thread_msg}", False)
                else:
                    log_message(f"      📱 Slack: ⏭️ Skipped (no main_post)", False)
                
                if slack_success:
                    total_slack_posted += 1
                
                # Mark as processed
                mark_as_processed(
                    gemini_file['id'], 
                    dedup_key, 
                    event_name, 
                    prospect_name, 
                    company_name, 
                    slack_success, 
                    ai_analysis,
                    event_record.get('Id'),
                    content_length
                )
                
                total_processed += 1
                log_message(f"      ✅ Processing complete", False)
    
    log_message(f"\n📊 DATE FULL PIPELINE SUMMARY:")
    log_message(f"   📅 Date folders processed: {len(date_folders)}")
    log_message(f"   📁 Meeting folders found: {total_meetings_found}")
    log_message(f"   📝 Gemini files found: {total_gemini_files}")
    log_message(f"   🎉 Calls processed: {total_processed}")
    log_message(f"   📱 Slack posts: {total_slack_posted}")
    log_message(f"   🎯 Database: v1_date_full.db")

if __name__ == "__main__":
    process_date_hierarchy_full()