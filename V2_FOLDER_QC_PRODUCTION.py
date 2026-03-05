#!/usr/bin/env python3
"""
V2 FINAL Call Intelligence with QUALITY CONTROL SYSTEM
Integrates comprehensive QC validation to filter out garbage before posting to Slack

NEW QC FEATURES:
🛡️  Pre-post validation with quality gates
❌ Blocks "Unknown Prospect" and "Unknown AE" posts
🔍 Validates AI analysis quality  
📊 Tracks filtered calls with detailed logging
✅ Only posts HIGH-QUALITY call intelligence to #sales-calls

Based on V2_FOLDER_SPECIFIC_FIXED.py with integrated QC system
"""

import requests
import json
import os
import sqlite3
import sys
import re
from datetime import datetime, timedelta
import subprocess
from qc_validator import QCValidator

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

# Initialize QC Validator
qc_validator = QCValidator()

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def log_qc_stats():
    """Log QC validation statistics"""
    stats = qc_validator.get_stats()
    log_message(f"🛡️  QC STATS: {stats['passed']}/{stats['total_validated']} passed ({stats['success_rate']:.1f}% success rate)")
    
    if stats['gate_failures']:
        log_message("📊 Gate Failure Breakdown:")
        for gate, count in stats['gate_failures'].items():
            log_message(f"   {gate}: {count} failures")

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
                        log_message(f"   📂 Found subfolder: {folder_name} ({folder_id_part})")
        
        log_message(f"📂 Total folders to search: {len(subfolder_ids)}")
        
        # Step 2: Search for Gemini notes in each folder
        for i, current_folder_id in enumerate(subfolder_ids):
            try:
                log_message(f"   🔍 Searching folder {i+1}/{len(subfolder_ids)}: {current_folder_id}")
                
                # Search for Gemini notes in this specific folder
                output, error = run_gog_command(f'gog drive ls --parent {current_folder_id} --query "name contains \'Gemini\'" --max 50 --plain')
                
                if error:
                    log_message(f"      ⚠️ Error searching folder {current_folder_id}: {error}")
                    continue
                
                if not output or 'ID' not in output:
                    log_message(f"      📭 No files in folder {current_folder_id}")
                    continue
                
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                folder_call_count = 0
                
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
                            call_data = {
                                'id': call_id,
                                'title': name,
                                'modified_date': modified_time,
                                'source': 'folder_specific'
                            }
                            all_calls.append(call_data)
                            folder_call_count += 1
                            log_message(f"      📄 Found Gemini note: {name[:60]}...")
                            
                log_message(f"      ✅ Found {folder_call_count} Gemini calls in this folder")
                            
            except Exception as e:
                log_message(f"⚠️ Error searching folder {current_folder_id}: {str(e)}")
                continue
        
        # Remove duplicates by ID
        unique_calls = {call['id']: call for call in all_calls}.values()
        unique_calls = list(unique_calls)
        
        # Sort by modified date (newest first)
        unique_calls.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        log_message(f"📊 Found {len(unique_calls)} unique Gemini calls total")
        
        return unique_calls, f"Found {len(unique_calls)} calls in folder structure"
        
    except Exception as e:
        return [], f"Error getting folder-specific calls: {str(e)}"

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

