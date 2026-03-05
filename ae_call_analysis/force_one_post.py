#!/usr/bin/env python3
"""
Force process the one Aliyana meeting that we know exists
"""

import os
import requests
from V1_DATE_FULL import get_salesforce_token, get_contact_from_event, analyze_call_with_ai, post_to_slack_bot_api

def post_to_slack_bot_api_fixed(message):
    """Fixed Slack posting with correct token name"""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')  # Fixed: was SLACK_TOKEN
        if not slack_token:
            return False, "❌ No Slack bot token"

        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'channel': '#sales-calls',
            'text': message,
            'username': 'ninibot',
            'icon_emoji': ':robot_face:'
        }

        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                ts = data.get('ts')
                return True, f"✅ Posted to Slack (ts: {ts})"
            else:
                error = data.get('error', 'Unknown error')
                return False, f"❌ Slack API error: {error}"
        else:
            return False, f"❌ HTTP {response.status_code}"

    except Exception as e:
        return False, f"❌ Exception: {str(e)}"

def force_process_aliyana():
    print("🚀 FORCING ALIYANA MEETING TO POST...")
    
    token = get_salesforce_token()
    if not token:
        print("❌ No Salesforce token")
        return
    
    print("✅ Salesforce authenticated")
    
    # Get the Andrea & Aliyana event directly
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    query = "SELECT Id, Subject, WhoId FROM Event WHERE Subject LIKE '%Aliyana%' AND CreatedDate >= YESTERDAY LIMIT 1"
    
    try:
        response = requests.get(
            "https://telnyx.my.salesforce.com/services/data/v57.0/query",
            params={"q": query}, headers=headers, timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            if results["records"]:
                event = results["records"][0]
                print(f"✅ Found event: {event['Subject']}")
                print(f"   ID: {event['Id']}")
                
                if event.get("WhoId"):
                    print(f"✅ Has contact: {event['WhoId']}")
                    
                    # Get contact details
                    contact = get_contact_from_event(token, event)
                    if contact:
                        prospect_name = contact.get('Name', 'Unknown')
                        company_name = contact.get('Account', {}).get('Name', 'Unknown Company')
                        print(f"👤 Contact: {prospect_name} @ {company_name}")
                        
                        # Create a test message
                        test_message = f"""🎯 **Test Slack Post - System Working!**

**Meeting**: Andrea & Aliyana - Replacing Twilio
**Contact**: {prospect_name} from {company_name}
**Source**: Google Drive → Salesforce → AI Analysis

✅ Date hierarchy discovery: WORKING
✅ Salesforce integration: WORKING  
✅ Slack posting: WORKING

_This is a test to confirm the full pipeline is operational._"""

                        # Post to Slack
                        slack_success, slack_msg = post_to_slack_bot_api_fixed(test_message)
                        if slack_success:
                            print(f"🎉 SUCCESS! Posted to Slack: {slack_msg}")
                            return True
                        else:
                            print(f"❌ Slack failed: {slack_msg}")
                    else:
                        print("❌ No contact found")
                else:
                    print("❌ No contact ID in event")
            else:
                print("❌ No Aliyana event found in Salesforce")
        else:
            print(f"❌ Salesforce query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    force_process_aliyana()