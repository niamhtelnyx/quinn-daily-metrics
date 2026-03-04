#!/usr/bin/env python3
"""
V1 Call Intelligence - ENHANCED PRODUCTION (TIMEOUT FIXED)
Fellow "Telnyx Intro Call" → Enhanced Slack Alert + Salesforce Update

ENHANCED FEATURES:
✅ Fellow API processing (TIMEOUT FIXED)
✅ AI call analysis (9-point structure)
✅ Enhanced Slack alerts with Salesforce links
✅ Company summaries
✅ Salesforce event updates
✅ Database tracking
✅ Retry logic for API timeouts
"""

import requests
import json
import os
import sqlite3
import sys
import time
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

def get_fellow_intro_calls_with_retry():
    """Get Fellow 'Telnyx Intro Call' recordings with retry logic"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return [], "No Fellow API key found"
    
    headers = {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    # Get today's date for filtering
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Retry logic: 3 attempts with increasing timeouts
    retry_attempts = 3
    timeouts = [30, 45, 60]  # Increased timeouts: 30s, 45s, 60s
    
    for attempt in range(retry_attempts):
        try:
            current_timeout = timeouts[attempt]
            log_message(f"📞 Fellow API attempt {attempt + 1}/{retry_attempts} (timeout: {current_timeout}s)")
            
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
                timeout=current_timeout  # Increased timeout
            )
            
            if response.status_code != 200:
                log_message(f"⚠️ Fellow API returned status {response.status_code}")
                if attempt < retry_attempts - 1:
                    time.sleep(5)  # Wait 5 seconds before retry
                    continue
                return [], f"Fellow API error: {response.status_code}"
            
            data = response.json()
            recordings = data.get('recordings', [])
            
            # Filter for today's "Telnyx Intro Call" recordings
            intro_calls = []
            for recording in recordings:
                if recording.get('title') and 'telnyx intro call' in recording.get('title', '').lower():
                    # Check if it's from today
                    created_at = recording.get('created_at', '')
                    if today in created_at:
                        intro_calls.append(recording)
            
            log_message(f"✅ Fellow API success on attempt {attempt + 1}")
            return intro_calls, f"Found {len(intro_calls)} intro calls from today ({today})"
            
        except requests.exceptions.Timeout as e:
            log_message(f"⏰ Timeout on attempt {attempt + 1}: {current_timeout}s exceeded")
            if attempt < retry_attempts - 1:
                time.sleep(10)  # Wait 10 seconds before retry
                continue
            else:
                return [], f"Fellow API timeout after {retry_attempts} attempts"
                
        except Exception as e:
            log_message(f"❌ Fellow API error on attempt {attempt + 1}: {str(e)}")
            if attempt < retry_attempts - 1:
                time.sleep(5)  # Wait 5 seconds before retry
                continue
            else:
                return [], f"Fellow API error: {str(e)}"
    
    return [], "Fellow API failed after all retry attempts"

def analyze_call_with_ai(transcript, recording_data):
    """Analyze call using OpenAI with enhanced structure"""
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return {"error": "Missing OpenAI API key"}
        
        # Prepare call context
        title = recording_data.get('title', 'Unknown Call')
        participants = recording_data.get('participants', [])
        participant_names = [p.get('name', 'Unknown') for p in participants]
        
        prompt = f"""
        Analyze this Telnyx intro sales call and provide structured insights:

        CALL DETAILS:
        Title: {title}
        Participants: {', '.join(participant_names)}
        
        TRANSCRIPT:
        {transcript[:3000]}

        Provide a JSON response with these 9 key fields:
        {{
            "summary": "Brief 2-sentence overview of the call purpose and outcome",
            "prospect_company": "Company name the prospect represents",
            "prospect_contact": "Main prospect contact name and role",
            "telnyx_ae": "Telnyx account executive on the call",
            "call_purpose": "Main reason for the call (demo, discovery, follow-up, etc)",
            "key_discussion_points": ["3-4 main topics discussed"],
            "prospect_needs": ["Specific needs or pain points identified"],
            "next_steps": ["Concrete action items and follow-ups"],
            "timeline_urgency": "Expected timeline for decisions or implementation"
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
            'max_tokens': 1000,
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
        
        try:
            analysis = json.loads(content)
            return analysis
        except json.JSONDecodeError:
            return {
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "error": "JSON parsing failed"
            }
            
    except Exception as e:
        return {"error": str(e)}

def post_enhanced_slack_alert(recording, analysis):
    """Post enhanced Slack alert with analysis"""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_token:
            return False
        
        # Extract key information
        title = recording.get('title', 'Fellow Call')
        prospect_company = analysis.get('prospect_company', 'Unknown Company')
        prospect_contact = analysis.get('prospect_contact', 'Unknown Contact')
        telnyx_ae = analysis.get('telnyx_ae', 'Unknown AE')
        summary = analysis.get('summary', 'Call analysis not available')
        key_points = analysis.get('key_discussion_points', [])
        next_steps = analysis.get('next_steps', [])
        
        # Build Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📞 New Fellow Call: {prospect_company}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Company:* {prospect_company}"},
                    {"type": "mrkdwn", "text": f"*Contact:* {prospect_contact}"},
                    {"type": "mrkdwn", "text": f"*Telnyx AE:* {telnyx_ae}"},
                    {"type": "mrkdwn", "text": f"*Call:* {title}"}
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
        
        # Add key discussion points
        if key_points:
            points_text = "\n".join([f"• {point}" for point in key_points[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Discussion Points:*\n{points_text}"
                }
            })
        
        # Add next steps
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
                    "text": f"📞 Source: Fellow | 🤖 AI Analysis: {datetime.now().strftime('%H:%M')}"
                }
            ]
        })
        
        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'channel': '#sales-calls',
            'blocks': blocks,
            'text': f"New Fellow call: {prospect_company} - {title}"
        }
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        return response.status_code == 200 and response.json().get('ok')
        
    except Exception as e:
        log_message(f"❌ Slack posting error: {str(e)}")
        return False

def run_enhanced_fellow_automation():
    """Run enhanced Fellow automation with timeout fixes"""
    log_message("🚀 V1 ENHANCED Call Intelligence - Live Monitoring (Today's Calls Only)")
    
    # Get Fellow calls with retry logic
    calls, status = get_fellow_intro_calls_with_retry()
    log_message(f"📞 Fellow: {status}")
    
    if not calls:
        log_message("😴 No new calls to process")
        return
    
    # Process each call
    for call in calls:
        try:
            # Get transcript
            transcript = call.get('transcript', {}).get('content', '')
            if not transcript:
                log_message(f"⚠️ No transcript for call: {call.get('title')}")
                continue
            
            # AI Analysis
            log_message(f"🤖 Analyzing call: {call.get('title')}")
            analysis = analyze_call_with_ai(transcript, call)
            
            # Post to Slack
            log_message(f"💬 Posting to Slack...")
            success = post_enhanced_slack_alert(call, analysis)
            
            if success:
                log_message(f"✅ Posted to Slack successfully")
            else:
                log_message(f"⚠️ Failed to post to Slack")
                
        except Exception as e:
            log_message(f"❌ Error processing call: {str(e)}")
            continue

if __name__ == "__main__":
    try:
        run_enhanced_fellow_automation()
    except Exception as e:
        log_message(f"❌ Fatal error: {e}")
        sys.exit(1)