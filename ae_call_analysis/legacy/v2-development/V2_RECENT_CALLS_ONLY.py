#!/usr/bin/env python3
"""
V2 RECENT CALLS ONLY - Enhanced Call Intelligence  
Only processes NEW calls created in the last 2 hours
Avoids reprocessing old calls every 30 minutes

ENHANCED FEATURES:
🚀 Recent calls only (last 2 hours)
💬 Real Slack alerts to #sales-calls  
🤖 AI analysis with OpenAI
🔗 Salesforce links + verification
📊 Salesforce API integration
📁 FOLDER-SPECIFIC Google Drive parsing
✅ Smart deduplication
🛡️ Quality control with Salesforce verification
"""

import requests
import json
import os
import sqlite3
import sys
import re
from datetime import datetime, timedelta
import subprocess
from dateutil import parser

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

def is_recent_call(modified_time_str, hours_back=2):
    """Check if call was modified within the last N hours"""
    try:
        if not modified_time_str:
            return False
            
        # Parse the modified time
        modified_time = parser.parse(modified_time_str)
        
        # Get cutoff time (N hours ago)
        cutoff_time = datetime.now(modified_time.tzinfo) - timedelta(hours=hours_back)
        
        is_recent = modified_time >= cutoff_time
        
        # Debug logging
        if is_recent:
            log_message(f"      ⏰ RECENT: Modified {modified_time.strftime('%Y-%m-%d %H:%M')} (within {hours_back}h)")
        
        return is_recent
        
    except Exception as e:
        log_message(f"      ⚠️ Date parsing error for '{modified_time_str}': {str(e)}")
        return False

def get_recent_gemini_calls(folder_id, hours_back=2):
    """Get ONLY recent Gemini call notes (last N hours)"""
    try:
        all_calls = []
        total_found = 0
        recent_count = 0
        
        log_message(f"🔍 Searching for calls modified in last {hours_back} hours")
        log_message(f"📁 Target folder: {folder_id}")
        
        # Step 1: Get all subfolders in target folder
        subfolders_output, error = run_gog_command(f'gog drive ls --parent {folder_id} --max 100 --plain')
        
        if error:
            log_message(f"⚠️ Error getting subfolders: {error}")
            return [], f"Error getting subfolders: {error}"
        
        subfolder_ids = [folder_id]  # Include main folder
        
        if subfolders_output and 'ID' in subfolders_output:
            lines = [line.strip() for line in subfolders_output.split('\n') if line.strip()]
            for line in lines[1:]:  # Skip header
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    folder_id_part = parts[0]
                    folder_name = parts[1]
                    folder_type = parts[2]
                    
                    if 'folder' in folder_type:
                        subfolder_ids.append(folder_id_part)
        
        log_message(f"📂 Searching {len(subfolder_ids)} folders...")
        
        # Step 2: Search for RECENT Gemini notes in each folder
        for i, current_folder_id in enumerate(subfolder_ids):
            try:
                # Search for Gemini notes in this specific folder
                output, error = run_gog_command(f'gog drive ls --parent {current_folder_id} --query "name contains \'Gemini\'" --max 50 --plain')
                
                if error or not output or 'ID' not in output:
                    continue
                
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                
                for line in lines[1:]:  # Skip header
                    if not line or line.startswith('#'):
                        continue
                        
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        call_id = parts[0]
                        name = parts[1]
                        file_type = parts[2]
                        size = parts[3]
                        modified_time = parts[4] if len(parts) > 4 else ''
                        
                        # Filter for Gemini call documents
                        if any(indicator in name.lower() for indicator in [
                            'notes by gemini', 'gemini'
                        ]) and 'file' in file_type:
                            total_found += 1
                            
                            # 🎯 KEY FILTER: Only include recent calls
                            if is_recent_call(modified_time, hours_back):
                                call_data = {
                                    'id': call_id,
                                    'title': name,
                                    'modified_date': modified_time,
                                    'source': 'recent_folder_calls'
                                }
                                all_calls.append(call_data)
                                recent_count += 1
                                log_message(f"      ✅ RECENT: {name[:60]}...")
                            
            except Exception as e:
                log_message(f"⚠️ Error searching folder {current_folder_id}: {str(e)}")
                continue
        
        # Remove duplicates by ID
        unique_calls = {call['id']: call for call in all_calls}.values()
        unique_calls = list(unique_calls)
        
        # Sort by modified date (newest first)
        unique_calls.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        log_message(f"📊 SUMMARY: Found {total_found} total Gemini calls, {len(unique_calls)} are recent (last {hours_back}h)")
        
        return unique_calls, f"Found {len(unique_calls)} recent calls (last {hours_back}h) out of {total_found} total"
        
    except Exception as e:
        return [], f"Error getting recent calls: {str(e)}"

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

