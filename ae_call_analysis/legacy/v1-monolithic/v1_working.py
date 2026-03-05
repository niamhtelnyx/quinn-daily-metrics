#!/usr/bin/env python3
"""
V1 Working - Simple Call Intelligence
Fellow "Telnyx Intro Call" → Basic Alert + Salesforce Check
"""

import requests
import json
import os
from datetime import datetime

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

def get_recent_fellow_calls():
    """Get recent Fellow intro calls"""
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        return [], "No Fellow API key"
    
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

def test_salesforce_oauth():
    """Test Salesforce OAuth2"""
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return False, "Missing Salesforce credentials"
    
    try:
        auth_url = "https://telnyx.my.salesforce.com/services/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=auth_data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            return True, f"✅ Salesforce OK (token: {token_data.get('access_token', '')[:20]}...)"
        else:
            return False, f"❌ Salesforce auth failed: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Salesforce error: {str(e)}"

def format_simple_alert(call):
    """Format simple alert for call"""
    title = call.get('title', 'Unknown Call')
    call_id = call.get('id', 'unknown')
    created_at = call.get('created_at', '')
    
    # Extract prospect name
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    alert = f"""🔔 **V1 Call Alert**

**Prospect**: {prospect_name}
**Date**: {created_at[:10] if created_at else 'Unknown'}
**Fellow ID**: {call_id}

📞 Link: https://telnyx.fellow.app/recordings/{call_id}

_V1 System Test - {datetime.now().strftime('%H:%M:%S')}_"""
    
    return alert

def main():
    """Run V1 test"""
    print("🚀 V1 Call Intelligence Test")
    print("=" * 40)
    
    # Test 1: Fellow API
    print("\n📞 Testing Fellow API...")
    calls, fellow_status = get_recent_fellow_calls()
    print(f"   Result: {fellow_status}")
    
    if calls:
        print(f"   Latest: {calls[0].get('title', 'Unknown')}")
        demo_call = calls[0]
    else:
        print("   ❌ No calls found")
        demo_call = None
    
    # Test 2: Salesforce
    print("\n🏢 Testing Salesforce...")
    sf_ok, sf_status = test_salesforce_oauth()
    print(f"   Result: {sf_status}")
    
    # Test 3: Alert Generation
    if demo_call:
        print("\n📝 Generating alert...")
        alert = format_simple_alert(demo_call)
        print("   ✅ Alert formatted")
        
        # Save alert to file for manual Slack posting
        alert_file = 'v1_alert_output.txt'
        with open(alert_file, 'w') as f:
            f.write(alert)
        print(f"   💾 Alert saved to: {alert_file}")
        
        print("\n" + "=" * 40)
        print("📱 ALERT PREVIEW:")
        print("=" * 40)
        print(alert)
        print("=" * 40)
    else:
        print("\n⏭️  Skipping alert generation (no calls)")
    
    # Summary
    print("\n🎯 V1 Status:")
    print(f"   Fellow API: {'✅' if calls else '❌'}")
    print(f"   Salesforce: {'✅' if sf_ok else '❌'}")
    print(f"   Alert Gen: {'✅' if demo_call else '❌'}")
    
    all_ok = bool(calls) and sf_ok and demo_call
    print(f"\n🚀 V1 Ready: {'✅ YES' if all_ok else '❌ NO'}")
    
    if all_ok:
        print(f"\n📋 Next: Copy alert from {alert_file} and post to Slack manually")
    
    return all_ok

if __name__ == "__main__":
    main()