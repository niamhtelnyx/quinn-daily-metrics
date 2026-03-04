#!/usr/bin/env python3
"""
Test Slack posting functionality for V2 FINAL Call Intelligence
Forces processing of a recent call to verify end-to-end functionality
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

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

def test_slack_posting():
    """Test Slack posting with a sample call"""
    print("🧪 Testing V2 FINAL Live Slack Posting")
    print("=" * 50)
    
    # Import functions from live version
    from V2_FINAL_PRODUCTION_LIVE import (
        get_enhanced_google_drive_calls,
        get_google_doc_content, 
        format_enhanced_google_drive_call,
        analyze_call_with_ai,
        post_to_slack,
        init_database,
        save_processed_call,
        generate_dedup_key
    )
    
    # Initialize database
    init_database()
    
    # Get a recent call for testing
    print("📁 Finding recent Google Drive calls...")
    calls, status = get_enhanced_google_drive_calls()
    print(f"📁 {status}")
    
    if not calls:
        print("❌ No calls found for testing")
        return False
    
    # Use the first call for testing
    test_call = calls[0]
    print(f"🎯 Testing with call: {test_call['title']}")
    
    # Get content
    print("📝 Fetching call content...")
    content, content_msg = get_google_doc_content(test_call['id'])
    if not content:
        print(f"❌ Failed to get content: {content_msg}")
        return False
    
    print(f"✅ Got content: {len(content)} characters")
    
    # Parse call data
    print("👤 Parsing attendee information...")
    formatted_call = format_enhanced_google_drive_call(test_call, content)
    print(f"✅ Parsed: {formatted_call['prospect_name']} | {formatted_call['ae_name']}")
    
    # AI Analysis
    print("🤖 Running AI analysis...")
    analysis = analyze_call_with_ai(content, formatted_call)
    
    if 'error' in analysis:
        print(f"⚠️ AI analysis error: {analysis['error']}")
    else:
        print(f"✅ AI analysis: {analysis.get('summary', 'No summary')[:50]}...")
    
    # Test Slack posting
    print("💬 Testing Slack posting...")
    
    # Add test indicator to call data
    formatted_call['prospect_name'] = f"[TEST] {formatted_call['prospect_name']}"
    
    slack_ts = post_to_slack(formatted_call, analysis)
    
    if slack_ts:
        print("✅ SUCCESS: Slack posting working!")
        print(f"📅 Slack message timestamp: {slack_ts}")
        
        # Save test result to database
        dedup_key = generate_dedup_key(
            formatted_call['prospect_email'] or formatted_call['prospect_name'], 
            test_call.get('modified_date', '')
        )
        save_processed_call(formatted_call, analysis, dedup_key, slack_ts)
        print("💾 Test saved to database")
        
        return True
    else:
        print("❌ FAILED: Slack posting not working")
        return False

def check_requirements():
    """Check if all required environment variables are set"""
    print("🔍 Checking requirements...")
    
    required_vars = ['SLACK_BOT_TOKEN', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}...")
        else:
            print(f"❌ {var}: Missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Check your .env file")
        return False
    
    return True

if __name__ == "__main__":
    print(f"🚀 V2 FINAL Live Slack Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not check_requirements():
        sys.exit(1)
    
    if test_slack_posting():
        print("\n🎉 TEST PASSED: V2 FINAL Live processing works end-to-end!")
        print("💬 Check #ae-call-intelligence Slack channel for test message")
        print("🚀 Ready to deploy live processing")
    else:
        print("\n❌ TEST FAILED: Issues found with live processing")
        print("🔧 Check logs and fix issues before deploying")
        sys.exit(1)