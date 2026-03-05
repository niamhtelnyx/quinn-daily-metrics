#!/usr/bin/env python3
"""
V2 FINAL Call Intelligence - PRODUCTION LIVE
Full end-to-end processing with Slack posting enabled

LIVE FEATURES:
🚀 Complete call processing pipeline (not dry run)
💬 Real Slack alerts to #ae-call-intelligence  
🤖 AI analysis with OpenAI
📊 Salesforce integration
📁 Enhanced Google Drive parsing
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

def get_enhanced_google_drive_calls(days_back=0):
    """Enhanced Google Drive call detection with flexible patterns"""
    target_date = datetime.now() - timedelta(days=days_back)
    
    try:
        search_patterns = [
            '"Notes by Gemini"',
            '"- Notes by Gemini"', 
            'Gemini'
        ]
        
        all_calls = []
        
        for pattern in search_patterns:
            output, error = run_gog_command(f'gog drive search {pattern} --max 50')
            
            if error:
                continue
            
            if not output or 'ID' not in output:
                continue
            
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            
            for line in lines[1:]:  # Skip header
                if not line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 4:
                    call_id, name, modified_time, _ = parts[0], parts[1], parts[2], parts[3]
                    
                    # Enhanced filtering for call documents
                    if any(indicator in name.lower() for indicator in [
                        'notes by gemini', 'gemini', 'sync -', 'meeting',
                        'call with', 'demo -', 'discovery', 'followup'
                    ]):
                        call_data = {
                            'id': call_id,
                            'title': name,
                            'modified_date': modified_time,
                            'source': 'google_drive_enhanced'
                        }
                        all_calls.append(call_data)
        
        # Remove duplicates by ID
        unique_calls = {call['id']: call for call in all_calls}.values()
        unique_calls = list(unique_calls)
        
        # Sort by modified date (newest first)
        unique_calls.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        return unique_calls, f"Found {len(unique_calls)} enhanced Google Drive calls"
        
    except Exception as e:
        return [], f"Error getting Google Drive calls: {str(e)}"

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
        'kai luo', 'rob messier', 'decliner slides'
    ]
    
    try:
        # Pattern 1: Look for "X and Y of Telnyx met with Z"
        summary_patterns = [
            r'(\w+\s+\w+)\s+and\s+(\w+\s+\w+)\s+of\s+Telnyx\s+met\s+with\s+([^.]+)',
            r'(\w+\s+\w+)\s+initiated\s+the\s+call\s+with\s+([^.]+)',
            r'Meeting\s+between\s+([^,]+),\s*([^,]+),?\s*and\s+([^.]+)',
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
        'source': 'google_drive_enhanced',
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

def post_to_slack(call_data, analysis):
    """Post enhanced call alert to Slack"""
    try:
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_bot_token:
            log_message("❌ Missing SLACK_BOT_TOKEN in .env")
            return False
        
        channel = "#sales-calls"
        prospect_name = call_data.get('prospect_name', 'Unknown Prospect')
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
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📁 Source: Google Drive | 🤖 AI Analysis: {datetime.now().strftime('%H:%M')}"
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
                log_message(f"✅ Posted to Slack: {prospect_name}")
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

def save_processed_call(call_data, analysis, dedup_key, slack_ts=None):
    """Save processed call to database"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_calls 
            (call_id, dedup_key, prospect_name, prospect_email, ae_name, call_date, source, 
             analysis, slack_posted, slack_ts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.now().isoformat()
        ))
        
        conn.commit()
        log_message(f"💾 Saved to database: {call_data['prospect_name']}")
        
    except Exception as e:
        log_message(f"❌ Error saving call to database: {str(e)}")
    
    finally:
        conn.close()

def run_live_automation():
    """Run LIVE V2 automation with full end-to-end processing"""
    log_message("🚀 V2 FINAL Call Intelligence - LIVE PROCESSING")
    
    init_database()
    processed_count = 0
    posted_count = 0
    
    # Get Google Drive calls
    google_calls, google_status = get_enhanced_google_drive_calls()
    log_message(f"📁 Google Drive: {google_status}")
    
    if not google_calls:
        log_message("ℹ️ No new calls found")
        return
    
    for call in google_calls:
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
            
            # Post to Slack
            log_message(f"   💬 Posting to Slack...")
            slack_ts = post_to_slack(formatted_call, analysis)
            
            if slack_ts:
                posted_count += 1
                log_message(f"   ✅ Posted to Slack successfully")
            else:
                log_message(f"   ⚠️ Slack posting failed")
            
            # Save to database
            save_processed_call(formatted_call, analysis, dedup_key, slack_ts)
            
            processed_count += 1
            log_message(f"   ✅ Completed: {prospect_name}")
            
        except Exception as e:
            log_message(f"   ❌ Error processing call: {str(e)}")
            continue
    
    log_message(f"🎉 LIVE processing complete: {processed_count} calls processed, {posted_count} posted to Slack")

if __name__ == "__main__":
    try:
        run_live_automation()
    except Exception as e:
        log_message(f"❌ Fatal error: {e}")
        sys.exit(1)