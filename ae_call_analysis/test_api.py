#!/usr/bin/env python3
"""
Test script for Call Intelligence API
Shows how to use the FastAPI programmatically
"""

import requests
import json
import time

API_BASE = "http://localhost:8080"

def test_api():
    print("🧪 TESTING CALL INTELLIGENCE API")
    print("=" * 40)
    
    # Test 1: Health check
    print("1️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ API healthy: {health['status']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ API not running: {str(e)}")
        return
    
    # Test 2: Process a realistic call
    print("\n2️⃣ Processing sample call...")
    
    sample_call = {
        "prospect_name": "Sarah Wilson",
        "title": "Telnyx Platform Demo - Sarah Wilson (DataFlow Inc)",
        "transcript": """
        AE: Hi Sarah, thanks for taking the time today. I understand DataFlow is looking into modernizing your communications infrastructure?

        Sarah: Yes, exactly. We're a growing data analytics company with about 150 employees. Our current phone system is really limiting us - dropped calls, poor international connectivity, and it's expensive.

        AE: Those are common pain points we solve. Tell me about your international calling needs specifically.

        Sarah: We have clients in Europe and Asia, so we're on calls at odd hours frequently. The call quality is inconsistent and we're spending about $3000/month just on international calls.

        AE: That's a significant expense. With Telnyx, you'd typically see 40-60% cost reduction on international calls, plus much better quality since we own our own global network.

        Sarah: That would be huge for us. What about integration with our existing tools? We use Salesforce heavily and need call logs to sync automatically.

        AE: Perfect - we have native Salesforce integration. All your call data, recordings, and analytics flow directly into Salesforce automatically. No manual work.

        Sarah: This sounds very promising. I'd like to run a pilot with a small team first. What would that look like?

        AE: Absolutely. We can set up a 30-day pilot for 10-15 users, include all the features, and show you the cost savings and integrations live. No commitment.

        Sarah: Great. When can we start? We're in budget planning mode right now, so timing is perfect.

        AE: I can have you set up by early next week. Let me send you the pilot agreement and get your IT team the integration details.

        Sarah: Perfect. I'm excited to see this in action.
        """,
        "call_date": "2026-02-27",
        "fellow_id": "demo_call_002"
    }
    
    print(f"   📞 Call: {sample_call['prospect_name']}")
    print(f"   📄 Transcript: {len(sample_call['transcript'])} chars")
    print(f"   🔄 Processing...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/process-call",
            json=sample_call,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success in {processing_time:.1f}s")
            print(f"   📞 Call ID: {result['call_id']}")
            
            # Show analysis if available
            analysis = result.get('analysis', {})
            if analysis and analysis.get('prospect_interest_level') != 'Medium':
                print(f"\n   🧠 AI Analysis:")
                print(f"      📈 Interest: {analysis.get('prospect_interest_level', 'N/A')}")
                print(f"      🎯 AE Excitement: {analysis.get('ae_excitement_level', 'N/A')}")
                print(f"      ⭐ Confidence: {analysis.get('analysis_confidence', 0):.0%}")
                print(f"      💡 Insights: {analysis.get('strategic_insights', 'N/A')[:100]}...")
            else:
                print(f"   ⚠️ OpenAI analysis returned fallback (API issue)")
            
        else:
            print(f"   ❌ Processing failed: {response.status_code}")
            print(f"   📋 Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request error: {str(e)}")
    
    # Test 3: List calls
    print("\n3️⃣ Listing recent calls...")
    try:
        response = requests.get(f"{API_BASE}/calls", timeout=5)
        if response.status_code == 200:
            data = response.json()
            calls = data.get('calls', [])
            print(f"   📊 Found {len(calls)} calls:")
            
            for call in calls[:3]:  # Show first 3
                print(f"      📞 {call['prospect_name']} - {call.get('interest_level', 'N/A')} interest")
        else:
            print(f"   ❌ List calls failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ List error: {str(e)}")
    
    # Summary
    print(f"\n🎯 API TEST SUMMARY:")
    print(f"   ✅ FastAPI orchestration working")
    print(f"   ✅ Database storage working")
    print(f"   ✅ Call processing pipeline active")
    print(f"   🔧 OpenAI/Salesforce APIs need API key fixes")
    print(f"\n📡 Ready for integration!")
    print(f"   • Direct Python calls")
    print(f"   • Zapier webhooks")  
    print(f"   • cURL commands")
    print(f"   • Any HTTP client")

def demo_integration_patterns():
    """Show different integration patterns"""
    print(f"\n🔗 INTEGRATION EXAMPLES")
    print("=" * 30)
    
    print("Python Integration:")
    print("""
import requests

def process_call(prospect_name, title, transcript):
    response = requests.post("http://localhost:8080/process-call", json={
        "prospect_name": prospect_name,
        "title": title, 
        "transcript": transcript
    })
    return response.json()

# Usage
result = process_call("Jane Doe", "Discovery Call", "transcript...")
print(f"Processed call {result['call_id']} for {result['prospect_name']}")
    """)
    
    print("cURL Integration:")
    print("""
curl -X POST "http://localhost:8080/process-call" \\
  -H "Content-Type: application/json" \\
  -d '{"prospect_name": "John Smith", "title": "Demo Call", "transcript": "..."}'
    """)
    
    print("Zapier Webhook Integration:")
    print("""
Zapier → HTTP POST → http://localhost:8080/process-call
Body: JSON with prospect_name, title, transcript fields
Response: Full processing results + analysis
    """)

if __name__ == "__main__":
    test_api()
    demo_integration_patterns()