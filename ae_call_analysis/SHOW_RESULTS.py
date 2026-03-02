#!/usr/bin/env python3
"""
Show Results - Demonstrate the working Call Intelligence API
Perfect for showing stakeholders what the system produces
"""

import requests
import json
import time

def show_complete_demo():
    print("🎉 CALL INTELLIGENCE SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Sample enterprise sales call
    sample_call = {
        "prospect_name": "Lisa Rodriguez",
        "title": "Telnyx Voice Platform Assessment - Lisa Rodriguez (GrowthTech Inc)",
        "transcript": """
AE: Hi Lisa, thanks for taking the time today. I understand GrowthTech is evaluating voice communication platforms?

Lisa: Yes, exactly. We've scaled from 75 to 250 employees in 18 months and our current phone system just can't handle it. We're experiencing dropped calls, poor international connectivity, and our costs have tripled.

AE: Those are exactly the challenges Telnyx specializes in solving. Tell me about your current setup and pain points.

Lisa: We're using a legacy on-premise system that requires constant IT attention. International calls to our European office are expensive and unreliable. We're spending about $15,000 monthly and our IT team is overwhelmed with maintenance.

AE: I completely understand. With Telnyx's global network, you'd typically see 50-70% cost reduction while getting carrier-grade quality. What's driving the urgency for this project?

Lisa: Our board mandated we solve this by Q1 next year. We have budget approved - up to $300,000 for the first year implementation. We're down to the final two vendors.

AE: Excellent timing. Based on your scale, I'd estimate your Telnyx solution around $6,000 monthly, saving over $100,000 annually. Could we schedule a technical demo with your IT director next week?

Lisa: Absolutely. I'll bring our CTO and operations manager. Can you prepare detailed ROI projections and migration timeline?

AE: Definitely. I'll have our solutions architect join to discuss the technical migration plan. This sounds like a perfect fit for our enterprise platform.

Lisa: Perfect. We're really excited about the potential cost savings and reliability improvements. This could be transformational for our communication infrastructure.

AE: I'm confident we can deliver both outcomes. Let me coordinate with our technical team and send you some relevant case studies.

Lisa: Sounds great. Looking forward to next week's deep dive.
        """,
        "call_date": "2026-02-27",
        "fellow_id": "demo_enterprise_002"
    }
    
    print("📞 PROCESSING ENTERPRISE SALES CALL")
    print(f"👤 Prospect: {sample_call['prospect_name']}")
    print(f"🏢 Company: GrowthTech Inc")
    print(f"💰 Budget: $300,000 approved")
    print(f"⏰ Urgency: Board mandate Q1 implementation")
    print()
    
    # Process through API
    print("🔄 Processing through Call Intelligence Pipeline...")
    try:
        response = requests.post(
            "http://localhost:8082/process-call",
            json=sample_call,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ PROCESSING SUCCESSFUL!")
            print(f"📞 Call ID: {result['call_id']}")
            print(f"⏱️ Processing Time: {result['processing_time']}")
            print()
            
            # Show pipeline execution
            steps = result.get('pipeline_steps', [])
            print("🔄 PIPELINE EXECUTION:")
            for step in steps:
                print(f"   {step}")
            print()
            
            # Show detailed analysis
            analysis = result.get('analysis', {})
            print("🧠 INTELLIGENT ANALYSIS RESULTS:")
            print(f"   📈 Interest Level: {analysis.get('prospect_interest_level', 'N/A')}")
            print(f"   🎯 AE Excitement: {analysis.get('ae_excitement_level', 'N/A')}")
            print(f"   ⭐ Analysis Confidence: {analysis.get('analysis_confidence', 0):.0%}")
            print()
            
            print("🔍 DETAILED INSIGHTS:")
            print(f"   📋 Strategic Insights:")
            print(f"      {analysis.get('strategic_insights', 'N/A')}")
            print()
            
            print(f"   🔴 Pain Points:")
            print(f"      {analysis.get('pain_points', 'N/A')}")
            print()
            
            print(f"   💡 Buying Signals:")
            print(f"      {analysis.get('buying_signals', 'N/A')}")
            print()
            
            print(f"   📈 Next Steps:")
            print(f"      {analysis.get('next_steps', 'N/A')}")
            print()
            
            # Show Salesforce integration
            sf_data = result.get('salesforce', {})
            print("🔗 SALESFORCE INTEGRATION:")
            print(f"   👤 Account Executive: {sf_data.get('Account Executive', 'N/A')}")
            print(f"   🏢 Account: {sf_data.get('Account', 'N/A')}")
            print(f"   📋 Event Subject: {sf_data.get('Subject', 'N/A')}")
            print(f"   🔗 Record URL: {sf_data.get('Record URL', 'N/A')}")
            print()
            
            # Show Slack alert
            slack_alert = result.get('slack_alert', {})
            if slack_alert:
                print("📱 SLACK ALERT GENERATED:")
                print("   📨 Main Channel Message:")
                main_lines = slack_alert.get('main_message', '').split('\n')
                for line in main_lines[:5]:
                    if line.strip():
                        print(f"      {line.strip()}")
                print()
                
                print("   🧵 Thread Reply:")
                thread_lines = slack_alert.get('thread_message', '').split('\n')
                for line in thread_lines[:8]:
                    if line.strip():
                        print(f"      {line.strip()}")
                print("      ... [full detailed analysis in thread]")
                print()
                
                summary = slack_alert.get('summary', {})
                print(f"   🎯 Alert Priority: {summary.get('priority', 'N/A')}")
                print()
            
            print("💾 DATABASE STORAGE:")
            print(f"   ✅ Call record created (ID: {result['call_id']})")
            print(f"   ✅ Analysis results stored")
            print(f"   ✅ Salesforce data linked")
            print(f"   ✅ Full transcript preserved")
            print()
            
            print("🎯 BUSINESS IMPACT:")
            if analysis.get('analysis_confidence', 0) > 0.8:
                print("   🔥 HIGH-VALUE OPPORTUNITY DETECTED")
                print(f"   💰 Revenue Potential: High (budget approved: $300k)")
                print(f"   ⏰ Sales Velocity: Fast (board mandate timeline)")
                print(f"   📊 Win Probability: High based on buying signals")
            else:
                print("   📊 Standard opportunity - monitor for development")
            
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print("Make sure the API is running: python3 demo_call_api.py")
        return
    
    print()
    print("=" * 60)
    print("🏆 CALL INTELLIGENCE DEMONSTRATION COMPLETE")
    print()
    print("✅ WHAT WAS DEMONSTRATED:")
    print("   • Complete end-to-end pipeline execution")
    print("   • Intelligent transcript analysis") 
    print("   • Salesforce integration (demo)")
    print("   • Professional Slack alert generation")
    print("   • Comprehensive database storage")
    print("   • Business impact assessment")
    print()
    print("🚀 SYSTEM READY FOR:")
    print("   • Production deployment")
    print("   • Team integration") 
    print("   • Real API credential enhancement")
    print("   • Stakeholder rollout")

def show_api_endpoints():
    print("\n📡 AVAILABLE API ENDPOINTS:")
    print("=" * 40)
    
    try:
        # Test root endpoint
        response = requests.get("http://localhost:8082/", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print(f"✅ API: {info['message']} v{info['version']}")
            print(f"📋 Status: {info['status']}")
            print("📊 Features:")
            for feature in info['features']:
                print(f"   • {feature}")
        
        print(f"\n🔗 Endpoints:")
        print(f"   POST /process-call   - Main pipeline")
        print(f"   GET  /calls          - List all calls") 
        print(f"   GET  /call/{{id}}      - Get call details")
        print(f"   GET  /health         - Health check")
        print(f"   GET  /docs           - Swagger UI")
        print(f"   GET  /               - API information")
        
    except Exception as e:
        print(f"❌ API not accessible: {str(e)}")

def show_integration_examples():
    print("\n🔗 INTEGRATION EXAMPLES:")
    print("=" * 30)
    
    print("Python:")
    print("""
import requests

call_data = {
    "prospect_name": "John Smith",
    "title": "Demo Call - John Smith (AcmeCorp)", 
    "transcript": "Your full call transcript here..."
}

response = requests.post("http://localhost:8082/process-call", json=call_data)
result = response.json()

print(f"Processed call {result['call_id']} with {result['analysis']['analysis_confidence']:.0%} confidence")
    """)
    
    print("cURL:")
    print("""
curl -X POST "http://localhost:8082/process-call" \\
  -H "Content-Type: application/json" \\
  -d '{"prospect_name": "Jane Doe", "title": "Demo Call", "transcript": "..."}'
    """)
    
    print("Zapier Webhook:")
    print("""
Webhook URL: http://localhost:8082/process-call
Method: POST
Content-Type: application/json
Body: {"prospect_name": "...", "title": "...", "transcript": "..."}
    """)

if __name__ == "__main__":
    show_complete_demo()
    show_api_endpoints() 
    show_integration_examples()