#!/usr/bin/env python3
"""
Test fuzzy matching for specific problematic event names
"""

from V1_DATE_FULL_FUZZY import get_salesforce_token, find_salesforce_event_fuzzy_match

def test_fuzzy_matching():
    token = get_salesforce_token()
    if not token:
        print("❌ No Salesforce token")
        return
    
    print("✅ Testing fuzzy matching...")
    
    test_names = [
        "Telnyx -- Collie",
        "Morgan & Aliyana -- Telnyx", 
        "Adrian - Mike",
        "Lightspeed -- Telnyx",
        "Allo-Telnyx - Spam"
    ]
    
    successful_matches = 0
    
    for name in test_names:
        print(f"\n🔍 Testing: '{name}'")
        event = find_salesforce_event_fuzzy_match(token, name)
        if event:
            print(f"  ✅ Found: {event['Subject']}")
            print(f"      ID: {event['Id']}")
            successful_matches += 1
        else:
            print(f"  ❌ No match found")
    
    print(f"\n📊 FUZZY MATCHING RESULTS:")
    print(f"   🎯 Successful matches: {successful_matches}/{len(test_names)}")
    print(f"   📈 Success rate: {successful_matches/len(test_names)*100:.1f}%")
    
    if successful_matches > 0:
        print(f"   ✅ Fuzzy matching is working!")
    else:
        print(f"   ❌ Fuzzy matching needs improvement")

if __name__ == "__main__":
    test_fuzzy_matching()