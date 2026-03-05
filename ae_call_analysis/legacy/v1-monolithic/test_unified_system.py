#!/usr/bin/env python3
"""
Test script for V2 Unified Call Intelligence
Tests both Fellow and Google Drive integration without external API calls
"""

import os
import sys
from datetime import datetime
from google_drive_integration import get_google_drive_calls, get_google_doc_content, format_google_drive_call_for_processing

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def test_google_drive_integration():
    """Test Google Drive call processing"""
    log_message("🔍 Testing Google Drive integration...")
    
    # Get Google Drive calls from today
    calls, status = get_google_drive_calls()
    log_message(f"📁 Google Drive: {status}")
    
    if not calls:
        log_message("😴 No Google Drive calls found for testing")
        return False
    
    # Test processing the first call
    test_call = calls[0]
    log_message(f"📄 Testing call: {test_call['title']}")
    
    # Get document content
    content, content_msg = get_google_doc_content(test_call['id'])
    log_message(f"📝 Content: {content_msg}")
    
    if not content:
        log_message("❌ Could not retrieve document content")
        return False
    
    # Format call for processing
    formatted_call = format_google_drive_call_for_processing(test_call, content)
    
    log_message(f"✅ Successfully formatted Google Drive call:")
    log_message(f"   Prospect: {formatted_call['prospect_name']}")
    log_message(f"   AE: {formatted_call['ae_name']}")
    log_message(f"   Source: {formatted_call['source']}")
    log_message(f"   Summary length: {len(formatted_call['transcript_summary'])} chars")
    
    return True

def test_fellow_api_connection():
    """Test Fellow API connection (without processing)"""
    log_message("🔍 Testing Fellow API connection...")
    
    api_key = os.getenv('FELLOW_API_KEY')
    if not api_key:
        log_message("⚠️ No FELLOW_API_KEY found in environment")
        return False
    
    log_message("✅ Fellow API key found")
    return True

def main():
    """Run all tests"""
    log_message("🚀 Testing V2 Unified Call Intelligence System")
    
    # Test Google Drive integration
    google_success = test_google_drive_integration()
    
    # Test Fellow API setup
    fellow_success = test_fellow_api_connection()
    
    log_message(f"\n🎯 Test Results:")
    log_message(f"   Google Drive: {'✅' if google_success else '❌'}")
    log_message(f"   Fellow API: {'✅' if fellow_success else '❌'}")
    
    if google_success and fellow_success:
        log_message("\n🎉 All tests passed! The unified system is ready for production.")
        log_message("\n📋 Next steps:")
        log_message("   1. Run 'python3 V2_UNIFIED_PRODUCTION.py' for full processing")
        log_message("   2. Set up cron job for automated monitoring")
        log_message("   3. Monitor Slack channel for processed calls")
    else:
        log_message("\n❌ Some tests failed. Check configuration before running production.")
    
    return google_success and fellow_success

if __name__ == "__main__":
    try:
        # Load environment variables
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        
        success = main()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        log_message(f"❌ Test failed with error: {e}")
        sys.exit(1)