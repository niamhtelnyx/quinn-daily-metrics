#!/usr/bin/env python3
"""
Post Quinn handoffs message to #general (since #quinn-daily-metrics doesn't exist)
"""

import os
import requests
import json

def post_to_general():
    # Load environment
    env_file = "/Users/niamhcollins/clawd/ae_call_analysis/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    token = os.getenv('SLACK_BOT_TOKEN')
    if not token:
        print("❌ No SLACK_BOT_TOKEN found")
        return False
    
    # Post to #general (C033NA4CH from earlier channel list)
    channel_id = "C033NA4CH"
    
    # Updated message with data quality warning
    message = """🚨 *Quinn Handoffs Report - URGENT DATA REVIEW NEEDED*

📈 *Quinn Handoffs Update - March 05, 2026*

• *Total Handoffs:* 2,986 (24h) ⚠️
• *Trending:* +986 vs yesterday (+49%) 📈
• *Peak Hour:* N/A (timezone calc needed)
• *Top Reasons:* Product - Portal Sign Up, Marketing - Contact Sales, Quinn - Reply Received

🚨 *CRITICAL ALERT:* This volume is extremely high and likely indicates data quality issues. Normal daily volume should be 10-100, not 3000+.

*Recommended Actions:*
• Investigate Salesforce Sales_Handoff__c data for duplicates
• Verify Quinn Taylor filters are working correctly
• Check for bulk imports or data migrations today

*Note:* Channel #quinn-daily-metrics doesn't exist - posting to #general
_Daily handoffs tracking • Automated at 2pm CST_"""
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "channel": channel_id,
        "text": message,
        "mrkdwn": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Message posted successfully to #general")
                return True
            else:
                print(f"❌ Slack API error: {result.get('error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error posting message: {e}")
    return False

if __name__ == "__main__":
    post_to_general()