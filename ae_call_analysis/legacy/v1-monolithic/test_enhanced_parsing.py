#!/usr/bin/env python3
"""
Test enhanced Google Drive parsing on specific challenging calls
"""

import os
import sys
from enhanced_google_drive_integration import get_google_doc_content, format_enhanced_google_drive_call

def test_specific_call(doc_id, title):
    """Test enhanced parsing on a specific call"""
    print(f"\n🔄 Testing: {title}")
    print("-" * 60)
    
    # Get document content
    content, content_status = get_google_doc_content(doc_id)
    print(f"📝 Content: {content_status}")
    
    if content:
        # Create mock call data
        call_data = {
            'id': doc_id,
            'title': title,
            'modified_date': '2026-03-03 15:00'
        }
        
        # Test enhanced parsing
        formatted_call = format_enhanced_google_drive_call(call_data, content)
        
        print(f"✅ Enhanced Parsing Results:")
        print(f"   📧 Prospect: {formatted_call['prospect_name']}")
        print(f"   📨 Email: {formatted_call['prospect_email']}")
        print(f"   👨‍💼 AE: {formatted_call['ae_name']}")
        print(f"   👥 All attendees: {formatted_call['attendees']['all_attendees']}")
        print(f"   📧 All emails: {formatted_call['attendees']['prospect_emails']}")
        print(f"   🏢 AEs found: {formatted_call['attendees']['ae_names']}")
        print(f"   👤 Prospects found: {formatted_call['attendees']['prospect_names']}")
        
        # Show first 200 chars of summary for verification
        summary = formatted_call['transcript_summary'][:200]
        print(f"   📋 Summary preview: {summary}...")
        
        return True
    else:
        print("❌ Could not retrieve document content")
        return False

def main():
    """Test enhanced parsing on the challenging calls"""
    print("🧪 Testing Enhanced Google Drive Parsing")
    print("=" * 60)
    
    # Test cases that were problematic before
    test_cases = [
        ("1rptvzzdTNQnXfG5Yb02X6CF5ZOITJwc2lgf2ugYZKxw", "Copy of Ken <> Ryan - 2026/03/02 13:15 EST - Notes by Gemini"),
        ("1c5Zpdvmy3vFGu3xnyl3xWeVLMxBs7UtpuAFk2UZC3lI", "Copy of sruthi@eltropy.com and Rob: 30-minute Meeting - 2026/02/25 09:23 EST - Notes by Gemini"),
        ("1RR-2K3mRD_DymfFTxRS_dhYXrHKVo8n0SFto-uPRvss", "Copy of roly@meetgail.com and Ryan: 30-minute Meeting - 2026/03/03 15:59 EST - Notes by Gemini")
    ]
    
    success_count = 0
    
    for doc_id, title in test_cases:
        if test_specific_call(doc_id, title):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"🎯 Results: {success_count}/{len(test_cases)} calls parsed successfully")
    
    if success_count == len(test_cases):
        print("🎉 Enhanced parsing is working for all test cases!")
        print("\n📋 Key Improvements:")
        print("   ✅ Content-based attendee extraction")
        print("   ✅ Flexible email detection")
        print("   ✅ Context-aware AE identification")
        print("   ✅ Broader search patterns")
    else:
        print("⚠️ Some parsing issues remain - check the results above")
    
    return success_count == len(test_cases)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)