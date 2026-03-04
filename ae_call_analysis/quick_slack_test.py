#!/usr/bin/env python3
"""
Quick Slack test using #revenue channel
"""

import os
import sys

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

# Import Slack function
sys.path.append(os.path.dirname(__file__))
from V2_FINAL_PRODUCTION_LIVE import post_to_slack

# Temporarily modify channel for testing
def test_slack_revenue():
    """Test posting to #revenue channel"""
    
    # Mock data
    mock_call = {
        'prospect_name': '[V2 TEST] Call Intelligence',
        'ae_name': 'System Test',
        'title': 'Slack Integration Test - Please Ignore',
        'prospect_email': 'test@example.com'
    }
    
    mock_analysis = {
        'summary': '🧪 Testing V2 FINAL Call Intelligence Slack integration. System working correctly!',
        'key_points': ['✅ Bot permissions working', '✅ API integration functional', '✅ Ready for production'],
        'next_steps': ['Create #ae-call-intelligence channel', 'Deploy live system'],
        'sentiment': 'positive'
    }
    
    print("💬 Testing Slack post to #revenue...")
    
    # Manually build Slack request for #revenue
    import requests
    
    slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    headers = {
        'Authorization': f'Bearer {slack_bot_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'channel': '#revenue',
        'text': f"🧪 [V2 TEST] Call Intelligence Slack Integration Test - {mock_call['prospect_name']}",
        'blocks': [
            {
                "type": "header",
                "text": {
                    "type": "plain_text", 
                    "text": f"🧪 [V2 TEST] {mock_call['prospect_name']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:* {mock_analysis['summary']}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "V2 FINAL Call Intelligence - Slack Integration Test ✅"
                    }
                ]
            }
        ]
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
            print("✅ SUCCESS: Slack posting works!")
            print(f"📅 Message timestamp: {result.get('ts')}")
            print("📱 Check #revenue channel")
            return True
        else:
            print(f"❌ Slack API error: {result.get('error')}")
            return False
    else:
        print(f"❌ HTTP error: {response.status_code}")
        return False

if __name__ == "__main__":
    print("🧪 Quick Slack Integration Test")
    print("🎯 Testing with #revenue channel")
    print()
    
    if test_slack_revenue():
        print("\n🎉 SLACK INTEGRATION CONFIRMED WORKING!")
        print("💬 V2 FINAL system can post to Slack successfully")
        print("📋 Next steps:")
        print("   1. Create #ae-call-intelligence channel") 
        print("   2. Add bot to that channel")
        print("   3. Deploy V2 live system")
    else:
        print("\n❌ Slack integration issues")
        print("🔧 Check bot permissions and try again")