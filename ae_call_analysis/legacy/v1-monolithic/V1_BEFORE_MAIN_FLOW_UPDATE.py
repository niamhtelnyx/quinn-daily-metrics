#!/usr/bin/env python3
"""
V1 Call Intelligence - ENHANCED WITH GOOGLE DRIVE
Google Drive "Gemini Notes" → Enhanced Slack Alert + Salesforce Update

ENHANCED FEATURES (From V1):
✅ AI call analysis (9-point structure) 
✅ Enhanced Slack alerts with Salesforce links
✅ Company summaries
✅ Salesforce event updates  
✅ Database tracking
✅ Threaded Slack posting

NEW FEATURES (From V2):
✅ Google Drive integration (replaces Fellow)
✅ Recent calls filtering (efficiency)
✅ Quality control validation

MIGRATION: V1 proven functionality + V2 Google Drive integration
"""

import requests
import json
import os
import sqlite3
import sys
import re
import subprocess
from datetime import datetime, timedelta
from dateutil import parser

# Google Drive folder configuration (from V2)
TARGET_FOLDER_ID = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"

def load_env():
    """Enhanced environment loading for both .env and .env.gog"""
    # Load existing .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

    # Load .env.gog for Google Drive (from V2)
    gog_env_path = '/Users/niamhcollins/clawd/.env.gog'
    if os.path.exists(gog_env_path):
        with open(gog_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    os.environ[key] = value.strip('"')

load_env()

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

# ==== GOOGLE DRIVE INTEGRATION (FROM V2) ====

def run_gog_command(cmd):
    """Run gog CLI command and return output (from V2_RECENT_CALLS_ONLY.py)"""
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

def is_recent_call(modified_time_str, hours_back=2):
    """Check if call was modified within the last N hours (from V2)"""
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
    """Get ONLY recent Gemini call notes (last N hours) - from V2_RECENT_CALLS_ONLY.py"""
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

def get_google_doc_content(doc_id):
    """Get Google Doc content using gog CLI (from V2)"""
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
    """Enhanced attendee extraction from document content and title (from V2)"""
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
    """Enhanced parsing of Google Drive call data (from V2)"""
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
        'source': 'google_drive',
        'content': content,
        'recording_url': None
    }

# ==== V1 CORE FUNCTIONS (PRESERVE ALL) ====

def get_company_summary_with_ai(transcript, prospect_name, company_name=""):
    """Generate company summary from transcript and available info (V1 ORIGINAL)"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key or not transcript:
        return None
        
    try:
        company_prompt = f"""
Based on this sales call transcript, extract and create a 1-sentence company summary for {company_name or prospect_name + "'s company"}.

TRANSCRIPT:
{transcript[:4000]}

Provide ONLY a company description in this format:
[Company Name] is a [industry/type] company that [what they do/provide] for [target customers/market].

Examples:
- Ondasa is a technology company that provides telephony and digital marketing solutions for businesses.
- TechCorp is a software development company that creates customer engagement platforms for enterprise clients.