def get_google_doc_content(doc_id):
    """Get Google Doc content using gog CLI"""
    try:
        log_message(f"      🔍 Getting content for doc ID: {doc_id}")
        output, error = run_gog_command(f'gog docs cat {doc_id}')
        
        if error:
            log_message(f"      ❌ gog command error: {error}")
            return None, f"Error getting doc content: {error}"
        
        if not output:
            log_message(f"      ❌ No output from gog command")
            return None, "No output from gog command"
            
        content_length = len(output.strip())
        log_message(f"      📝 Content length: {content_length} characters")
        
        if content_length < 50:
            log_message(f"      ⚠️ Content too short ({content_length} chars)")
            return None, "Document content too short or empty"
        
        log_message(f"      ✅ Content retrieved successfully")
        return output.strip(), None
        
    except Exception as e:
        log_message(f"      ❌ Exception: {str(e)}")
        return None, f"Error getting doc content: {str(e)}"

def extract_attendees_from_content(content, title=""):
    """Enhanced attendee extraction from document content and title"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # Enhanced list of known Telnyx AEs
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian'
    ]
    
    try:
        # PRIORITY 1: Extract from title (most reliable)
        title_patterns = [
            r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx',  # "Company <> Telnyx"
            r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)',      # "Telnyx <> Company"  
            r'^Copy of ([^/]+)\s*/\s*Telnyx',            # "Company / Telnyx"
            r'^Copy of (.+?)\s+and\s+\w+:',              # "Company and Person:"
            r'^Copy of (.+?)\s+-\s+.*Notes by Gemini',   # Extract before date
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                potential_company = match.group(1).strip()
                # Clean up company name
                potential_company = re.sub(r'\s*(meeting|call|sync|demo)\s*$', '', potential_company, flags=re.IGNORECASE)
                potential_company = re.sub(r'\s*(intro|recurring)\s*', ' ', potential_company, flags=re.IGNORECASE).strip()
                if len(potential_company) > 2 and 'telnyx' not in potential_company.lower():
                    prospect_name = potential_company.title()
                    break
        
        # PRIORITY 2: Extract people mentioned in content (for AE identification)
        people_pattern = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b'  # More precise: FirstName LastName
        people_mentioned = re.findall(people_pattern, content)
        
        # Remove duplicates and filter obvious non-names
        people_mentioned = list(set([p for p in people_mentioned if 
            len(p.split()) == 2 and  # Exactly 2 words
            not any(x in p.lower() for x in ['telnyx', 'meeting', 'call', 'notes', 'summary', 'details'])
        ]))
        
        # Identify Telnyx AE from people mentioned
        for person in people_mentioned:
            person_lower = person.lower()
            # Check against known AEs
            if any(ae.lower() in person_lower for ae in telnyx_aes):
                ae_name = person.title()
                break
            # Check for partial matches on first names of known AEs
            first_name = person.split()[0].lower()
            if first_name in [ae.split()[0] for ae in telnyx_aes if ' ' in ae]:
                ae_name = person.title()
                break
        
        # PRIORITY 3: Extract email addresses 
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # Filter out Telnyx emails to find prospect email
        for email in emails:
            if '@telnyx.com' not in email.lower():
                prospect_email = email
                # Use email domain as company if still unknown
                if prospect_name == 'Unknown Prospect':
                    domain = email.split('@')[1].split('.')[0]
                    prospect_name = domain.title()
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
    
    # Extract attendee information from content AND title
    attendees_info = extract_attendees_from_content(content, title)
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
        'source': 'recent_folder_calls',
        'content': content,
        'recording_url': None
    }

def validate_call_quality(call_data, analysis):
    """Enhanced quality validation with Salesforce verification"""
    prospect_name = call_data.get('prospect_name', '').strip()
    prospect_email = call_data.get('prospect_email', '').strip()
    ae_name = call_data.get('ae_name', '').strip()
    content = call_data.get('content', '') or ''
    
    # QUALITY GATES - Block obvious garbage
    if prospect_name in ['Unknown Prospect', 'Unknown', '']:
        return False, "Unknown prospect name"
    
    if ae_name in ['Unknown AE', 'Unknown', '']:
        return False, "Unknown AE name"
    
    if not content or len(content.strip()) < 100:
        return False, "No meaningful content extracted"
    
    summary = analysis.get('summary', '')
    if any(indicator in summary.lower() for indicator in [
        'json', '```json', 'insufficient conversation', 'supported language',
        'no summary was produced', 'error', 'failed'
    ]):
        return False, "AI analysis contains error messages"
    
    key_points = analysis.get('key_points', [])
    next_steps = analysis.get('next_steps', [])
    
    if len(key_points) == 0 and len(next_steps) == 0:
        return False, "Analysis contains no actionable content"
    
    if any(indicator in prospect_name.lower() for indicator in [
        'copy of', 'notes by gemini', 'meeting -', 'porting', 'sync'
    ]):
        return False, "Prospect name looks like parsing error"
    
    if len(prospect_name) < 3 or len(ae_name) < 3:
        return False, "Names too short to be meaningful"
    
    if len(summary.strip()) < 20:
        return False, "Summary too short to be meaningful"
    
    # 🎯 SALESFORCE VERIFICATION - Only post if prospect exists in Salesforce
    try:
        from salesforce_integration import validate_salesforce_prospect
        is_in_sf, sf_reason = validate_salesforce_prospect(prospect_name, prospect_email)
        
        if not is_in_sf:
            return False, f"Prospect not found in Salesforce: {sf_reason}"
        
        log_message(f"      ✅ Salesforce verified: {sf_reason}")
        return True, f"Quality validation passed + Salesforce verified: {sf_reason}"
        
    except Exception as e:
        # Fallback: if Salesforce lookup fails, allow high-quality calls through
        log_message(f"      ⚠️ Salesforce lookup failed: {str(e)}, allowing based on content quality")
        return True, "Quality validation passed (Salesforce lookup unavailable)"

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
    """Real Salesforce lookup with actual record verification"""
    try:
        from salesforce_integration import search_salesforce_prospect
        
        # Actually search Salesforce API
        result, error = search_salesforce_prospect(prospect_name, prospect_email)
        
        if result and result.get('found'):
            # Found actual Salesforce record
            contact_name = result.get('contact_name', prospect_name)
            account_name = result.get('account_name', '')
            record_url = result.get('record_url', '')
            
            display_text = f"📋 {contact_name}"
            if account_name:
                display_text += f" at {account_name}"
            
            return {
                'search_url': record_url,
                'display_text': display_text,
                'found': True,
                'contact_id': result.get('contact_id', ''),
                'verified': True
            }
        else:
            # Not found - fallback to search URL  
            sf_base_url = "https://telnyx.lightning.force.com"
            search_query = prospect_email if prospect_email else prospect_name.replace(' ', '%20')
            sf_search_url = f"{sf_base_url}/lightning/o/Contact/list?filterName=00B8K00000HbCdpUAF&search={search_query}"
            
            return {
                'search_url': sf_search_url,
                'display_text': f"🔍 Search: {prospect_name}",
                'found': False,
                'verified': False
            }
        
    except Exception as e:
        log_message(f"⚠️ Salesforce lookup error: {str(e)}")
        return {
            'search_url': None,
            'display_text': "Salesforce lookup failed",
            'found': False,
            'verified': False
        }

def post_to_slack(call_data, analysis):
    """Post enhanced call alert to Slack with Salesforce links (WITH QC FILTER)"""
    try:
        # 🛡️ QUALITY CONTROL CHECK - BLOCK GARBAGE
        should_post, qc_reason = validate_call_quality(call_data, analysis)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prospect = call_data.get('prospect_name', 'Unknown')
        
        if not should_post:
            log_message(f"🛡️ QC BLOCKED: {prospect} - {qc_reason}")
            # Log to QC decisions file
            with open('logs/qc_decisions.log', 'a') as f:
                f.write(f"[{timestamp}] ❌ BLOCKED | {prospect} | {qc_reason}\n")
            return False  # Don't post garbage
        
        log_message(f"🛡️ QC APPROVED: {prospect} - {qc_reason}")
        with open('logs/qc_decisions.log', 'a') as f:
            f.write(f"[{timestamp}] ✅ APPROVED | {prospect} | {qc_reason}\n")
        
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
        
        # Add footer with recent call indication
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📁 Source: Recent Calls (2h) | 🤖 AI Analysis: {datetime.now().strftime('%H:%M')} | 🔗 <{sf_lookup.get('search_url', '#')}|View in Salesforce>"
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
            'text': f"New recent call: {prospect_name} with {ae_name}"  # Fallback text
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
                return result.get('ts')
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
            slack_posted BOOLEAN DEFAULT FALSE,
            slack_ts TEXT,
            salesforce_url TEXT,
            processed_at TEXT,
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
    
    cursor.execute('SELECT prospect_name, processed_at FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        prospect_name, processed_at = result
        log_message(f"      🔄 Found duplicate: {prospect_name} processed at {processed_at}")
        return True
    
    return False

def is_call_id_processed(call_id):
    """Check if call ID (Google Doc ID) already processed"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT prospect_name, processed_at FROM processed_calls WHERE call_id = ?', (call_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        prospect_name, processed_at = result
        log_message(f"      🔄 Found by call_id: {prospect_name} processed at {processed_at}")
        return True
    
    return False

