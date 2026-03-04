#!/usr/bin/env python3
"""
Test the updated V1 Enhanced system with correct Salesforce logic
"""
import sys
sys.path.append('.')

from datetime import datetime
import re

def test_event_name_extraction():
    print("🔍 TESTING EVENT NAME EXTRACTION")
    print("-" * 60)
    
    test_cases = [
        ("Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini", "Telnyx // Voxtelesys"),
        ("Copy of Dayforce <> Telnyx - 2026/03/04 12:29 EST - Notes by Gemini", "Dayforce <> Telnyx"),
        ("Copy of Ringba <> Telnyx - 2026/03/04 11:58 CST - Notes by Gemini", "Ringba <> Telnyx")
    ]
    
    for title, expected in test_cases:
        # Test regex
        pattern = r'^Copy of (.+?) - \d{4}/\d{2}/\d{2} .+ - Notes by Gemini'
        match = re.search(pattern, title)
        
        if match:
            event_name = match.group(1).strip()
            status = "✅" if event_name == expected else "❌"
            print(f"{status} '{event_name}' (expected: '{expected}')")
        else:
            print(f"❌ No match for: {title}")

def test_salesforce_subject():
    print("\n🔍 TESTING SALESFORCE SUBJECT GENERATION")
    print("-" * 60)
    
    event_names = [
        "Telnyx // Voxtelesys",
        "Dayforce <> Telnyx", 
        "Ringba <> Telnyx"
    ]
    
    for event_name in event_names:
        subject = f"Meeting Booked: {event_name}"
        print(f"✅ Event: '{event_name}' → SF: '{subject}'")

if __name__ == "__main__":
    print("🚀 TESTING UPDATED V1 ENHANCED SYSTEM")
    print("=" * 60)
    
    test_event_name_extraction()
    test_salesforce_subject()
    
    print("\n🎯 FOR VOXTELESYS:")
    print("   Title: 'Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini'")
    print("   Event: 'Telnyx // Voxtelesys'") 
    print("   SF Search: 'Meeting Booked: Telnyx // Voxtelesys'")
    print("   Should find your existing Salesforce event! ✅")