Be concise, professional, and extract real information from the transcript. If no clear company information is available, return "Unknown company details".
"""
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "You are an expert at extracting company information from sales calls. Be concise and accurate."},
                    {"role": "user", "content": company_prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.3
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result['choices'][0]['message']['content'].strip()
            return summary if summary != "Unknown company details" else None
        return None
        
    except Exception as e:
        return None

def analyze_call_with_ai(transcript, prospect_name, company_name="", company_website=""):
    """V1 ORIGINAL THREADED FORMAT with COMPANY SUMMARY - Analyze call with detailed breakdown for main post + thread"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        return {
            "status": "no_api_key",
            "main_post": "❌ OpenAI API key required",
            "thread_reply": "Add OPENAI_API_KEY to .env for detailed insights",
            "summary": "❌ OpenAI API key required"
        }
    
    if not transcript:
        return {
            "status": "no_transcript", 
            "main_post": "❌ No transcript available",
            "thread_reply": "Transcript not found for AI analysis",
            "summary": "❌ No transcript available"
        }

    # Get company summary
    company_summary = get_company_summary_with_ai(transcript, prospect_name, company_name)
    
    # Format company line with company name hyperlinked to website
    company_line = ""
    if company_summary:
        if company_name and company_website:
            # Clean website (remove protocol, trailing slashes)
            clean_website = company_website.replace('https://', '').replace('http://', '').strip('/')
            full_url = f"https://{clean_website}"
            # Format: <URL|Company> - display shows just "Company", links to URL
            company_line = f"🏢 <{full_url}|{company_name}> is {company_summary.lower()}"
        elif company_name:
            company_line = f"🏢 {company_name} is {company_summary.lower()}"
        else:
            company_line = f"🏢 {company_summary}"
    
    # V1 ORIGINAL DETAILED PROMPT for threaded Slack format matching user's example
    analysis_prompt = f"""
Analyze this Telnyx intro call transcript for {prospect_name}.

TRANSCRIPT:
{transcript[:8000]}

Provide TWO separate formatted outputs:

=== MAIN POST ===
Meeting Notes Retrieved
📆 {prospect_name} | [extract AE names from transcript] | [today's date]
{company_line}
📊 Scores: Interest X/10 | AE X/10 | Quinn X/10  
🔴 Key Pain: [primary pain point in one line]
💡 Product Focus: [main Telnyx product discussed]
🚀 Next Step: [primary action needed]
🔗 Salesforce: ✅ Validated
See thread for full analysis and stakeholder actions 👇

=== THREAD REPLY ===
📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS

🔴 All Pain Points:
1. [First pain point]
2. [Second pain point]
3. [Third pain point if any]

🎯 Use Cases Discussed:
• [Use case 1]
• [Use case 2]

💡 Telnyx Products:
• [Product 1] 
• [Product 2]

🗣️ Conversation Style: [Technical Integration/Strategic Discussion/etc.]

📈 Buying Signals:
• [Signal 1]
• [Signal 2]

🚀 NEXT STEPS Category: [Technical Validation/Commercial Discussion/etc.]
Actions:
• [Action 1] 
• [Action 2]

📋 QUINN REVIEW
Quality: X/10

🎯 STAKEHOLDER ACTIONS

📈 Sales Manager:
🌟 [Performance feedback or coaching notes]

🎨 Marketing:
📊 Pain trend: [main pain point for trend tracking]

🔧 Product:
🔧 Interest in: [main product discussed]

👑 Executive:
📈 [Qualification status and strategic insights]

Analyze thoroughly and provide realistic scores. Extract AE names from the transcript.
"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "You are an expert sales call analyst. Provide detailed, actionable insights in the exact format requested. Follow the format precisely."},
                    {"role": "user", "content": analysis_prompt}
                ],
                "max_tokens": 3000,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            full_analysis = ai_response['choices'][0]['message']['content']
            
            # Split into main post and thread reply
            parts = full_analysis.split("=== THREAD REPLY ===")
            main_post = parts[0].replace("=== MAIN POST ===", "").strip()
            thread_reply = parts[1].strip() if len(parts) > 1 else ""
            
            return {
                "status": "success",
                "main_post": main_post,
                "thread_reply": thread_reply,
                "summary": main_post,  # For backward compatibility
                "full_analysis": full_analysis
            }
        else:
            return {
                "status": "error",
                "main_post": f"❌ OpenAI API error: {response.status_code}",
                "thread_reply": "AI analysis failed",
                "summary": f"❌ OpenAI API error: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "main_post": f"❌ AI analysis failed: {str(e)}",
            "thread_reply": "Error in AI processing",
            "summary": f"❌ AI analysis failed: {str(e)}"
        }

def get_salesforce_token():
    """Get Salesforce OAuth2 access token (V1 ORIGINAL)"""
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    
    if not client_id or not client_secret:
        return None, "Salesforce credentials missing"
    
    try:
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=auth_data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token'), "✅ Salesforce authenticated"
        else:
            return None, f"❌ Salesforce auth failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Salesforce error: {e}"

def find_salesforce_contact_enhanced(prospect_name, access_token):
    """Find Salesforce contact with enhanced data including company name and website (V1 ORIGINAL)"""
    if not access_token:
        return None, "No access token"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Enhanced query to get contact + account info including website
        # Make sure we get all account fields we need for company info
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Description, Account.Website, Account.Type FROM Contact WHERE Name LIKE '%{prospect_name}%' LIMIT 5"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('records', [])
            if contacts:
                contact = contacts[0]
                # Extract account data safely
                account = contact.get('Account', {})
                
                # Clean company website if present
                company_website = account.get('Website')
                if company_website:
                    # Clean up website format
                    company_website = company_website.replace('https://', '').replace('http://', '').strip('/')
                    if company_website.startswith('www.'):
                        company_website = company_website[4:]
                
                company_name = account.get('Name')
                
                return {
                    'contact_id': contact['Id'],
                    'contact_name': contact['Name'],
                    'account_id': contact.get('AccountId'),
                    'company_name': company_name,
                    'company_description': account.get('Description'),
                    'company_website': company_website,
                    'account_type': account.get('Type')
                }, f"✅ Found contact: {contact['Name']}" + (f" at {company_name}" if company_name else "")
            else:
                return None, f"⚠️ No contact found for: {prospect_name}"
        else:
            return None, f"❌ Contact search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Contact search error: {e}"

def find_or_update_salesforce_event(contact_data, prospect_name, call_id, access_token):
    """Find and update Salesforce event (V1 ORIGINAL CRITICAL FUNCTIONALITY)"""
    if not access_token or not contact_data:
        return None, "Missing access token or contact"
    
    contact_id = contact_data['contact_id']
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        query = f"SELECT Id, Subject, Description FROM Event WHERE WhoId = '{contact_id}' AND Subject LIKE '%Telnyx Intro%' ORDER BY CreatedDate DESC LIMIT 5"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('records', [])
            
            if events:
                event_id = events[0]['Id']
                google_drive_url = f"https://docs.google.com/document/d/{call_id}/edit"
                
                update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_id}"
                update_data = {
                    'Description': f"Telnyx Intro Call with {prospect_name}\\n\\n📁 Google Drive Notes: {google_drive_url}\\n\\n✅ Processed by V1 Enhanced Intelligence (Google Drive) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
                
                update_response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)
                
                if update_response.status_code == 204:
                    return event_id, f"✅ Updated event {event_id}"
                else:
                    return None, f"❌ Event update failed: {update_response.status_code}"
            else:
                return None, f"⚠️ No existing event found for {prospect_name}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Event processing error: {e}"

def post_to_slack_bot_api(message, channel="C0AJ9E9F474"):
    """Post enhanced message to Slack using Bot Token API (V1 ORIGINAL)"""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        return False, "❌ SLACK_BOT_TOKEN not found"
    
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": channel,
            "text": message,
            "unfurl_links": True,
            "unfurl_media": True
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                message_ts = data.get('ts', 'unknown')
                return True, f"✅ Posted to Slack (ts: {message_ts})"
            else:
                error = data.get('error', 'unknown_error')
                return False, f"❌ Slack API error: {error}"
        else:
            return False, f"❌ HTTP error: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Slack error: {str(e)}"

def post_thread_reply_to_slack(message, parent_ts, channel="C0AJ9E9F474"):
    """Post thread reply to Slack (V1 ORIGINAL)"""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        return False, "❌ SLACK_BOT_TOKEN not found"
    
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": channel,
            "text": message,
            "thread_ts": parent_ts,
            "unfurl_links": True,
            "unfurl_media": True
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return True, f"✅ Posted thread reply"
            else:
                error = data.get('error', 'unknown_error')
                return False, f"❌ Thread error: {error}"
        else:
            return False, f"❌ HTTP error: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Thread error: {str(e)}"

def is_call_processed(call_id):
    """Check if call already processed (V1 ORIGINAL)"""
    db_path = 'v1_google_drive.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            call_id TEXT UNIQUE,
            prospect_name TEXT,
            processed_at TEXT,
            slack_posted BOOLEAN DEFAULT FALSE,
            salesforce_updated BOOLEAN DEFAULT FALSE,
            ai_analyzed BOOLEAN DEFAULT FALSE,
            source TEXT DEFAULT 'google_drive'
        )
    ''')
    
    cursor.execute('SELECT * FROM processed_calls WHERE call_id = ?', (call_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success):
    """Mark call as processed with enhanced tracking (V1 ORIGINAL + source tracking)"""
    db_path = 'v1_google_drive.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (call_id, prospect_name, processed_at, slack_posted, salesforce_updated, ai_analyzed, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), slack_success, sf_success, ai_success, 'google_drive'))
    
    conn.commit()
    conn.close()

def extract_event_name_from_google_title(title):
    """Extract event name from: Copy of {event name} - {time} - Notes by Gemini"""
    import re
    pattern = r'^Copy of (.+?) - \d{4}/\d{2}/\d{2} .+ - Notes by Gemini'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return None

def find_salesforce_event_by_exact_subject(event_name, access_token):
    """Find Salesforce event by exact subject: Meeting Booked: {event name}"""
    if not access_token or not event_name:
        return None, "Missing access token or event name"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # EXACT subject match - fixed syntax
        subject = "Meeting Booked: " + event_name
        query = f"SELECT Id, Subject, WhoId, OwnerId, AssignedToId FROM Event WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('records', [])
            if events:
                event = events[0]
                return {
                    'event_id': event['Id'],
                    'contact_id': event['WhoId'], 
                    'ae_user_id': event.get('AssignedToId') or event.get('OwnerId'),
                    'subject': event['Subject']
                }, f"✅ Found event: {event['Subject']}"
            else:
                return None, f"❌ No event found: Meeting Booked: {event_name}"
        else:
            return None, f"❌ Event search failed: {response.status_code}"
    except Exception as e:
        return None, f"❌ Event search error: {e}"

def get_contact_from_event(contact_id, access_token):
    """Get contact details from contact ID"""
    if not access_token or not contact_id:
        return None, "Missing access token or contact ID"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx') 
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Website FROM Contact WHERE Id = '{contact_id}'"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('records', [])
            if contacts:
                contact = contacts[0]
                account = contact.get('Account', {})
                return {
                    'contact_id': contact['Id'],
                    'contact_name': contact['Name'],
                    'contact_email': contact.get('Email'),
                    'company_name': account.get('Name'),
                    'company_website': account.get('Website')
                }, f"✅ Found contact: {contact['Name']}"
            else:
                return None, f"❌ No contact found: {contact_id}"
        else:
            return None, f"❌ Contact lookup failed: {response.status_code}"
    except Exception as e:
        return None, f"❌ Contact lookup error: {e}"

def run_enhanced_automation():
    """Run ENHANCED V1 automation with Google Drive integration"""
    log_message("🚀 V1 ENHANCED Call Intelligence - Google Drive Integration")
    
    # Get recent Google Drive calls (replacing Fellow API)
    calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=2)
    log_message(f"📁 Google Drive: {status}")
    
    if not calls:
        log_message("😴 No calls found")
        return
    
    processed_count = 0
    
    # Get Salesforce token once (V1 ORIGINAL)
    access_token, auth_msg = get_salesforce_token()
    log_message(f"🏢 Salesforce: {auth_msg}")
    
    for call in calls:
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        if is_call_processed(call_id):
            continue
            
        log_message(f"🆕 Processing ENHANCED: {title[:60]}...")
        
        # Step 1: Get Google Doc content (replacing Fellow transcript)
        content, content_msg = get_google_doc_content(call_id)
        log_message(f"   📝 Content: {content_msg}")
        
        if not content:
            continue
        
        # Step 2: Parse Google Drive call data (replacing Fellow data parsing)
        formatted_call = format_enhanced_google_drive_call(call, content)
        prospect_name = formatted_call['prospect_name']
        
        log_message(f"   👤 Parsed: {prospect_name}")
        
        # Step 3: Find Salesforce contact with enhanced data (V1 ORIGINAL - KEEP)
        contact_data = None
        if access_token:
            contact_data, contact_msg = find_salesforce_contact_enhanced(prospect_name, access_token)
            log_message(f"   👤 Contact: {contact_msg}")
        
        # Step 4: Run AI analysis with company information (V1 ORIGINAL - KEEP)
        company_name = contact_data.get('company_name', '') if contact_data else ''
        company_website = contact_data.get('company_website', '') if contact_data else ''
        ai_analysis = analyze_call_with_ai(content, prospect_name, company_name, company_website)
        ai_success = ai_analysis.get('status') == 'success'
        log_message(f"   🤖 AI Analysis: {ai_analysis.get('status')}")
        
        # Step 5: Update Salesforce event (V1 ORIGINAL - CRITICAL)
        event_id = None
        sf_success = False
        if contact_data and access_token:
            event_id, event_msg = find_or_update_salesforce_event(contact_data, prospect_name, call_id, access_token)
            sf_success = event_id is not None
            log_message(f"   📅 Event: {event_msg}")
        
        # Step 6: Post ORIGINAL V1 THREADED format to Slack (V1 ORIGINAL - KEEP)
        if ai_analysis.get('status') == 'success' and ai_analysis.get('main_post'):
            # Post main message
            main_post = ai_analysis['main_post']
            slack_success, slack_msg = post_to_slack_bot_api(main_post)
            log_message(f"   📱 Slack Main: {slack_msg}")
            
            # Post thread reply if main post succeeded
            if slack_success and ai_analysis.get('thread_reply'):
                # Extract timestamp from slack_msg for threading
                ts_match = re.search(r'ts: ([\d.]+)', slack_msg)
                if ts_match:
                    parent_ts = ts_match.group(1)
                    thread_reply = ai_analysis['thread_reply']
                    thread_success, thread_msg = post_thread_reply_to_slack(thread_reply, parent_ts)
                    log_message(f"   📱 Slack Thread: {thread_msg}")
        else:
            slack_success = False
            log_message(f"   📱 Slack: Skipped due to AI analysis failure")
        
        # Step 7: Mark as processed (V1 ORIGINAL)
        mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success)
        
        processed_count += 1
        log_message(f"✅ ENHANCED: {prospect_name} (Slack: {'✅' if slack_success else '❌'}, SF: {'✅' if sf_success else '❌'}, AI: {'✅' if ai_success else '❌'})")
        
        if processed_count >= 3:
            break
    
    if processed_count == 0:
        log_message("😴 No new calls to process")
    else:
        log_message(f"🎉 V1 ENHANCED (Google Drive) processed {processed_count} calls")

if __name__ == "__main__":
    try:
        run_enhanced_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)