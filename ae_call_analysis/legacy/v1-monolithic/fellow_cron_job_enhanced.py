#!/usr/bin/env python3
"""
V1 Call Intelligence - ENHANCED PRODUCTION
Fellow "Telnyx Intro Call" → Enhanced Slack Alert + Salesforce Update

ENHANCED FEATURES:
✅ Fellow API processing
✅ AI call analysis (9-point structure)
✅ Enhanced Slack alerts with Salesforce links
✅ Company summaries
✅ Salesforce event updates
✅ Database tracking
"""

import requests
import json
import os
import sqlite3
import sys
from datetime import datetime

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
    """Get Fellow 'Telnyx Intro Call' recordings"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return [], "No Fellow API key found"
    
    headers = {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            json={"page": 1, "limit": 10},
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            return [], f"Fellow API error: {response.status_code}"
            
        data = response.json()
        recordings = data.get('recordings', {}).get('data', [])
        
        # Filter for "Telnyx Intro Call"
        intro_calls = [
            call for call in recordings 
            if 'telnyx intro call' in call.get('title', '').lower()
        ]
        
        return intro_calls, f"Found {len(intro_calls)} intro calls"
        
    except Exception as e:
        return [], f"Error: {str(e)}"

def get_fellow_transcript(call_id):
    """Get transcript from Fellow call"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return None, "No Fellow API key"
    
    headers = {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # Try to get transcript - this may need the correct Fellow API endpoint
        response = requests.get(
            f'https://telnyx.fellow.app/api/v1/recordings/{call_id}/transcript',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            transcript = data.get('transcript', data.get('text', ''))
            return transcript, "✅ Transcript retrieved"
        else:
            return None, f"❌ Transcript unavailable: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Transcript error: {e}"

def analyze_call_with_ai(transcript, prospect_name):
    """Analyze call with OpenAI - 9-point structure"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        return {
            "status": "no_api_key",
            "summary": "AI analysis unavailable - add OPENAI_API_KEY to .env for enhanced insights"
        }
    
    if not transcript:
        return {
            "status": "no_transcript",
            "summary": "AI analysis unavailable - no transcript found for this call"
        }
    
    analysis_prompt = f"""Analyze this Telnyx intro call with {prospect_name}. Provide concise insights:

TRANSCRIPT: {transcript[:2000]}...

Respond with 9 key insights in this exact format:

**🔴 Pain Points**: [What business problems do they have?]
**🎯 Use Cases**: [How will they use Telnyx?]  
**💡 Products**: [Which Telnyx services discussed?]
**📈 Buying Signals**: [What shows purchase intent?]
**⚙️ Technical Needs**: [What integrations/specs needed?]
**⏰ Timeline**: [How urgent? When do they need it?]
**👤 Decision Makers**: [Who decides? Are they involved?]
**🔄 Competition**: [Current provider/competitors mentioned?]
**🚀 Next Steps**: [What should happen next?]

**Scores**: Interest: X/10, Qualification: X/10, AE Performance: X/10"""

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
                    {"role": "system", "content": "You are an expert sales call analyst. Be concise and actionable."},
                    {"role": "user", "content": analysis_prompt}
                ],
                "max_tokens": 800,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            content = ai_response['choices'][0]['message']['content']
            return {
                "status": "success",
                "summary": content
            }
        else:
            return {
                "status": "error",
                "summary": f"OpenAI API error: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "summary": f"AI analysis failed: {str(e)}"
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
    """Find Salesforce contact with enhanced data"""
    if not access_token:
        return None, "No access token"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Enhanced query to get contact + account info
        query = f"SELECT Id, Name, Email, AccountId, Account.Name, Account.Description FROM Contact WHERE Name LIKE '%{prospect_name}%' LIMIT 5"
        
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
                return {
                    'contact_id': contact['Id'],
                    'contact_name': contact['Name'],
                    'account_id': contact.get('AccountId'),
                    'company_name': contact.get('Account', {}).get('Name') if contact.get('Account') else None,
                    'company_description': contact.get('Account', {}).get('Description') if contact.get('Account') else None
                }, f"✅ Found contact: {contact['Name']}"
            else:
                return None, f"⚠️ No contact found for: {prospect_name}"
        else:
            return None, f"❌ Contact search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Contact search error: {e}"

def find_or_update_salesforce_event(contact_data, prospect_name, fellow_id, access_token):
    """Find and update Salesforce event"""
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
                fellow_url = f"https://telnyx.fellow.app/recordings/{fellow_id}"
                
                update_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/sobjects/Event/{event_id}"
                update_data = {
                    'Description': f"Telnyx Intro Call with {prospect_name}\\n\\n📞 Fellow Recording: {fellow_url}\\n\\n✅ Processed by V1 Enhanced Intelligence - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

def format_enhanced_slack_alert(call_data, contact_data, event_id, ai_analysis):
    """Format enhanced Slack alert with all features"""
    title = call_data.get('title', 'Unknown Call')
    call_id = call_data.get('id', 'unknown')
    created_at = call_data.get('created_at', '')
    
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    # Base alert
    alert = f"""🔔 *New Telnyx Intro Call - Enhanced Analysis*

*Prospect*: {prospect_name}
*Date*: {created_at[:10] if created_at else 'Unknown'}
*Fellow ID*: `{call_id}`

📞 *Recording*: <https://telnyx.fellow.app/recordings/{call_id}|View in Fellow>"""

    # Add company info if available
    if contact_data and contact_data.get('company_name'):
        company_name = contact_data['company_name']
        company_desc = contact_data.get('company_description', f"{company_name} - Telecommunications prospect")
        # Limit description to one sentence
        if company_desc:
            first_sentence = company_desc.split('.')[0][:100] + ('...' if len(company_desc) > 100 else '')
            alert += f"\\n🏢 *Company*: {first_sentence}"
    
    # Add AI analysis
    alert += f"\\n\\n---\\n\\n🤖 *CALL ANALYSIS*:"
    
    if ai_analysis.get('status') == 'success':
        alert += f"\\n{ai_analysis['summary']}"
    else:
        alert += f"\\n❌ {ai_analysis['summary']}\\n\\n*📋 Manual review recommended for detailed insights*"
    
    # Add Salesforce links  
    alert += f"\\n\\n---\\n\\n🔗 *SALESFORCE*:"
    
    if contact_data:
        contact_id = contact_data['contact_id'] 
        sf_base = "https://telnyx.lightning.force.com/lightning/r"
        
        alert += f"\\n👤 <{sf_base}/Contact/{contact_id}/view|View Contact>"
        
        if contact_data.get('account_id'):
            account_id = contact_data['account_id']
            alert += f"\\n🏢 <{sf_base}/Account/{account_id}/view|View Account>"
            
        if event_id:
            alert += f"\\n📅 <{sf_base}/Event/{event_id}/view|View Event>"
    else:
        alert += f"\\n⚠️ Contact not found - manual Salesforce linking needed"
    
    # Footer
    alert += f"""\\n\\n---

✅ *Status*: Ready for AE follow-up
🔄 *System*: V1 Enhanced Intelligence
⏰ *Posted*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    return alert

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

def is_call_processed(call_id):
    """Check if call already processed"""
    db_path = 'v1_enhanced.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            fellow_id TEXT UNIQUE,
            prospect_name TEXT,
            processed_at TEXT,
            slack_posted BOOLEAN DEFAULT FALSE,
            salesforce_updated BOOLEAN DEFAULT FALSE,
            ai_analyzed BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('SELECT * FROM processed_calls WHERE fellow_id = ?', (call_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success):
    """Mark call as processed with enhanced tracking"""
    db_path = 'v1_enhanced.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (fellow_id, prospect_name, processed_at, slack_posted, salesforce_updated, ai_analyzed)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), slack_success, sf_success, ai_success))
    
    conn.commit()
    conn.close()

def run_enhanced_automation():
    """Run ENHANCED V1 automation"""
    log_message("🚀 V1 ENHANCED Call Intelligence - Fellow + AI Analysis + Enhanced Slack + Salesforce")
    
    calls, status = get_fellow_intro_calls()
    log_message(f"📞 Fellow: {status}")
    
    if not calls:
        log_message("😴 No calls found")
        return
    
    processed_count = 0
    
    # Get Salesforce token once
    access_token, auth_msg = get_salesforce_token()
    log_message(f"🏢 Salesforce: {auth_msg}")
    
    for call in calls:
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        if is_call_processed(call_id):
            continue
            
        if '(' in title and ')' in title:
            prospect_name = title.split('(')[1].split(')')[0]
        else:
            prospect_name = 'Unknown'
        
        log_message(f"🆕 Processing ENHANCED: {prospect_name}")
        
        # Step 1: Get transcript and run AI analysis
        transcript, transcript_msg = get_fellow_transcript(call_id)
        log_message(f"   📝 Transcript: {transcript_msg}")
        
        ai_analysis = analyze_call_with_ai(transcript, prospect_name)
        ai_success = ai_analysis.get('status') == 'success'
        log_message(f"   🤖 AI Analysis: {ai_analysis.get('status')}")
        
        # Step 2: Find Salesforce contact with enhanced data
        contact_data = None
        if access_token:
            contact_data, contact_msg = find_salesforce_contact_enhanced(prospect_name, access_token)
            log_message(f"   👤 Contact: {contact_msg}")
        
        # Step 3: Update Salesforce event
        event_id = None
        sf_success = False
        if contact_data and access_token:
            event_id, event_msg = find_or_update_salesforce_event(contact_data, prospect_name, call_id, access_token)
            sf_success = event_id is not None
            log_message(f"   📅 Event: {event_msg}")
        
        # Step 4: Generate enhanced Slack alert
        alert = format_enhanced_slack_alert(call, contact_data, event_id, ai_analysis)
        
        # Step 5: Post to Slack
        slack_success, slack_msg = post_to_slack_bot_api(alert)
        log_message(f"   📱 Slack: {slack_msg}")
        
        # Step 6: Mark as processed
        mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success)
        
        processed_count += 1
        log_message(f"✅ ENHANCED: {prospect_name} (Slack: {'✅' if slack_success else '❌'}, SF: {'✅' if sf_success else '❌'}, AI: {'✅' if ai_success else '❌'})")
        
        if processed_count >= 3:
            break
    
    if processed_count == 0:
        log_message("😴 No new calls to process")
    else:
        log_message(f"🎉 V1 ENHANCED processed {processed_count} calls")

if __name__ == "__main__":
    try:
        run_enhanced_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)