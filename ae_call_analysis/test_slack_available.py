#!/usr/bin/env python3
"""
Test Slack posting to an available channel where bot is member
"""

import os
import requests
import sys

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

def find_available_channel():
    """Find a channel where the bot is already a member"""
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return None
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'https://slack.com/api/conversations.list',
        headers=headers,
        params={'types': 'public_channel,private_channel', 'limit': 100}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            channels = result.get('channels', [])
            
            # Find channels where bot is member
            member_channels = [ch for ch in channels if ch.get('is_member', False)]
            
            print(f"📋 Bot is member of {len(member_channels)} channels:")
            for ch in member_channels:
                print(f"   ✅ #{ch.get('name')}")
            
            if member_channels:
                # Use first available channel for testing
                return member_channels[0].get('name')
    
    return None

def test_posting_to_available_channel():
    """Test posting to any available channel"""
    channel = find_available_channel()
    
    if not channel:
        print("❌ No channels found where bot is member")
        print("💡 Add bot to a channel first:")
        print("   1. Go to Slack channel")
        print("   2. Type: /invite @your-bot-name")
        print("   3. Or create #ae-call-intelligence and add bot")
        return False
    
    print(f"🎯 Testing with channel: #{channel}")
    
    # Import Slack function and modify it for testing
    sys.path.append(os.path.dirname(__file__))
    from V2_FINAL_PRODUCTION_LIVE import post_to_slack
    
    # Mock data
    mock_call = {
        'prospect_name': '[TEST] V2 Call Intelligence Test',
        'ae_name': 'System Test',
        'title': 'Slack Integration Verification',
        'prospect_email': 'test@example.com'
    }
    
    mock_analysis = {
        'summary': 'This is a test message to verify V2 FINAL Call Intelligence Slack integration is working properly.',
        'key_points': ['✅ Slack posting functional', '✅ Bot permissions correct', '✅ Ready for production'],
        'next_steps': ['Deploy live system', 'Monitor call processing'],
        'sentiment': 'positive'
    }
    
    # Temporarily patch the channel in the post_to_slack function
    import importlib
    import V2_FINAL_PRODUCTION_LIVE
    
    # Reload module with modified channel
    original_code = open('V2_FINAL_PRODUCTION_LIVE.py', 'r').read()
    modified_code = original_code.replace('channel = "#ae-call-intelligence"', f'channel = "#{channel}"')
    
    with open('temp_slack_test.py', 'w') as f:
        f.write(modified_code)
    
    sys.path.insert(0, os.getcwd())
    import temp_slack_test
    
    print(f"💬 Posting test message to #{channel}...")
    
    slack_ts = temp_slack_test.post_to_slack(mock_call, mock_analysis)
    
    # Clean up temp file
    import os
    os.remove('temp_slack_test.py')
    
    if slack_ts:
        print("✅ SUCCESS: Slack posting works!")
        print(f"📅 Message timestamp: {slack_ts}")
        print(f"📱 Check #{channel} channel")
        return True
    else:
        print("❌ FAILED: Slack posting failed")
        return False

if __name__ == "__main__":
    print("🧪 V2 FINAL Slack Integration Test (Available Channels)")
    print("=" * 55)
    
    if test_posting_to_available_channel():
        print("\n🎉 SLACK INTEGRATION WORKING!")
        print("💬 V2 FINAL system can post to Slack successfully")
        print("🔧 To use #ae-call-intelligence:")
        print("   1. Create the channel in Slack")
        print("   2. Add the bot: /invite @your-bot-name")
        print("   3. V2 system will work end-to-end")
    else:
        print("\n❌ SLACK INTEGRATION ISSUES")
        print("🔧 Fix bot permissions first")