#!/usr/bin/env python3
"""
V1 Fixed - Working E2E Call Intelligence
Fellow "Telnyx Intro Call" → Slack Alert + Salesforce Update
"""

import requests
import json
import os
import subprocess
from datetime import datetime

# Load environment
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

def test_fellow_api():
    """Test Fellow API authentication"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return False, "FELLOW_API_KEY not found in environment"
    
    try:
        headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            json={"page": 1, "limit": 1},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, f"✅ Fellow API working (got {response.status_code})"
        else:
            return False, f"❌ Fellow API failed: {response.status_code} - {response.text[:200]}"
            
    except Exception as e:
        return False, f"❌ Fellow API error: {str(e)}"

def get_fellow_intro_calls(limit=5):
    """Get recent Fellow 'Telnyx Intro Call' recordings"""
    api_key = os.getenv('FELLOW_API_KEY')
    headers = {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            json={"page": 1, "limit": 20},
            headers=headers,
            timeout=30
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
        
        return intro_calls[:limit], f"Found {len(intro_calls)} intro calls"
        
    except Exception as e:
        return [], f"Error: {str(e)}"

def format_v1_alert(call_data):
    """Format simple V1 Slack alert"""
    title = call_data.get('title', 'Unknown Call')
    call_id = call_data.get('id', 'unknown')
    created_at = call_data.get('created_at', '')
    
    # Extract prospect name from title
    prospect_name = title.replace('Telnyx Intro Call (', '').replace(')', '') if '(' in title else 'Unknown'
    
    alert = f"""🔔 **New Telnyx Intro Call**

**Prospect**: {prospect_name}
**Call Date**: {created_at[:10] if created_at else 'Unknown'}
**Fellow ID**: {call_id}
**Status**: Ready for review

📞 **Fellow Link**: https://telnyx.fellow.app/recordings/{call_id}

_V1 Call Intelligence System_"""
    
    return alert

def post_to_slack_via_clawdbot(message):
    """Post to Slack via Clawdbot CLI"""
    try:
        # Write message to temp file
        temp_file = '/tmp/slack_message.txt'
        with open(temp_file, 'w') as f:
            f.write(message)
        
        # Use Clawdbot CLI to send message
        cmd = ['clawdbot', 'message', 'send', '--target', 'C38URQASH', '--message', message]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return True, "✅ Message sent via Clawdbot CLI"
        else:
            return False, f"❌ Clawdbot CLI failed: {result.stderr}"
            
    except Exception as e:
        return False, f"❌ Clawdbot error: {str(e)}"

def test_salesforce():
    """Test Salesforce OAuth2 integration"""
    try:
        client_id = os.getenv('SF_CLIENT_ID')
        client_secret = os.getenv('SF_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            return False, "Salesforce credentials missing"
            
        # Get access token
        auth_url = f"https://telnyx.my.salesforce.com/services/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        auth_response = requests.post(auth_url, data=auth_data, timeout=10)
        
        if auth_response.status_code == 200:
            return True, "✅ Salesforce OAuth2 working"
        else:
            return False, f"❌ Salesforce auth failed: {auth_response.status_code}"
            
    except Exception as e:
        return False, f"❌ Salesforce error: {str(e)}"

def run_v1_demo():
    """Run V1 demo with real call"""
    print("🚀 V1 Call Intelligence - Demo Run")
    print("=" * 50)
    
    # Get a real Fellow call
    print("📞 Getting real Fellow intro calls...")
    calls, msg = get_fellow_intro_calls(3)
    print(f"   {msg}")
    
    if not calls:
        print("   ❌ No calls found - cannot demo")
        return False
    
    # Pick the most recent call
    demo_call = calls[0]
    print(f"   📋 Demo call: {demo_call.get('title', 'Unknown')}")
    
    # Format alert
    print("\n📝 Formatting Slack alert...")
    alert = format_v1_alert(demo_call)
    print("   ✅ Alert formatted")
    
    # Test Slack posting
    print(f"\n📱 Posting to Slack (#bot-testing)...")
    slack_ok, slack_msg = post_to_slack_via_clawdbot(alert)
    print(f"   {slack_msg}")
    
    # Test Salesforce
    print(f"\n🏢 Testing Salesforce integration...")
    sf_ok, sf_msg = test_salesforce()
    print(f"   {sf_msg}")
    
    # Show the alert
    print("\n" + "=" * 50)
    print("📱 SLACK ALERT PREVIEW:")
    print("=" * 50)
    print(alert)
    print("=" * 50)
    
    # Summary
    print("\n🎯 V1 Demo Results:")
    print(f"   Fellow Data: ✅ Retrieved {len(calls)} calls")
    print(f"   Slack Alert: {'✅' if slack_ok else '❌'}")
    print(f"   Salesforce: {'✅' if sf_ok else '❌'}")
    
    success = slack_ok and sf_ok and len(calls) > 0
    print(f"\n🚀 V1 Demo: {'✅ SUCCESS' if success else '❌ PARTIAL'}")
    
    return success

def run_v1_test():
    """Test V1 components"""
    print("🧪 V1 Component Test")
    print("=" * 30)
    
    # Test 1: Fellow API
    print("1. Fellow API...")
    fellow_ok, fellow_msg = test_fellow_api()
    print(f"   {fellow_msg}")
    
    # Test 2: Salesforce API
    print("2. Salesforce API...")
    sf_ok, sf_msg = test_salesforce()
    print(f"   {sf_msg}")
    
    # Test 3: Simple Slack test
    print("3. Slack posting...")
    test_message = f"🧪 V1 Test - {datetime.now().strftime('%H:%M:%S')}"
    slack_ok, slack_msg = post_to_slack_via_clawdbot(test_message)
    print(f"   {slack_msg}")
    
    all_working = fellow_ok and sf_ok and slack_ok
    print(f"\n✅ All Systems: {'WORKING' if all_working else 'ISSUES'}")
    
    return all_working

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        run_v1_demo()
    else:
        if run_v1_test():
            print("\n🚀 Ready for demo! Run: python3 v1_fixed.py demo")
        else:
            print("\n❌ Fix issues before running demo")