def extract_attendees_from_content(content):
    """Extract attendees from document content using multiple patterns"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # List of known Telnyx AEs for identification
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'decliner slides', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian'
    ]
    
    try:
        # Pattern 1: Look for "X and Y of Telnyx met with Z"
        summary_patterns = [
            r'(\w+\s+\w+)\s+and\s+(\w+\s+\w+)\s+of\s+Telnyx\s+met\s+with\s+([^.]+)',
            r'(\w+\s+\w+)\s+initiated\s+the\s+call\s+with\s+([^.]+)',
            r'Meeting\s+between\s+([^,]+),\s*([^,]+),?\s*and\s+([^.]+)',
            r'(\w+)\s+from\s+Telnyx.*?met.*?with\s+([^.]+)',
            r'(\w+)\s+&\s+(\w+)\s+sync',
            r'Telnyx.*?&.*?(\w+)',
            r'(\w+)\s+\|\s+Telnyx',
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
                "sentiment": "neutral",
                "error": "JSON parsing failed - using fallback analysis"
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
        sf_base_url = "https://telnyx.lightning.force.com"
        
        if prospect_email:
            search_query = prospect_email
        else:
            search_query = prospect_name.replace(' ', '%20')
        
        sf_search_url = f"{sf_base_url}/lightning/o/Contact/list?filterName=00B8K00000HbCdpUAF&search={search_query}"
        
        return {
            'search_url': sf_search_url,
            'display_text': f"🔍 Search: {prospect_name}",
            'found': True
        }
        
    except Exception as e:
        log_message(f"⚠️ Salesforce lookup error: {str(e)}")
        return {
            'search_url': None,
            'display_text': "Salesforce lookup failed",
            'found': False
        }

def post_to_slack_with_qc(call_data, analysis):
    """Post enhanced call alert to Slack WITH QC VALIDATION"""
    
    # 🛡️ QUALITY CONTROL VALIDATION
    should_post, qc_summary = qc_validator.should_post_to_slack(call_data, analysis)
    
    log_message(f"🛡️ {qc_summary}")
    
    if not should_post:
        log_message(f"🚫 BLOCKED BY QC: {call_data.get('prospect_name', 'Unknown')} - {qc_summary}")
        return None  # Return None to indicate blocked
    
    # If QC passed, proceed with Slack posting
    return post_to_slack(call_data, analysis)

def post_to_slack(call_data, analysis):
    """Post enhanced call alert to Slack with Salesforce links (QC already validated)"""
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
        
        # Add footer with QC indicator
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🛡️ QC Validated | 📁 Source: Drive Folder | 🤖 AI Analysis: {datetime.now().strftime('%H:%M')} | 🔗 <{sf_lookup.get('search_url', '#')}|View in Salesforce>"
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
                log_message(f"✅ Posted to Slack (QC Validated): {prospect_name}")
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
    db_path = 'v2_qc_production.db'
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
            qc_passed BOOLEAN DEFAULT FALSE,
            qc_messages TEXT,
            created_at TEXT,
            UNIQUE(call_id, source)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qc_filtered_calls (
            id INTEGER PRIMARY KEY,
            call_id TEXT,
            prospect_name TEXT,
            ae_name TEXT,
            call_title TEXT,
            failed_gates TEXT,
            qc_messages TEXT,
            call_data TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dedup_key ON processed_calls(dedup_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_qc_passed ON processed_calls(qc_passed)')
    
    conn.commit()
    conn.close()

def generate_dedup_key(prospect_identifier, call_date):
    """Generate deduplication key from prospect and date"""
    clean_prospect = re.sub(r'[^a-zA-Z0-9@.]', '', prospect_identifier.lower())
    date_only = call_date[:10] if len(call_date) >= 10 else call_date
    return f"{clean_prospect}_{date_only}"

def is_call_duplicate(dedup_key):
    """Check if call already processed using deduplication key"""
    db_path = 'v2_qc_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def save_processed_call(call_data, analysis, dedup_key, slack_ts=None, sf_url=None, qc_passed=False, qc_messages=None):
    """Save processed call to database with QC results"""
    db_path = 'v2_qc_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_calls 
            (call_id, dedup_key, prospect_name, prospect_email, ae_name, call_date, source, 
             analysis, slack_posted, slack_ts, salesforce_url, qc_passed, qc_messages, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            qc_passed,
            json.dumps(qc_messages) if qc_messages else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        log_message(f"💾 Saved to database: {call_data['prospect_name']} (QC: {'✅' if qc_passed else '❌'})")
        
    except Exception as e:
        log_message(f"❌ Error saving call to database: {str(e)}")
    
    finally:
        conn.close()

def save_qc_filtered_call(call_data, failed_gates, qc_messages):
    """Save QC filtered call for audit trail"""
    db_path = 'v2_qc_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO qc_filtered_calls 
            (call_id, prospect_name, ae_name, call_title, failed_gates, qc_messages, call_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data.get('call_id'),
            call_data.get('prospect_name'),
            call_data.get('ae_name'),
            call_data.get('title'),
            json.dumps(failed_gates),
            json.dumps(qc_messages),
            json.dumps(call_data),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
    except Exception as e:
        log_message(f"❌ Error saving filtered call: {str(e)}")
    
    finally:
        conn.close()

def run_folder_specific_automation_with_qc():
    """Run V2 automation with COMPREHENSIVE QC VALIDATION"""
    log_message(f"🚀 V2 QC-ENHANCED Call Intelligence - LIVE PROCESSING WITH QUALITY CONTROL")
    log_message(f"🛡️ QC System: Active with comprehensive validation gates")
    log_message(f"📁 Target folder: {TARGET_FOLDER_ID}")
    
    init_database()
    processed_count = 0
    posted_count = 0
    qc_blocked_count = 0
    
    # Get Google Drive calls from specific folder only
    folder_calls, folder_status = get_folder_specific_gemini_calls(TARGET_FOLDER_ID)
    log_message(f"📁 Folder Search: {folder_status}")
    
    if not folder_calls:
        log_message("ℹ️ No new calls found in specified folder")
        log_qc_stats()
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
            
            # 🛡️ QC VALIDATION CHECKPOINT
            log_message(f"   🛡️ Running QC validation...")
            should_post, qc_summary = qc_validator.should_post_to_slack(formatted_call, analysis)
            
            # Salesforce lookup
            sf_lookup = lookup_salesforce_prospect(prospect_name, prospect_email)
            
            if should_post:
                # QC PASSED - Post to Slack
                log_message(f"   ✅ QC PASSED - Posting to Slack...")
                slack_ts = post_to_slack(formatted_call, analysis)
                
                if slack_ts:
                    posted_count += 1
                    log_message(f"   ✅ Posted to Slack (QC Validated)")
                else:
                    log_message(f"   ⚠️ Slack posting failed (but QC passed)")
                
                # Save with QC passed
                save_processed_call(formatted_call, analysis, dedup_key, slack_ts, 
                                  sf_lookup.get('search_url'), qc_passed=True)
                
            else:
                # QC FAILED - Block posting but log details
                qc_blocked_count += 1
                log_message(f"   🚫 QC FAILED - BLOCKED: {qc_summary}")
                
                # Save to filtered calls table for audit
                failed_gates = [gate for gate, passed in qc_validator.validation_stats.get('gate_failures', {}).items()]
                save_qc_filtered_call(formatted_call, failed_gates, [qc_summary])
                
                # Still save to processed calls but mark as not posted
                save_processed_call(formatted_call, analysis, dedup_key, None, 
                                  sf_lookup.get('search_url'), qc_passed=False, 
                                  qc_messages=[qc_summary])
            
            processed_count += 1
            log_message(f"   ✅ Completed: {prospect_name} (QC: {'✅' if should_post else '❌'})")
            
        except Exception as e:
            log_message(f"   ❌ Error processing call: {str(e)}")
            continue
    
    # Final statistics
    log_message(f"🎉 QC-ENHANCED processing complete:")
    log_message(f"   📊 {processed_count} calls processed")
    log_message(f"   ✅ {posted_count} posted to Slack (QC validated)")
    log_message(f"   🚫 {qc_blocked_count} blocked by QC")
    log_qc_stats()

if __name__ == "__main__":
    try:
        run_folder_specific_automation_with_qc()
    except Exception as e:
        log_message(f"❌ Fatal error: {e}")
        sys.exit(1)