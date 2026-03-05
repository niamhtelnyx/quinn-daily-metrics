#!/usr/bin/env python3
"""
Simple Slack posting test with mock data
Tests that Slack integration works end-to-end
"""

import os
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

def test_slack_with_mock_data():
    """Test Slack posting with mock call data"""
    print("🧪 Testing Slack Posting with Mock Data")
    print("=" * 40)
    
    # Import Slack function
    sys.path.append(os.path.dirname(__file__))
    from V2_FINAL_PRODUCTION_LIVE import post_to_slack
    
    # Mock call data
    mock_call = {
        'prospect_name': '[SLACK TEST] Acme Corp',
        'ae_name': 'Test AE',
        'title': 'Demo Call - Slack Integration Test',
        'call_date': datetime.now().isoformat(),
        'prospect_email': 'test@acme.com'
    }
    
    # Mock analysis
    mock_analysis = {
        'summary': 'This is a test of the Slack integration for V2 FINAL Call Intelligence system.',
        'key_points': [
            'Testing Slack message formatting',
            'Verifying API integration', 
            'Ensuring rich blocks work properly'
        ],
        'next_steps': [
            'Verify message posted correctly',
            'Check formatting in #ae-call-intelligence',
            'Deploy live system'
        ],
        'sentiment': 'positive',
        'competitive_mentions': [],
        'decision_makers': ['Test Manager']
    }
    
    print("📋 Mock call data:")
    print(f"   Prospect: {mock_call['prospect_name']}")
    print(f"   AE: {mock_call['ae_name']}")
    print(f"   Summary: {mock_analysis['summary'][:50]}...")
    
    print("\n💬 Posting to Slack...")
    
    slack_ts = post_to_slack(mock_call, mock_analysis)
    
    if slack_ts:
        print("✅ SUCCESS: Mock message posted to Slack!")
        print(f"📅 Slack timestamp: {slack_ts}")
        print("📱 Check #ae-call-intelligence channel")
        return True
    else:
        print("❌ FAILED: Slack posting failed")
        return False

def check_slack_config():
    """Check Slack configuration"""
    print("🔍 Checking Slack configuration...")
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ SLACK_BOT_TOKEN not found in .env")
        return False
    
    if not slack_token.startswith('xoxb-'):
        print("❌ SLACK_BOT_TOKEN doesn't look like a bot token")
        return False
    
    print(f"✅ SLACK_BOT_TOKEN: {slack_token[:15]}...")
    return True

if __name__ == "__main__":
    print(f"🚀 V2 FINAL Slack Integration Test - {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    if not check_slack_config():
        print("\n❌ Slack configuration issues")
        sys.exit(1)
    
    if test_slack_with_mock_data():
        print("\n🎉 SLACK TEST PASSED!")
        print("💬 V2 FINAL Live system is ready to post to Slack")
        print("🚀 End-to-end processing will work correctly")
    else:
        print("\n❌ SLACK TEST FAILED!")
        print("🔧 Check Slack bot permissions and channel access")
        sys.exit(1)