def save_processed_call(call_data, analysis, dedup_key, slack_ts=None, sf_url=None):
    """Save processed call to database with Salesforce URL"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_calls 
            (call_id, dedup_key, prospect_name, prospect_email, ae_name, call_date, source, 
             slack_posted, slack_ts, salesforce_updated, ai_analyzed, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data['call_id'],
            dedup_key,
            call_data['prospect_name'],
            call_data['prospect_email'],
            call_data['ae_name'],
            call_data['call_date'],
            call_data['source'],
            slack_ts is not None,
            slack_ts,
            sf_url is not None,  # salesforce_updated boolean
            True,  # ai_analyzed boolean
            datetime.now().isoformat()
        ))
        
        conn.commit()
        log_message(f"💾 Saved to database: {call_data['prospect_name']}")
        
    except Exception as e:
        log_message(f"❌ Error saving call to database: {str(e)}")
    
    finally:
        conn.close()

def run_recent_calls_automation():
    """Run automation for RECENT calls only (last 2 hours)"""
    log_message(f"🚀 V2 RECENT CALLS ONLY - Live Processing")
    log_message(f"⏰ Processing calls modified in last 2 hours")
    log_message(f"📁 Target folder: {TARGET_FOLDER_ID}")
    
    init_database()
    processed_count = 0
    posted_count = 0
    
    # Get ONLY recent Google Drive calls (last 2 hours)
    recent_calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=2)
    log_message(f"📁 Recent Search: {status}")
    
    if not recent_calls:
        log_message("ℹ️ No new calls found in last 2 hours")
        return
    
    log_message(f"🔥 Processing {len(recent_calls)} recent calls...")
    
    for call in recent_calls:
        try:
            call_id = call.get('id')
            
            log_message(f"🆕 Processing: {call['title']}")
            
            # Get content
            content, content_msg = get_google_doc_content(call_id)
            
            if not content:
                log_message(f"   📝 Content: {content_msg}")
                continue
            
            # Log successful content extraction
            content_length = len(content.strip()) if content else 0
            log_message(f"   📝 Content: {content_length} characters extracted successfully")
            
            # Parse call data
            formatted_call = format_enhanced_google_drive_call(call, content)
            prospect_name = formatted_call['prospect_name']
            prospect_email = formatted_call['prospect_email']
            ae_name = formatted_call['ae_name']
            
            log_message(f"   👤 Parsed: {prospect_name} | {ae_name}")
            
            # Check for duplicates (multiple methods)
            call_id = call.get('id')
            dedup_key = generate_dedup_key(prospect_email or prospect_name, call.get('modified_date', ''))
            
            # Method 1: Check by dedup_key (prospect + date)
            if is_call_duplicate(dedup_key):
                log_message(f"   🔄 Already processed (dedup_key): {dedup_key}")
                continue
                
            # Method 2: Check by call_id (Google Doc ID)
            if is_call_id_processed(call_id):
                log_message(f"   🔄 Already processed (call_id): {call_id}")
                continue
            
            log_message(f"   🆕 New call - processing: {dedup_key}")
            
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
                log_message(f"   ⚠️ Slack posting failed (likely blocked by QC)")
            
            # Save to database
            save_processed_call(formatted_call, analysis, dedup_key, slack_ts, sf_lookup.get('search_url'))
            
            processed_count += 1
            log_message(f"   ✅ Completed: {prospect_name}")
            
        except Exception as e:
            log_message(f"   ❌ Error processing call: {str(e)}")
            continue
    
    log_message(f"🎉 RECENT CALLS processing complete: {processed_count} calls processed, {posted_count} posted to Slack")

if __name__ == "__main__":
    try:
        run_recent_calls_automation()
    except Exception as e:
        log_message(f"❌ Fatal error: {e}")
        sys.exit(1)