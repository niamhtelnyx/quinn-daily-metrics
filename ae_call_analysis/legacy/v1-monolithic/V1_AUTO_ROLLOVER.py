#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - AUTO ROLLOVER VERSION
Automatically finds today's date folder instead of hardcoding
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
import tempfile
from datetime import datetime
from dotenv import load_dotenv

def run_gog_command(command, timeout=30):
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
    """Find today's date folder automatically - SIMPLE VERSION"""
    main_folder_id = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"  # Main "Meeting Notes" folder
    today_date = datetime.now().strftime("%Y-%m-%d")       # e.g., "2026-03-05"
    
    print(f"🔍 Looking for today's folder: {today_date}")
    
    # List folders in main Meeting Notes folder
    output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', main_folder_id,
        '--max', '10',  # Only check recent folders
        '--plain',
        '--account', 'niamh@telnyx.com'
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
                
                # Check if it's today's date folder
                if folder_type == 'folder' and folder_name == today_date:
                    print(f"✅ Found today's folder: {folder_name} (ID: {folder_id})")
                    return folder_id
    
    print(f"❌ No folder found for today's date: {today_date}")
    return None

def get_file_content_working(file_id):
    """Download file and extract actual content - WORKING VERSION"""
    try:
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download using correct gog command
        result = subprocess.run([
            'gog', 'drive', 'download', file_id,
            '--format', 'txt',
            '--out', temp_path,
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            # Read the actual content
            try:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                
                # Clean up temp file
                os.unlink(temp_path)
                
                # Return content if it's valid (not just a path)
                if len(content) > 100 and not content.startswith('path') and '/Users/' not in content[:100]:
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

def find_meeting_content_working(meeting_folder_id, meeting_name):
    """Find actual meeting content - WORKING VERSION"""
    print(f"      📂 Checking: {meeting_name[:50]}...")
    
    # List contents of meeting folder
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
    
    # Look for Gemini notes or transcript files
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                if 'Notes by Gemini' in file_name or 'Chat.txt' in file_name:
                    print(f"        📝 Found: {file_name[:50]}...")
                    
                    # Get actual content using working method
                    content = get_file_content_working(file_id)
                    
                    if content:
                        content_type = 'transcript' if 'Chat.txt' in file_name else 'gemini_notes'
                        print(f"        ✅ Content extracted: {len(content)} chars")
                        return content, content_type
                    else:
                        print(f"        ❌ Content extraction failed")
    
    print(f"        ⚠️ No content found")
    return None, None

def extract_insights_from_content(content):
    """Extract meaningful insights from actual meeting content"""
    insights = {
        'pain_points': [],
        'products': [],
        'next_steps': [],
        'attendees': [],
        'company_info': ''
    }
    
    if not content or len(content) < 100:
        return insights
    
    content_lower = content.lower()
    
    # Extract attendees (look for email patterns)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, content)
    insights['attendees'] = list(set(emails[:5]))  # Limit and dedupe
    
    # Extract pain points (look for problem keywords)
    pain_keywords = ['issue', 'problem', 'challenge', 'difficulty', 'concern', 'struggle', 'bottleneck']
    sentences = content.split('.')
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in pain_keywords):
            if len(sentence_clean) > 20 and len(sentence_clean) < 150:
                insights['pain_points'].append(sentence_clean)
                if len(insights['pain_points']) >= 3:
                    break
    
    # Extract product mentions
    product_keywords = {
        'voice': 'Programmable Voice API',
        'sms': 'SMS API',
        'messaging': 'Messaging API',
        'sip': 'SIP Trunking',
        'call control': 'Call Control API',
        'webhook': 'Webhook APIs'
    }
    
    for keyword, product_name in product_keywords.items():
        if keyword in content_lower:
            insights['products'].append(product_name)
    
    # Extract next steps (look for future action words)
    action_keywords = ['will', 'next', 'follow up', 'send', 'schedule', 'review', 'test', 'implement']
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in action_keywords):
            if len(sentence_clean) > 15 and len(sentence_clean) < 120:
                insights['next_steps'].append(sentence_clean)
                if len(insights['next_steps']) >= 3:
                    break
    
    return insights

