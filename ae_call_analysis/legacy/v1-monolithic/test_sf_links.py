#!/usr/bin/env python3
"""
Test Salesforce links in Slack messages
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

def test_salesforce_links():
    """Test Slack posting with Salesforce links"""
    print("🧪 Testing Salesforce Links in Slack Messages")
    print("=" * 50)
    
    # Import functions from enhanced version
    sys.path.append(os.path.dirname(__file__))
    from V2_LIVE_SALES_CALLS_WITH_SF import lookup_salesforce_prospect, post_to_slack
    
    # Mock call data
    mock_call = {
        'prospect_name': '[SF TEST] Test Prospect',
        'prospect_email': 'test@acme.com',
        'ae_name': 'Test AE',
        'title': 'Demo Call - Salesforce Links Test',
        'call_date': '2026-03-04'
    }
    
    # Mock analysis
    mock_analysis = {
        'summary': 'Testing Salesforce links in V2 FINAL Call Intelligence Slack messages.',
        'key_points': ['✅ Salesforce lookup working', '✅ Links in Slack messages', '✅ Ready for production'],
        'next_steps': ['Deploy enhanced system', 'Verify links work in Slack'],
        'sentiment': 'positive'
    }
    
    print("🔗 Testing Salesforce lookup...")
    sf_lookup = lookup_salesforce_prospect(mock_call['prospect_name'], mock_call['prospect_email'])
    
    if sf_lookup['found']:
        print(f"✅ Salesforce lookup successful:")
        print(f"   🔍 URL: {sf_lookup['search_url']}")
        print(f"   📱 Display: {sf_lookup['display_text']}")
    else:
        print("❌ Salesforce lookup failed")
        return False
    
    print("\n💬 Testing Slack message with Salesforce links...")
    
    slack_ts = post_to_slack(mock_call, mock_analysis)
    
    if slack_ts:
        print("✅ SUCCESS: Slack message posted with Salesforce links!")
        print(f"📅 Slack timestamp: {slack_ts}")
        print("📱 Check #sales-calls channel for message with clickable Salesforce links")
        return True
    else:
        print("❌ FAILED: Slack posting failed")
        return False

if __name__ == "__main__":
    print("🚀 V2 FINAL Salesforce Links Test")
    print()
    
    if test_salesforce_links():
        print("\n🎉 SALESFORCE LINKS TEST PASSED!")
        print("🔗 V2 system now includes clickable Salesforce links")
        print("🚀 Ready to deploy enhanced version")
    else:
        print("\n❌ SALESFORCE LINKS TEST FAILED!")
        print("🔧 Check configuration and try again")
        sys.exit(1)