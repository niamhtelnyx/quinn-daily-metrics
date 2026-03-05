#!/usr/bin/env python3
"""
Test posting to #sales-calls channel
"""

import os
import requests

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def test_sales_calls_post():
    """Test posting to #sales-calls"""
    slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    headers = {
        'Authorization': f'Bearer {slack_bot_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'channel': '#sales-calls',
        'text': '🧪 [TEST] V2 Call Intelligence - Testing #sales-calls access',
        'blocks': [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 [TEST] V2 Call Intelligence"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Testing access to #sales-calls channel for call intelligence alerts."
                }
            }
        ]
    }
    
    print("💬 Testing post to #sales-calls...")
    
    response = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers=headers,
        json=payload,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print("✅ SUCCESS: Can post to #sales-calls!")
            return True
        else:
            error = result.get('error')
            print(f"❌ Slack API error: {error}")
            
            if error == 'channel_not_found':
                print("💡 Solutions:")
                print("   1. Create #sales-calls channel")
                print("   2. Add bot to existing #sales-calls channel")
                print("   3. Check if channel exists but bot lacks access")
            
            return False
    else:
        print(f"❌ HTTP error: {response.status_code}")
        return False

if __name__ == "__main__":
    print("🎯 Testing #sales-calls channel access...")
    test_sales_calls_post()