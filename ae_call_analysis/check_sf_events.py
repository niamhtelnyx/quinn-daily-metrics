#!/usr/bin/env python3
"""
Check what Salesforce events exist today to debug event matching
"""

from V1_DATE_FULL import get_salesforce_token
import requests
import os

def check_salesforce_events():
    token = get_salesforce_token()
    if not token:
        print("❌ No Salesforce token")
        return
    
    print("✅ Salesforce authenticated")
    
    # Search for recent events with "Meeting Booked"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Query for today's events
    query = """
    SELECT Id, Subject, CreatedDate 
    FROM Event 
    WHERE Subject LIKE 'Meeting Booked:%' 
    AND CreatedDate >= TODAY 
    ORDER BY CreatedDate DESC 
    LIMIT 15
    """
    
    try:
        response = requests.get(
            "https://telnyx.my.salesforce.com/services/data/v57.0/query",
            params={"q": query}, 
            headers=headers, 
            timeout=30
        )
        if response.status_code == 200:
            results = response.json()
            if results["records"]:
                print(f"\n📋 Found {len(results['records'])} Salesforce events today:")
                for i, event in enumerate(results["records"], 1):
                    subject = event["Subject"]
                    event_name = subject.replace("Meeting Booked: ", "")
                    print(f"  {i}. {subject}")
                    print(f"     → Event name: '{event_name}'")
                    print(f"     → ID: {event['Id']}")
                    print()
                    
                # Also check what we're searching for
                print("🔍 What the system is searching for:")
                meeting_names = [
                    "Allo-Telnyx - Spam",
                    "Telnyx -- Collie", 
                    "Morgan & Aliyana -- Telnyx",
                    "Lightspeed -- Telnyx",
                    "Adrian - Mike"
                ]
                
                for name in meeting_names:
                    search_subject = f"Meeting Booked: {name}"
                    found = any(event["Subject"] == search_subject for event in results["records"])
                    status = "✅" if found else "❌"
                    print(f"  {status} {search_subject}")
                    
            else:
                print("❌ No 'Meeting Booked' events found today")
        else:
            print(f"❌ Salesforce query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Query error: {e}")

if __name__ == "__main__":
    check_salesforce_events()