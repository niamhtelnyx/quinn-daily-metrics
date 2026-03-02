#!/usr/bin/env python3
"""
Quick test of Fellow call ID webhook approach
"""

import requests
import json

def test_call_id_webhook(call_id):
    """Test webhook with just a Fellow call ID"""
    
    # Simple payload - just the call ID
    payload = {'fellow_call_id': call_id}
    
    webhook_url = 'http://localhost:5001/webhook/fellow-call'
    
    try:
        print(f"🧪 Testing webhook with Fellow call ID: {call_id}")
        print(f"📡 URL: {webhook_url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        print("")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"📋 Response: {json.dumps(response.json(), indent=2)}")
            print("")
            print("✅ Call ID webhook test successful!")
            print("🎯 Check webhook server console for Fellow API fetch and processing logs...")
        else:
            print(f"📋 Error Response: {response.text}")
            print(f"❌ Webhook test failed: {response.status_code}")
            
    except requests.ConnectionError:
        print("❌ Connection failed - is the webhook server running?")
        print("💡 Start it with: ./ae_call_analysis/start_webhook_server.sh")
    except Exception as e:
        print(f"❌ Test error: {str(e)}")

if __name__ == '__main__':
    print("🔬 FELLOW CALL ID WEBHOOK TEST")
    print("=" * 35)
    
    # Use a real Fellow call ID for testing
    test_call_id = input("Enter Fellow call ID to test (or press Enter for 'QdZdMHWoec'): ").strip()
    
    if not test_call_id:
        test_call_id = 'QdZdMHWoec'  # Default test ID
    
    print("")
    test_call_id_webhook(test_call_id)