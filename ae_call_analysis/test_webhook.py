#!/usr/bin/env python3
"""
Test the webhook receiver with sample Zapier payload
"""

import requests
import json
from datetime import datetime

# Simple Zapier webhook payload (just Fellow call ID)
test_payload = {
    'fellow_call_id': 'QdZdMHWoec'
}

# Alternative formats supported:
# test_payload = {'call_id': 'QdZdMHWoec'}
# test_payload = {'id': 'QdZdMHWoec'}

def test_webhook():
    """Test the webhook endpoint"""
    
    webhook_url = 'http://localhost:5000/webhook/fellow-call'
    
    try:
        print("🧪 Testing webhook endpoint...")
        print(f"📡 URL: {webhook_url}")
        print(f"📦 Payload: {json.dumps(test_payload, indent=2)}")
        
        response = requests.post(
            webhook_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Webhook test successful!")
            print("🎯 Check console for processing logs...")
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
            
    except requests.ConnectionError:
        print("❌ Connection failed - is the webhook server running?")
        print("💡 Start it with: ./ae_call_analysis/start_webhook_server.sh")
    except Exception as e:
        print(f"❌ Test error: {str(e)}")

def test_health():
    """Test health check endpoint"""
    
    try:
        response = requests.get('http://localhost:5000/health')
        print(f"💊 Health Check: {response.status_code}")
        print(f"📋 Status: {response.json()}")
        
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")

if __name__ == '__main__':
    print("🔬 WEBHOOK RECEIVER TEST")
    print("=" * 30)
    
    # Test health first
    test_health()
    print()
    
    # Test webhook
    test_webhook()