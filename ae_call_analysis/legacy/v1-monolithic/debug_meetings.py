#!/usr/bin/env python3
"""
Debug: Check if Google Drive meetings exist in Salesforce at all
"""

from V1_DATE_FULL import get_salesforce_token
import requests

def debug_missing_meetings():
    token = get_salesforce_token()
    if not token:
        print("❌ No Salesforce token")
        return
    
    print("🔍 Checking if Google Drive meetings exist in Salesforce...")
    
    # Get ALL events from the last few days, not just "Meeting Booked"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    query = "SELECT Id, Subject, CreatedDate FROM Event WHERE CreatedDate >= YESTERDAY ORDER BY CreatedDate DESC LIMIT 30"
    
    try:
        response = requests.get(
            "https://telnyx.my.salesforce.com/services/data/v57.0/query",
            params={"q": query}, 
            headers=headers, 
            timeout=30
        )
        if response.status_code == 200:
            results = response.json()
            events = results["records"]
            print(f"📋 Found {len(events)} total Salesforce events (last 2 days):")
            
            # Google Drive meeting keywords to search for
            drive_keywords = ["collie", "morgan", "aliyana", "lightspeed", "adrian", "mike", "allo", "spam", "evan", "jonathan"]
            
            potential_matches = []
            
            for event in events:
                subject = event["Subject"].lower()
                matches = [word for word in drive_keywords if word in subject]
                
                if matches:
                    potential_matches.append({
                        'subject': event["Subject"],
                        'matches': matches,
                        'id': event["Id"]
                    })
                    
                # Show first 15 regardless
                if len(events) <= 15 or matches:
                    marker = "🎯" if matches else "  "
                    print(f"{marker} {event['Subject'][:80]}")
                    if matches:
                        print(f"    → Keywords found: {matches}")
            
            print(f"\n📊 ANALYSIS:")
            print(f"   📅 Total events: {len(events)}")
            print(f"   🎯 Potential matches: {len(potential_matches)}")
            
            if len(potential_matches) == 0:
                print(f"\n❌ CONCLUSION: Google Drive meetings are NOT in Salesforce")
                print(f"   → These might be:")
                print(f"     - Old meetings (before yesterday)")
                print(f"     - Meetings not booked through Calendly/Salesforce")
                print(f"     - Internal meetings (no prospects)")
                print(f"     - Test meetings")
            else:
                print(f"\n✅ FOUND POTENTIAL MATCHES:")
                for match in potential_matches:
                    print(f"   🎯 {match['subject']}")
                    print(f"      Keywords: {match['matches']}")
                    print(f"      ID: {match['id']}")
        else:
            print(f"❌ Query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_missing_meetings()