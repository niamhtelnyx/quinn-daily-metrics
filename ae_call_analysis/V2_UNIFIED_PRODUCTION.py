#!/usr/bin/env python3
"""
V2 Unified Call Intelligence - PRODUCTION
Processes both Fellow "Telnyx Intro Call" AND Google Drive "Notes by Gemini" calls

UNIFIED FEATURES:
✅ Fellow API processing (existing)
✅ Google Drive integration (new)
✅ AI call analysis (9-point structure)
✅ Enhanced Slack alerts with Salesforce links
✅ Company summaries
✅ Salesforce event updates
✅ Unified database tracking
"""

import requests
import json
import os
import sqlite3
import sys
from datetime import datetime
import subprocess

# Import our Google Drive integration module
from google_drive_integration import get_google_drive_calls, get_google_doc_content, format_google_drive_call_for_processing

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

def get_fellow_intro_calls():
    """Get Fellow 'Telnyx Intro Call' recordings from today only"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return [], "No Fellow API key found"
    
    headers = {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    # Get today's date for filtering
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            json={
                "page": 1, 
                "limit": 50,
                "include": {
                    "transcript": True,
                    "ai_notes": True
                }
            },
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            return [], f"Fellow API error: {response.status_code}"
            
        data = response.json()
        recordings = data.get('recordings', {}).get('data', [])
        
        # Filter for "Telnyx Intro Call" AND today's date
        today_intro_calls = []
        for call in recordings:
            if 'telnyx intro call' in call.get('title', '').lower():
                created_at = call.get('created_at', '')
                call_date = created_at[:10] if created_at else ''
                if call_date == today:
                    today_intro_calls.append(call)
        
        return today_intro_calls, f"Found {len(today_intro_calls)} Fellow intro calls from today ({today})"
        
    except Exception as e:
        return [], f"Error: {str(e)}"

def get_fellow_transcript(call_data):
    """Get transcript from Fellow call data (parse structured transcript)"""
    # Parse transcript data (it's a complex object with speech_segments)
    transcript_data = call_data.get('transcript')
    ai_notes_data = call_data.get('ai_notes')
    
    # Extract text from speech segments
    if transcript_data and isinstance(transcript_data, dict):
        speech_segments = transcript_data.get('speech_segments', [])
        if speech_segments:
            # Combine all speech segments into readable transcript
            transcript_text = []
            for segment in speech_segments:
                speaker = segment.get('speaker', 'Speaker')
                text = segment.get('text', '')
                transcript_text.append(f"{speaker}: {text}")
            
            full_transcript = "\n".join(transcript_text)
            if len(full_transcript.strip()) > 10:
                return full_transcript, f"✅ Fellow transcript retrieved ({len(speech_segments)} segments)"
    
    return None, "⚠️ No usable Fellow transcript found"

def get_company_summary_with_ai(transcript, prospect_name, company_name=""):
    """Generate company summary from transcript and available info"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key or not transcript:
        return None
        
    try:
        company_prompt = f"""
Based on this sales call transcript/notes, extract and create a 1-sentence company summary for {company_name or prospect_name + "'s company"}.

CONTENT:
{transcript[:4000]}

Provide ONLY a company description in this format:
[Company Name] is a [industry/type] company that [what they do/provide] for [target customers/market].

Examples:
- Ondasa is a technology company that provides telephony and digital marketing solutions for businesses.
- Gail AI is an artificial intelligence company that creates voice AI agents for insurance agencies and call centers.

Be concise, professional, and extract real information from the content. If no clear company information is available, return "Unknown company details".
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

def analyze_call_with_ai(content, prospect_name, company_name="", company_website="", source="fellow"):
    """UNIFIED AI ANALYSIS - Analyze both Fellow transcripts and Google Drive notes"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        return {
            "status": "no_api_key",
            "main_post": "❌ OpenAI API key required",
            "thread_reply": "Add OPENAI_API_KEY to .env for detailed insights",
            "summary": "❌ OpenAI API key required"
        }
    
    if not content:
        return {
            "status": "no_content", 
            "main_post": "❌ No content available",
            "thread_reply": "No content found for AI analysis",
            "summary": "❌ No content available"
        }

    # Get company summary
    company_summary = get_company_summary_with_ai(content, prospect_name, company_name)
    
    # Format company line with company name hyperlinked to website
    company_line = ""
    if company_summary:
        if company_name and company_website:
            # Clean website (remove protocol, trailing slashes)
            clean_website = company_website.replace('https://', '').replace('http://', '').strip('/')
            full_url = f"https://{clean_website}"
            company_line = f"🏢 <{full_url}|{company_name}> is {company_summary.lower()}"
        elif company_name:
            company_line = f"🏢 {company_name} is {company_summary.lower()}"
        else:
            company_line = f"🏢 {company_summary}"
    
    # Adaptive prompt based on content source
    if source == "google_drive":
        content_description = "Google Meet notes with Gemini summary"
        content_instruction = "This content is already structured with summary, details, and next steps. Extract insights from this structured format."
    else:
        content_description = "Fellow call transcript"
        content_instruction = "This is a raw transcript with speaker segments. Extract insights from the conversation flow."

    analysis_prompt = f"""
Analyze this Telnyx intro call {content_description} for {prospect_name}.

CONTENT ({source.upper()}):
{content[:8000]}

{content_instruction}

Provide TWO separate formatted outputs:

=== MAIN POST ===
Meeting Notes Retrieved
📆 {prospect_name} | [extract AE names from content] | [today's date]
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

Analyze thoroughly and provide realistic scores. Extract AE names from the content.
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
                "full_analysis": full_analysis,
                "source": source
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
    """Get Salesforce OAuth2 access token"""
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
    """Find Salesforce contact with enhanced data including company name and website"""
    if not access_token:
        return None, "No access token"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Enhanced query to get contact + account info including website
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Description, Account.Website, Account.Type FROM Contact WHERE Name LIKE '%{prospect_name}%' OR Email LIKE '%{prospect_name}%' LIMIT 5"
        
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

def post_to_slack_bot_api(message, channel="C0AJ9E9F474"):
    """Post enhanced message to Slack using Bot Token API"""
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
    """Post thread reply to Slack"""
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

def is_call_processed(call_id, source="fellow"):
    """Check if call already processed (unified database)"""
    db_path = 'v2_unified.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            call_id TEXT,
            source TEXT,
            prospect_name TEXT,
            processed_at TEXT,
            slack_posted BOOLEAN DEFAULT FALSE,
            salesforce_updated BOOLEAN DEFAULT FALSE,
            ai_analyzed BOOLEAN DEFAULT FALSE,
            UNIQUE(call_id, source)
        )
    ''')
    
    cursor.execute('SELECT * FROM processed_calls WHERE call_id = ? AND source = ?', (call_id, source))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_call_processed(call_id, source, prospect_name, slack_success, sf_success, ai_success):
    """Mark call as processed with enhanced tracking (unified database)"""
    db_path = 'v2_unified.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (call_id, source, prospect_name, processed_at, slack_posted, salesforce_updated, ai_analyzed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (call_id, source, prospect_name, datetime.now().isoformat(), slack_success, sf_success, ai_success))
    
    conn.commit()
    conn.close()

def run_unified_automation():
    """Run UNIFIED V2 automation - processes both Fellow and Google Drive calls"""
    log_message("🚀 V2 UNIFIED Call Intelligence - Live Monitoring (Fellow + Google Drive)")
    
    processed_count = 0
    
    # Get Salesforce token once for both sources
    access_token, auth_msg = get_salesforce_token()
    log_message(f"🏢 Salesforce: {auth_msg}")
    
    # Process Fellow calls
    log_message("📞 Checking Fellow API...")
    fellow_calls, fellow_status = get_fellow_intro_calls()
    log_message(f"📞 Fellow: {fellow_status}")
    
    for call in fellow_calls:
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        if is_call_processed(call_id, 'fellow'):
            continue
            
        if '(' in title and ')' in title:
            prospect_name = title.split('(')[1].split(')')[0]
        else:
            prospect_name = 'Unknown'
        
        log_message(f"🆕 Processing Fellow: {prospect_name}")
        
        # Get Fellow transcript
        transcript, transcript_msg = get_fellow_transcript(call)
        log_message(f"   📝 Transcript: {transcript_msg}")
        
        if transcript:
            # Find Salesforce contact
            contact_data = None
            if access_token:
                contact_data, contact_msg = find_salesforce_contact_enhanced(prospect_name, access_token)
                log_message(f"   👤 Contact: {contact_msg}")
            
            # Run AI analysis
            company_name = contact_data.get('company_name', '') if contact_data else ''
            company_website = contact_data.get('company_website', '') if contact_data else ''
            ai_analysis = analyze_call_with_ai(transcript, prospect_name, company_name, company_website, 'fellow')
            ai_success = ai_analysis.get('status') == 'success'
            log_message(f"   🤖 AI Analysis: {ai_analysis.get('status')}")
            
            # Post to Slack
            if ai_analysis.get('status') == 'success' and ai_analysis.get('main_post'):
                main_post = ai_analysis['main_post']
                slack_success, slack_msg = post_to_slack_bot_api(main_post)
                log_message(f"   📱 Slack Main: {slack_msg}")
                
                # Post thread reply if main post succeeded
                if slack_success and ai_analysis.get('thread_reply'):
                    import re
                    ts_match = re.search(r'ts: ([\d.]+)', slack_msg)
                    if ts_match:
                        parent_ts = ts_match.group(1)
                        thread_reply = ai_analysis['thread_reply']
                        thread_success, thread_msg = post_thread_reply_to_slack(thread_reply, parent_ts)
                        log_message(f"   📱 Slack Thread: {thread_msg}")
            else:
                slack_success = False
            
            # Mark as processed
            mark_call_processed(call_id, 'fellow', prospect_name, slack_success, False, ai_success)
            processed_count += 1
            log_message(f"✅ Fellow: {prospect_name} (AI: {'✅' if ai_success else '❌'}, Slack: {'✅' if slack_success else '❌'})")
    
    # Process Google Drive calls
    log_message("📁 Checking Google Drive...")
    google_calls, google_status = get_google_drive_calls()
    log_message(f"📁 Google Drive: {google_status}")
    
    for call in google_calls:
        call_id = call.get('id')
        
        if is_call_processed(call_id, 'google_drive'):
            continue
        
        log_message(f"🆕 Processing Google Drive: {call['title']}")
        
        # Get document content
        content, content_msg = get_google_doc_content(call_id)
        log_message(f"   📝 Content: {content_msg}")
        
        if content:
            # Format call data for processing
            formatted_call = format_google_drive_call_for_processing(call, content)
            prospect_name = formatted_call['prospect_name']
            
            # Find Salesforce contact
            contact_data = None
            if access_token:
                contact_data, contact_msg = find_salesforce_contact_enhanced(prospect_name, access_token)
                log_message(f"   👤 Contact: {contact_msg}")
            
            # Run AI analysis
            company_name = contact_data.get('company_name', '') if contact_data else ''
            company_website = contact_data.get('company_website', '') if contact_data else ''
            ai_analysis = analyze_call_with_ai(content, prospect_name, company_name, company_website, 'google_drive')
            ai_success = ai_analysis.get('status') == 'success'
            log_message(f"   🤖 AI Analysis: {ai_analysis.get('status')}")
            
            # Post to Slack
            if ai_analysis.get('status') == 'success' and ai_analysis.get('main_post'):
                main_post = ai_analysis['main_post']
                slack_success, slack_msg = post_to_slack_bot_api(main_post)
                log_message(f"   📱 Slack Main: {slack_msg}")
                
                # Post thread reply if main post succeeded
                if slack_success and ai_analysis.get('thread_reply'):
                    import re
                    ts_match = re.search(r'ts: ([\d.]+)', slack_msg)
                    if ts_match:
                        parent_ts = ts_match.group(1)
                        thread_reply = ai_analysis['thread_reply']
                        thread_success, thread_msg = post_thread_reply_to_slack(thread_reply, parent_ts)
                        log_message(f"   📱 Slack Thread: {thread_msg}")
            else:
                slack_success = False
            
            # Mark as processed
            mark_call_processed(call_id, 'google_drive', prospect_name, slack_success, False, ai_success)
            processed_count += 1
            log_message(f"✅ Google Drive: {prospect_name} (AI: {'✅' if ai_success else '❌'}, Slack: {'✅' if slack_success else '❌'})")
    
    if processed_count == 0:
        log_message("😴 No new calls to process from either source")
    else:
        log_message(f"🎉 V2 UNIFIED processed {processed_count} calls total")

if __name__ == "__main__":
    try:
        run_unified_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)