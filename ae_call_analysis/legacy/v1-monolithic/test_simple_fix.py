#!/usr/bin/env python3

from V1_DATE_SIMPLE_FIX import find_salesforce_event_simple_fix, get_salesforce_token

def test_simple_fix():
    token = get_salesforce_token()
    if not token:
        print("❌ No token")
        return
    
    print("✅ Testing simple fix...")
    
    test_names = [
        "Morgan & Aliyana -- Telnyx",
        "Aliyana",
        "Telnyx -- Collie"
    ]
    
    for name in test_names:
        print(f"\n🔍 Testing: {name}")
        event = find_salesforce_event_simple_fix(token, name)
        if event:
            print(f"  ✅ Found: {event['Subject']}")
            print(f"      ID: {event['Id']}")
        else:
            print(f"  ❌ No match")

if __name__ == "__main__":
    test_simple_fix()