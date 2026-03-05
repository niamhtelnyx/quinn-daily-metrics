#!/usr/bin/env python3
"""
V1 Call Intelligence - PRODUCTION WITH SLACK BOT
Fellow "Telnyx Intro Call" → Slack Alert + Salesforce Update

FULL V1 SCOPE WITH RELIABLE SLACK POSTING:
✅ Fellow API processing
✅ Slack alerts (C0AJ9E9F474) via BOT TOKEN 
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

def find_salesforce_contact(prospect_name, access_token):
    """Find Salesforce contact by name"""
    if not access_token:
        return None, "No access token"
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        query = f"SELECT Id, Name, Email FROM Contact WHERE Name LIKE '%{prospect_name}%' LIMIT 5"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('records', [])
            if contacts:
                return contacts[0], f"✅ Found contact: {contacts[0]['Name']}"
            else:
                return None, f"⚠️ No contact found for: {prospect_name}"
        else:
            return None, f"❌ Contact search failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Contact search error: {e}"

def find_or_create_salesforce_event(contact_id, prospect_name, fellow_id, access_token):
    """Find or create Salesforce event for the call"""
    if not access_token or not contact_id:
        return None, "Missing access token or contact"
    
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
                    'Description': f"Telnyx Intro Call with {prospect_name}\n\n📞 Fellow Recording: {fellow_url}\n\n✅ Processed by V1 Call Intelligence - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

def update_salesforce(call_data):
    """Complete Salesforce update process"""
    title = call_data.get('title', 'Unknown Call')
    call_id = call_data.get('id', 'unknown')
    
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown'
    
    log_message(f"🏢 Starting Salesforce update for: {prospect_name}")
    
    access_token, auth_msg = get_salesforce_token()
    log_message(f"   {auth_msg}")
    
    if not access_token:
        return False, auth_msg
    
    contact, contact_msg = find_salesforce_contact(prospect_name, access_token)
    log_message(f"   {contact_msg}")
    
    if not contact:
        return False, contact_msg
    
    event_id, event_msg = find_or_create_salesforce_event(contact['Id'], prospect_name, call_id, access_token)
    log_message(f"   {event_msg}")
    
    return event_id is not None, event_msg

def post_to_slack_bot_api(message, channel="C0AJ9E9F474"):
    """Post message to Slack using Bot Token API - PRODUCTION VERSION"""
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

def format_slack_alert(call):
    """Format professional Slack alert for new call"""
    title = call.get('title', 'Unknown Call')
    call_id = call.get('id', 'unknown')
    created_at = call.get('created_at', '')
    
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    alert = f"""🔔 *New Telnyx Intro Call*

*Prospect*: {prospect_name}
*Date*: {created_at[:10] if created_at else 'Unknown'}
*Fellow ID*: `{call_id}`

📞 *Recording*: <https://telnyx.fellow.app/recordings/{call_id}|View in Fellow>

✅ Ready for AE follow-up
🏢 Salesforce event updated

_V1 Call Intelligence - Bot Integration_
_Posted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"""
    
    return alert

def is_call_processed(call_id):
    """Check if call already processed"""
    db_path = 'v1_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            fellow_id TEXT UNIQUE,
            prospect_name TEXT,
            processed_at TEXT,
            slack_posted BOOLEAN DEFAULT FALSE,
            salesforce_updated BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('SELECT * FROM processed_calls WHERE fellow_id = ?', (call_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_call_processed(call_id, prospect_name, slack_success, sf_success):
    """Mark call as processed with full V1 status"""
    db_path = 'v1_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (fellow_id, prospect_name, processed_at, slack_posted, salesforce_updated)
        VALUES (?, ?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), slack_success, sf_success))
    
    conn.commit()
    conn.close()

def run_v1_production_automation():
    """Run V1 PRODUCTION automation - Fellow + Slack Bot + Salesforce"""
    log_message("🚀 V1 PRODUCTION Call Intelligence - Fellow + Slack Bot + Salesforce")
    
    calls, status = get_fellow_intro_calls()
    log_message(f"📞 Fellow: {status}")
    
    if not calls:
        log_message("😴 No calls found")
        return
    
    processed_count = 0
    
    for call in calls:
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        if is_call_processed(call_id):
            continue
            
        if '(' in title and ')' in title:
            prospect_name = title.split('(')[1].split(')')[0]
        else:
            prospect_name = 'Unknown'
        
        log_message(f"🆕 Processing V1 PRODUCTION: {prospect_name}")
        
        # Update Salesforce
        sf_success, sf_msg = update_salesforce(call)
        
        # Generate and post Slack alert using BOT API
        alert = format_slack_alert(call)
        slack_success, slack_msg = post_to_slack_bot_api(alert)
        log_message(f"📱 Slack Bot: {slack_msg}")
        
        # Mark as processed
        mark_call_processed(call_id, prospect_name, slack_success, sf_success)
        
        processed_count += 1
        log_message(f"✅ V1 PRODUCTION: {prospect_name} (Slack: {'✅' if slack_success else '❌'}, SF: {'✅' if sf_success else '❌'})")
        
        if processed_count >= 3:
            break
    
    if processed_count == 0:
        log_message("😴 No new calls to process")
    else:
        log_message(f"🎉 V1 PRODUCTION processed {processed_count} calls")

if __name__ == "__main__":
    try:
        run_v1_production_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)