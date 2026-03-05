#!/usr/bin/env python3
"""
V2 FINAL Call Intelligence - FOLDER-SPECIFIC SEARCH
Only searches within specified Google Drive folder for Gemini notes

ENHANCED FEATURES:
🚀 Complete call processing pipeline (not dry run)
💬 Real Slack alerts to #sales-calls  
🤖 AI analysis with OpenAI
🔗 Salesforce links in Slack messages ✅
📊 Salesforce integration
📁 FOLDER-SPECIFIC Google Drive parsing ✅
✅ Smart deduplication
"""

import requests
import json
import os
import sqlite3
import sys
import re
from datetime import datetime, timedelta
import subprocess

# SPECIFIC FOLDER ID for call notes
TARGET_FOLDER_ID = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"

def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def run_gog_command(cmd):
    """Run gog CLI command and return output"""
    try:
        env = os.environ.copy()
        env_file_path = '/Users/niamhcollins/clawd/.env.gog'
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.startswith('export '):
                            key = key[7:]
                        env[key] = value.strip('"')
        
        result = subprocess.run(
            f'source /Users/niamhcollins/clawd/.env.gog && {cmd}',
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout, None
        
    except Exception as e:
        return None, f"Error running gog command: {str(e)}"

def get_folder_specific_gemini_calls(folder_id, days_back=0):
    """Get Gemini call notes from specific folder only"""
    target_date = datetime.now() - timedelta(days=days_back)
    
    try:
        all_calls = []
        
        log_message(f"🔍 Searching in specific folder: {folder_id}")
        
        # Step 1: Get all subfolders in target folder
        subfolders_output, error = run_gog_command(f'gog drive ls --parent {folder_id} --max 100')
        
        if error:
            log_message(f"⚠️ Error getting subfolders: {error}")
        
        subfolder_ids = [folder_id]  # Include main folder
        
        if subfolders_output and 'ID' in subfolders_output:
            lines = [line.strip() for line in subfolders_output.split('\n') if line.strip()]
            for line in lines[1:]:  # Skip header
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 3 and 'folder' in parts[2]:
                    subfolder_id = parts[0]
                    subfolder_ids.append(subfolder_id)
        
        log_message(f"📂 Found {len(subfolder_ids)} folders to search (including main folder)")
        
        # Step 2: Search for Gemini notes in each folder
        for i, folder_id in enumerate(subfolder_ids):
            try:
                log_message(f"   🔍 Searching folder {i+1}/{len(subfolder_ids)}")
                
                # Search for Gemini notes in this specific folder
                output, error = run_gog_command(f'gog drive ls --parent {folder_id} --query "name contains \'Gemini\'" --max 50')
                
                if error:
                    continue
                
                if not output or 'ID' not in output:
                    continue
                
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                
                for line in lines[1:]:  # Skip header
                    if not line or line.startswith('#'):
                        continue
                        
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        call_id, name, file_type, size, modified_time = parts[0], parts[1], parts[2], parts[3], parts[4] if len(parts) > 4 else ''
                        
                        # Filter for Gemini call documents
                        if any(indicator in name.lower() for indicator in [
                            'notes by gemini', 'gemini'
                        ]) and 'file' in file_type:
                            call_data = {
                                'id': call_id,
                                'title': name,
                                'modified_date': modified_time,
                                'source': 'folder_specific'
                            }
                            all_calls.append(call_data)
                            
            except Exception as e:
                log_message(f"⚠️ Error searching folder {folder_id}: {str(e)}")
                continue
        
        # Remove duplicates by ID
        unique_calls = {call['id']: call for call in all_calls}.values()
        unique_calls = list(unique_calls)
        
        # Sort by modified date (newest first)
        unique_calls.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        log_message(f"📊 Found {len(unique_calls)} unique Gemini calls in specified folder structure")
        
        return unique_calls, f"Found {len(unique_calls)} calls in folder {TARGET_FOLDER_ID}"
        
    except Exception as e:
        return [], f"Error getting folder-specific calls: {str(e)}"

def get_google_doc_content(doc_id):
    """Get Google Doc content using gog CLI"""
    try:
        output, error = run_gog_command(f'gog docs get {doc_id}')
        
        if error:
            return None, f"Error getting doc content: {error}"
        
        if not output or len(output.strip()) < 50:
            return None, "Document content too short or empty"
        
        return output.strip(), None
        
    except Exception as e:
        return None, f"Error getting doc content: {str(e)}"

def extract_attendees_from_content(content):
    """Extract attendees from document content using multiple patterns"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # List of known Telnyx AEs for identification
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'decliner slides', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda'
    ]
    
    try:
        # Pattern 1: Look for "X and Y of Telnyx met with Z"
        summary_patterns = [
            r'(\w+\s+\w+)\s+and\s+(\w+\s+\w+)\s+of\s+Telnyx\s+met\s+with\s+([^.]+)',
            r'(\w+\s+\w+)\s+initiated\s+the\s+call\s+with\s+([^.]+)',
            r'Meeting\s+between\s+([^,]+),\s*([^,]+),?\s*and\s+([^.]+)',
            r'(\w+)\s+from\s+Telnyx.*?met.*?with\s+([^.]+)',
            r'(\w+)\s+&\s+(\w+)\s+sync',
        ]
        
        for pattern in summary_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches:
                    participants = [p.strip() for p in match]
                    
                    # Identify Telnyx AEs vs prospects
                    for participant in participants:
                        if any(ae.lower() in participant.lower() for ae in telnyx_aes):
                            ae_name = participant.title()
                        else:
                            if prospect_name == 'Unknown Prospect':
                                prospect_name = participant.title()
                    
                    if ae_name != 'Unknown AE' and prospect_name != 'Unknown Prospect':
                        break
        
        # Pattern 2: Extract email addresses 
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # Filter out Telnyx emails to find prospect email
        for email in emails:
            if '@telnyx.com' not in email.lower():
                prospect_email = email
                if prospect_name == 'Unknown Prospect':
                    prospect_name = email.split('@')[0].replace('.', ' ').title()
                break
        
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }
        
    except Exception as e:
        log_message(f"⚠️ Error extracting attendees: {str(e)}")
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }

def format_enhanced_google_drive_call(call_data, content):
    """Enhanced parsing of Google Drive call data"""
    title = call_data.get('title', '')
    
    # Extract attendee information from content
    attendees_info = extract_attendees_from_content(content)
    prospect_name = attendees_info.get('prospect_name', 'Unknown Prospect')
    prospect_email = attendees_info.get('prospect_email', '')
    ae_name = attendees_info.get('ae_name', 'Unknown AE')
    
    return {
        'call_id': call_data['id'],
        'title': title,
        'prospect_name': prospect_name,
        'prospect_email': prospect_email,
        'ae_name': ae_name,
        'call_date': call_data.get('modified_date', ''),
        'source': 'folder_specific',
        'content': content,
        'recording_url': None
    }

def analyze_call_with_ai(content, call_data):
    """Analyze call content using OpenAI"""
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return {"error": "Missing OpenAI API key"}
        
        # Truncate content for API limits
        truncated_content = content[:3000]
        
        prompt = f"""
        Analyze this sales call and provide structured insights:

        CALL DETAILS:
        - Prospect: {call_data.get('prospect_name', 'Unknown')}
        - AE: {call_data.get('ae_name', 'Unknown')}
        - Title: {call_data.get('title', 'Unknown')}

        CALL CONTENT:
        {truncated_content}

        Provide a JSON response with these fields:
        {{
            "summary": "Brief overview of the call",
            "key_points": ["Main discussion points"],
            "next_steps": ["Action items"],
            "pain_points": ["Customer challenges identified"],
            "competitive_mentions": ["Any competitors discussed"],
            "decision_makers": ["Key stakeholders mentioned"],
            "timeline": "Expected timeline for decisions",
            "sentiment": "positive/neutral/negative"
        }}
        """
        
        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': 'You are a sales call analysis expert. Return only valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 800,
            'temperature': 0.3
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return {"error": f"OpenAI API error: {response.status_code}"}
        
        result = response.json()
        
        if 'choices' not in result or not result['choices']:
            return {"error": "No choices in OpenAI response"}
        
        content = result['choices'][0]['message']['content']
        
        # Parse JSON response
        try:
            analysis = json.loads(content)
            return analysis
        except json.JSONDecodeError:
            # Fallback to basic analysis if JSON parsing fails
            return {
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "key_points": ["AI analysis available"],
                "next_steps": ["Follow up with prospect"],
                "sentiment": "neutral"
            }
            
    except Exception as e:
        log_message(f"❌ AI analysis error: {str(e)}")
        return {
            "summary": "Call analysis unavailable",
            "error": str(e),
            "sentiment": "neutral"
        }

def lookup_salesforce_prospect(prospect_name, prospect_email):
    """Lookup prospect in Salesforce and return URL"""
    try:
        # For now, create a search URL that opens Salesforce with the prospect info
        # This can be enhanced with actual API integration later
        
        sf_base_url = "https://telnyx.lightning.force.com"
        
        if prospect_email:
            # Search by email (most accurate)
            search_query = prospect_email
        else:
            # Search by name
            search_query = prospect_name.replace(' ', '%20')
        
        # Create Salesforce search URL
        sf_search_url = f"{sf_base_url}/lightning/o/Contact/list?filterName=00B8K00000HbCdpUAF&search={search_query}"
        
        return {
            'search_url': sf_search_url,
            'display_text': f"🔍 Search: {prospect_name}",
            'found': True  # We'll assume it exists and let SF handle the search
        }
        
    except Exception as e:
        log_message(f"⚠️ Salesforce lookup error: {str(e)}")
        return {
            'search_url': None,
            'display_text': "Salesforce lookup failed",
            'found': False
        }

def post_to_slack(call_data, analysis):
    """Post enhanced call alert to Slack with Salesforce links"""
    try:
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_bot_token:
            log_message("❌ Missing SLACK_BOT_TOKEN in .env")
            return False
        
        channel = "#sales-calls"
        prospect_name = call_data.get('prospect_name', 'Unknown Prospect')
        prospect_email = call_data.get('prospect_email', '')
        ae_name = call_data.get('ae_name', 'Unknown AE')
        call_title = call_data.get('title', 'Call')
        
        # Build Slack message
        summary = analysis.get('summary', 'Call analysis not available')
        key_points = analysis.get('key_points', [])
        next_steps = analysis.get('next_steps', [])
        sentiment = analysis.get('sentiment', 'neutral')
        
        # Sentiment emoji
        sentiment_emoji = {
            'positive': '🟢',
            'negative': '🔴', 
            'neutral': '🟡'
        }.get(sentiment, '🟡')
        
        # Lookup Salesforce info
        sf_lookup = lookup_salesforce_prospect(prospect_name, prospect_email)
        
        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{sentiment_emoji} New Call: {prospect_name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Prospect:* {prospect_name}"},
                    {"type": "mrkdwn", "text": f"*AE:* {ae_name}"},
                    {"type": "mrkdwn", "text": f"*Call:* {call_title}"},
                    {"type": "mrkdwn", "text": f"*Sentiment:* {sentiment.title()} {sentiment_emoji}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n{summary}"
                }
            }
        ]
        
        # Add Salesforce section with links
        if sf_lookup.get('search_url'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔗 Salesforce:* <{sf_lookup['search_url']}|{sf_lookup['display_text']}>"
                }
            })
        
        # Add key points if available
        if key_points:
            points_text = "\n".join([f"• {point}" for point in key_points[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Discussion Points:*\n{points_text}"
                }
            })
        
        # Add next steps if available
        if next_steps:
            steps_text = "\n".join([f"• {step}" for step in next_steps[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Next Steps:*\n{steps_text}"
                }
            })
        
        # Add footer with folder indication
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📁 Source: Specific Drive Folder | 🤖 AI Analysis: {datetime.now().strftime('%H:%M')} | 🔗 <{sf_lookup.get('search_url', '#')}|View in Salesforce>"
                }
            ]
        })
        
        # Post to Slack
        headers = {
            'Authorization': f'Bearer {slack_bot_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'channel': channel,
            'blocks': blocks,
            'text': f"New call: {prospect_name} with {ae_name}"  # Fallback text
        }
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                log_message(f"✅ Posted to Slack with Salesforce links: {prospect_name}")
                return result.get('ts')  # Return timestamp for database
            else:
                log_message(f"❌ Slack API error: {result.get('error')}")
                return False
        else:
            log_message(f"❌ Slack HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        log_message(f"❌ Slack posting error: {str(e)}")
        return False

def init_database():
    """Initialize SQLite database with required tables"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            call_id TEXT,
            dedup_key TEXT UNIQUE,
            prospect_name TEXT,
            prospect_email TEXT,
            ae_name TEXT,
            call_date TEXT,
            source TEXT,
            analysis TEXT,
            slack_posted BOOLEAN DEFAULT FALSE,
            slack_ts TEXT,
            salesforce_url TEXT,
            created_at TEXT,
            UNIQUE(call_id, source)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unmatched_contacts (
            id INTEGER PRIMARY KEY,
            prospect_name TEXT,
            prospect_email TEXT,
            call_id TEXT,
            source TEXT,
            call_date TEXT,
            created_at TEXT,
            notes TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dedup_key ON processed_calls(dedup_key)')
    
    conn.commit()
    conn.close()

def generate_dedup_key(prospect_identifier, call_date):
    """Generate deduplication key from prospect and date"""
    clean_prospect = re.sub(r'[^a-zA-Z0-9@.]', '', prospect_identifier.lower())
    date_only = call_date[:10] if len(call_date) >= 10 else call_date
    return f"{clean_prospect}_{date_only}"

def is_call_duplicate(dedup_key):
    """Check if call already processed using deduplication key"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def save_processed_call(call_data, analysis, dedup_key, slack_ts=None, sf_url=None):
    """Save processed call to database with Salesforce URL"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_calls 
            (call_id, dedup_key, prospect_name, prospect_email, ae_name, call_date, source, 
             analysis, slack_posted, slack_ts, salesforce_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data['call_id'],
            dedup_key,
            call_data['prospect_name'],
            call_data['prospect_email'],
            call_data['ae_name'],
            call_data['call_date'],
            call_data['source'],
            json.dumps(analysis),
            slack_ts is not None,
            slack_ts,
            sf_url,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        log_message(f"💾 Saved to database: {call_data['prospect_name']}")
        
    except Exception as e:
        log_message(f"❌ Error saving call to database: {str(e)}")
    
    finally:
        conn.close()

def run_folder_specific_automation():
    """Run LIVE V2 automation with folder-specific processing"""
    log_message(f"🚀 V2 FOLDER-SPECIFIC Call Intelligence - LIVE PROCESSING")
    log_message(f"📁 Target folder: {TARGET_FOLDER_ID}")
    
    init_database()
    processed_count = 0
    posted_count = 0
    
    # Get Google Drive calls from specific folder only
    folder_calls, folder_status = get_folder_specific_gemini_calls(TARGET_FOLDER_ID)
    log_message(f"📁 Folder Search: {folder_status}")
    
    if not folder_calls:
        log_message("ℹ️ No new calls found in specified folder")
        return
    
    for call in folder_calls:
        try:
            call_id = call.get('id')
            
            log_message(f"🆕 Processing: {call['title']}")
            
            # Get content
            content, content_msg = get_google_doc_content(call_id)
            log_message(f"   📝 Content: {content_msg}")
            
            if not content:
                continue
            
            # Parse call data
            formatted_call = format_enhanced_google_drive_call(call, content)
            prospect_name = formatted_call['prospect_name']
            prospect_email = formatted_call['prospect_email']
            ae_name = formatted_call['ae_name']
            
            log_message(f"   👤 Parsed: {prospect_name} | {ae_name}")
            
            # Check for duplicates
            dedup_key = generate_dedup_key(prospect_email or prospect_name, call.get('modified_date', ''))
            
            if is_call_duplicate(dedup_key):
                log_message(f"   ⚠️ Duplicate found, skipping")
                continue
            
            # AI Analysis
            log_message(f"   🤖 Running AI analysis...")
            analysis = analyze_call_with_ai(content, formatted_call)
            
            # Salesforce lookup
            log_message(f"   🔗 Looking up Salesforce info...")
            sf_lookup = lookup_salesforce_prospect(prospect_name, prospect_email)
            
            # Post to Slack with Salesforce links
            log_message(f"   💬 Posting to Slack with Salesforce links...")
            slack_ts = post_to_slack(formatted_call, analysis)
            
            if slack_ts:
                posted_count += 1
                log_message(f"   ✅ Posted to Slack with Salesforce links")
            else:
                log_message(f"   ⚠️ Slack posting failed")
            
            # Save to database
            save_processed_call(formatted_call, analysis, dedup_key, slack_ts, sf_lookup.get('search_url'))
            
            processed_count += 1
            log_message(f"   ✅ Completed: {prospect_name}")
            
        except Exception as e:
            log_message(f"   ❌ Error processing call: {str(e)}")
            continue
    
    log_message(f"🎉 FOLDER-SPECIFIC processing complete: {processed_count} calls processed, {posted_count} posted to Slack")

if __name__ == "__main__":
    try:
        run_folder_specific_automation()
    except Exception as e:
        log_message(f"❌ Fatal error: {e}")
        sys.exit(1)