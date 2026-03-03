#!/usr/bin/env python3
"""
V1 Call Intelligence - Production Automation
Fellow "Telnyx Intro Call" → Slack Alert (C0AJ9E9F474)

This is the clean, production-ready V1 automation script.
Runs every 30 minutes via cron to process new Fellow intro calls.
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

def format_slack_alert(call):
    """Format professional Slack alert for new call"""
    title = call.get('title', 'Unknown Call')
    call_id = call.get('id', 'unknown')
    created_at = call.get('created_at', '')
    
    # Extract prospect name from title
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    alert = f"""🔔 **New Telnyx Intro Call**

**Prospect**: {prospect_name}
**Date**: {created_at[:10] if created_at else 'Unknown'}
**Fellow ID**: {call_id}

📞 **Recording**: https://telnyx.fellow.app/recordings/{call_id}

✅ Ready for AE follow-up

_V1 Call Intelligence - Automated Processing_"""
    
    return alert

def post_to_slack(message):
    """Post message to Slack channel C0AJ9E9F474"""
    # Try webhook method first
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if webhook_url and not webhook_url.startswith('#') and 'your-webhook' not in webhook_url:
        try:
            payload = {"text": message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True, "Posted via webhook"
        except Exception as e:
            log_message(f"Webhook failed: {e}")
    
    # Try Clawdbot gateway method
    try:
        gateway_url = "http://localhost:18789"
        payload = {
            "action": "send",
            "channel": "slack",
            "target": "C0AJ9E9F474",  # Target Slack channel
            "message": message
        }
        
        response = requests.post(
            f"{gateway_url}/api/message",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201, 202]:
            return True, "Posted via Clawdbot"
    except Exception as e:
        log_message(f"Clawdbot gateway failed: {e}")
    
    # Fallback: Save to file for manual posting
    timestamp = datetime.now().strftime('%H%M%S')
    filename = f'v1_alert_ready_{timestamp}.txt'
    with open(filename, 'w') as f:
        f.write(message)
    return False, f"Saved to {filename} for manual posting"

def is_call_processed(call_id):
    """Check if call already processed"""
    db_path = 'v1_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            fellow_id TEXT UNIQUE,
            prospect_name TEXT,
            processed_at TEXT,
            slack_posted BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('SELECT * FROM processed_calls WHERE fellow_id = ?', (call_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_call_processed(call_id, prospect_name, slack_success):
    """Mark call as processed in database"""
    db_path = 'v1_production.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (fellow_id, prospect_name, processed_at, slack_posted)
        VALUES (?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), slack_success))
    
    conn.commit()
    conn.close()

def run_v1_automation():
    """Run V1 automation - main entry point"""
    log_message("🚀 V1 Call Intelligence Starting")
    
    # Get Fellow calls
    calls, status = get_fellow_intro_calls()
    log_message(f"📞 Fellow: {status}")
    
    if not calls:
        log_message("😴 No calls found")
        return
    
    processed_count = 0
    
    # Process each call
    for call in calls:
        call_id = call.get('id')
        title = call.get('title', 'Unknown')
        
        # Check if already processed
        if is_call_processed(call_id):
            continue
            
        # Extract prospect name
        if '(' in title and ')' in title:
            prospect_name = title.split('(')[1].split(')')[0]
        else:
            prospect_name = 'Unknown'
        
        log_message(f"🆕 Processing new call: {prospect_name}")
        
        # Generate Slack alert
        alert = format_slack_alert(call)
        
        # Post to Slack
        slack_success, slack_msg = post_to_slack(alert)
        log_message(f"📱 Slack: {slack_msg}")
        
        # Mark as processed
        mark_call_processed(call_id, prospect_name, slack_success)
        
        processed_count += 1
        log_message(f"✅ Processed: {prospect_name}")
        
        # Limit to 3 calls per run to avoid spam
        if processed_count >= 3:
            break
    
    if processed_count == 0:
        log_message("😴 No new calls to process")
    else:
        log_message(f"🎉 Processed {processed_count} new calls")

if __name__ == "__main__":
    try:
        run_v1_automation()
    except Exception as e:
        log_message(f"❌ Error: {e}")
        sys.exit(1)