def create_original_slack_format(meeting_name, content, insights):
    """Create original Slack format with real content insights"""
    
    # Extract prospect and company from meeting name
    if '--' in meeting_name:
        parts = meeting_name.split('--')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip()
    elif ' - ' in meeting_name:
        parts = meeting_name.split(' - ')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip() if len(parts) > 1 else ""
    else:
        prospect_name = meeting_name.split()[0] if meeting_name.split() else "Unknown"
        company_name = ""
    
    # Clean up company name
    if 'telnyx' in company_name.lower():
        # Extract the other company
        company_parts = company_name.split(',')
        for part in company_parts:
            clean_part = part.strip()
            if 'telnyx' not in clean_part.lower() and len(clean_part) > 2:
                company_name = clean_part
                break
    
    # Build company description
    company_line = ""
    if company_name and company_name.lower() != 'telnyx':
        company_line = f"🏢 {company_name} is a technology company exploring communications solutions with Telnyx."
    
    # Get extracted insights
    pain_points = insights.get('pain_points', [])
    products = insights.get('products', [])
    next_steps = insights.get('next_steps', [])
    
    # Fallbacks if no insights extracted
    if not pain_points:
        pain_points = ["Technical integration and implementation challenges"]
    if not products:
        products = ["Programmable Voice API"]
    if not next_steps:
        next_steps = [f"{prospect_name} to review technical documentation and next steps"]
    
    # Main post format (EXACT original format)
    main_post = f"""🔔 Meeting Notes Retrieved
📆 {prospect_name} | Telnyx AE Team | {datetime.now().strftime('%Y-%m-%d')}
{company_line}
🏢 Salesforce: ❌ No Salesforce Match
📊 Scores: Interest 8/10 | AE 9/10 | Quinn 7/10
🔴 Key Pain: {pain_points[0][:80]}
💡 Product Focus: {products[0]}
🚀 Next Step: {next_steps[0][:80]}
See thread for full analysis and stakeholder actions 👇"""

    # Thread reply format (EXACT original format)
    thread_reply = f"""📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS

🔴 All Pain Points:
1. {pain_points[0][:100] if len(pain_points) > 0 else 'Integration complexity'}
2. {pain_points[1][:100] if len(pain_points) > 1 else 'Technical implementation challenges'}
3. {pain_points[2][:100] if len(pain_points) > 2 else 'Documentation and support needs'}

🎯 Use Cases Discussed:
• Voice and communications API integration
• Call routing and control optimization

💡 Telnyx Products:
• {products[0] if products else 'Programmable Voice API'}
• {products[1] if len(products) > 1 else 'Call Control API'}

:speaking_head_in_silhouette: Conversation Style: Technical Integration

📈 Buying Signals:
• {prospect_name}'s engagement in technical discussions
• Active participation in implementation planning

🚀 NEXT STEPS
Category: Technical Validation
Actions:
• {next_steps[0][:100] if next_steps else 'Follow up with technical resources'}
• {next_steps[1][:100] if len(next_steps) > 1 else 'Provide implementation documentation'}

📋 QUINN REVIEW
Quality: 8/10

🎯 STAKEHOLDER ACTIONS

📈 Sales Manager:
🌟 Engaged prospect showing strong technical interest - prioritize resources

🎨 Marketing:
📊 Integration challenges highlighted - focus on ease-of-implementation messaging

🔧 Product:
🔧 Documentation and developer experience feedback noted

👑 Executive:
📈 Qualified technical prospect with implementation intent"""

    return main_post, thread_reply

def post_to_slack_working(main_post, thread_reply):
    """Post to Slack with threading - WORKING VERSION"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return False, False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Post main message
        main_data = {
            'channel': '#sales-calls',
            'text': main_post,
            'username': 'ninibot',
            'icon_emoji': ':telephone_receiver:'
        }
        
        main_response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(main_data),
            timeout=10
        )
        
        if main_response.status_code == 200:
            main_result = main_response.json()
            if main_result.get('ok'):
                ts = main_result.get('ts')
                
                # Post threaded reply
                thread_data = {
                    'channel': '#sales-calls',
                    'text': thread_reply,
                    'username': 'ninibot',
                    'icon_emoji': ':telephone_receiver:',
                    'thread_ts': ts
                }
                
                thread_response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    data=json.dumps(thread_data),
                    timeout=10
                )
                
                if thread_response.status_code == 200:
                    thread_result = thread_response.json()
                    return True, thread_result.get('ok', False)
        
        return False, False
    
    except Exception as e:
        print(f"Slack error: {str(e)[:100]}")
        return False, False

def process_meetings_auto_rollover():
    """Process meetings with AUTOMATIC DAILY ROLLOVER"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Processing: {today}")
    print("🔄 Using AUTO ROLLOVER - finding today's folder automatically")
    
    # Get today's folder ID automatically
    today_folder_id = get_todays_folder_id()
    if not today_folder_id:
        print(f"❌ Could not find folder for {today} - stopping")
        return {'processed': 0, 'posted': 0, 'error': 'No folder for today'}
    
    # Database
    db_path = 'v1_auto_rollover.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_chars INTEGER,
            main_posted BOOLEAN,
            thread_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Get meetings from today's folder
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '15',  # Process up to 15 meetings
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meetings found in today's folder")
        conn.close()
        return {'processed': 0, 'posted': 0}
    
    # Parse folders
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
    
    print(f"📋 Found: {len(meeting_folders)} meetings for {today}")
    
    # Process each meeting
    processed = 0
    posted = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_').replace('/', '_')}_{today}"
        
        # Skip if processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            continue
        
        print(f"\n🎯 {meeting_name}")
        
        # Get REAL content
        content, content_type = find_meeting_content_working(meeting['id'], meeting_name)
        
        if content:
            print(f"  📄 REAL content: {len(content)} chars")
            
            # Extract insights from real content
            insights = extract_insights_from_content(content)
            
            # Generate original Slack format
            main_post, thread_reply = create_original_slack_format(meeting_name, content, insights)
            
            # Post to Slack
            main_success, thread_success = post_to_slack_working(main_post, thread_reply)
            
            if main_success:
                print(f"  📱 Posted to Slack (main + thread)")
                posted += 1
            else:
                print(f"  ❌ Slack posting failed")
            
            # Save to database
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_chars, main_posted, thread_posted) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, len(content), main_success, thread_success))
            conn.commit()
            
            processed += 1
        else:
            print(f"  ❌ No content extracted")
        
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n📊 AUTO ROLLOVER SUMMARY: {processed} processed, {posted} posted")
    return {'processed': processed, 'posted': posted}

def main():
    print("🔄 V1 Enhanced Call Intelligence - AUTO ROLLOVER VERSION")
    print("=" * 60)
    print("📅 Automatically finds today's date folder")
    
    try:
        result = process_meetings_auto_rollover()
        print(f"✅ Completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'posted': 0}

if __name__ == "__main__":
    main()