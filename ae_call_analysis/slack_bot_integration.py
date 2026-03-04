#!/usr/bin/env python3
"""
Slack Bot API Integration for V1 Call Intelligence
Direct posting using bot token - more reliable than localhost gateway
"""

import requests
import json
import os
from datetime import datetime

def load_env():
    """Load environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def post_to_slack_bot_api(message, channel="C0AJ9E9F474"):
    """
    Post message to Slack using Bot Token API
    
    Args:
        message (str): Message text to post
        channel (str): Slack channel ID (default: C0AJ9E9F474)
    
    Returns:
        tuple: (success_bool, response_message)
    """
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        return False, "❌ SLACK_BOT_TOKEN not found in environment"
    
    if not bot_token.startswith('xoxb-'):
        return False, "❌ Invalid bot token format (should start with 'xoxb-')"
    
    try:
        # Slack API endpoint
        url = "https://slack.com/api/chat.postMessage"
        
        # Headers with bot token
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        # Message payload
        payload = {
            "channel": channel,
            "text": message,
            "unfurl_links": True,
            "unfurl_media": True
        }
        
        # Make API call
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        # Parse response
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
            
    except requests.exceptions.Timeout:
        return False, "❌ Slack API timeout (15s)"
    except requests.exceptions.ConnectionError:
        return False, "❌ Network connection error"
    except Exception as e:
        return False, f"❌ Unexpected error: {str(e)}"

def test_bot_connection():
    """Test bot token and permissions"""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        return False, "No bot token configured"
    
    try:
        url = "https://slack.com/api/auth.test"
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        response = requests.post(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_id = data.get('bot_id', 'unknown')
                team = data.get('team', 'unknown')
                return True, f"✅ Bot authenticated: {bot_id} on {team}"
            else:
                return False, f"❌ Auth failed: {data.get('error')}"
        else:
            return False, f"❌ HTTP error: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {e}"

def format_rich_slack_message(call_data):
    """
    Format rich Slack message with bot API features
    
    Args:
        call_data (dict): Fellow call data
        
    Returns:
        str: Formatted message
    """
    title = call_data.get('title', 'Unknown Call')
    call_id = call_data.get('id', 'unknown')
    created_at = call_data.get('created_at', '')
    
    # Extract prospect name
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    # Rich formatted message using bot API
    message = f"""🔔 *New Telnyx Intro Call*

*Prospect*: {prospect_name}
*Date*: {created_at[:10] if created_at else 'Unknown'}
*Fellow ID*: `{call_id}`

📞 *Recording*: <https://telnyx.fellow.app/recordings/{call_id}|View in Fellow>

✅ Ready for AE follow-up
🏢 Salesforce event updated

_V1 Call Intelligence - Bot Integration_
_Posted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"""
    
    return message

def main():
    """Test the Slack bot integration"""
    load_env()
    
    print("🤖 SLACK BOT INTEGRATION TEST")
    print("=" * 40)
    
    # Test 1: Bot authentication
    print("1. Testing bot authentication...")
    auth_success, auth_msg = test_bot_connection()
    print(f"   {auth_msg}")
    
    if not auth_success:
        print("\n❌ Cannot proceed without valid bot token")
        print("\nTo fix:")
        print("1. Get bot token from https://api.slack.com/apps")
        print("2. Add to .env: SLACK_BOT_TOKEN=xoxb-your-token-here")
        return
    
    # Test 2: Test message posting
    print("\n2. Testing message posting...")
    test_message = f"🧪 Bot Integration Test\n\n**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Status**: V1 Call Intelligence bot working!"
    
    success, msg = post_to_slack_bot_api(test_message)
    print(f"   {msg}")
    
    if success:
        print("\n🎉 Bot integration working perfectly!")
        print("✅ Ready to integrate into production script")
    else:
        print("\n❌ Bot posting failed - check token permissions")

if __name__ == "__main__":
    main()