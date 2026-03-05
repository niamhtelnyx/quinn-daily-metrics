#!/usr/bin/env python3
"""
Test the normalized field matching
"""

from V1_DATE_FULL import normalize_event_name, get_salesforce_token, find_salesforce_event_by_exact_subject

def test_normalized_matching():
    # Test normalization
    test_names = [
        "Telnyx -- Collie",
        "Allo-Telnyx - Spam", 
        "Morgan & Aliyana -- Telnyx"
    ]

    print("🧪 Testing normalization:")
    for name in test_names:
        normalized = normalize_event_name(name)
        print(f"  {name} → {normalized}")

    print("\n🔍 Testing Salesforce matches:")
    token = get_salesforce_token()
    if token:
        for name in test_names:
            print(f"\n🎯 Testing: {name}")
            event = find_salesforce_event_by_exact_subject(token, name)
            if event:
                print(f"  ✅ Found: {event['Subject']}")
                print(f"      Normalized: {event.get('Subject_Normalized__c', 'N/A')}")
            else:
                print(f"  ❌ No match")
    else:
        print("❌ No token")

if __name__ == "__main__":
    test_normalized_matching()