#!/usr/bin/env python3
"""
Post Quinn handoffs message to Slack
"""

import os
import requests
import json

def find_channel_id(channel_name, token):
    """Find channel ID by name"""
    url = "https://slack.com/api/conversations.list"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for channel in data.get('channels', []):
                if channel['name'] == channel_name.replace('#', ''):
                    return channel['id']
    except Exception as e:
        print(f"Error finding channel: {e}")
    return None

def post_message(channel_id, message, token):
    """Post message to Slack channel"""
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
                print(f"✅ Message posted successfully to channel {channel_id}")
                return True
            else:
                print(f"❌ Slack API error: {result.get('error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error posting message: {e}")
    return False

def main():
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
    
    # Find channel
    channel_id = find_channel_id('quinn-daily-metrics', token)
    if not channel_id:
        print("❌ Could not find #quinn-daily-metrics channel")
        print("Available channels:")
        # List some channels for debugging
        url = "https://slack.com/api/conversations.list"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for channel in data.get('channels', [])[:10]:  # First 10 channels
                print(f"  #{channel['name']} ({channel['id']})")
        return False
    
    print(f"✅ Found channel: #{channel_id}")
    
    # Message to post
    message = """📈 *Quinn Handoffs Update - March 05, 2026*

• *Total Handoffs:* 2000 (24h)
• *Trending:* First day 
• *Peak Hour:* N/A
• *Top Reasons:* Product - Portal Sign Up, Marketing - Contact Sales, Product - General
• *7d Average:* N/A (when available)

🚨 *Key Insights:* High volume day

_Daily handoffs tracking • Automated at 2pm CST_"""
    
    # Post message
    return post_message(channel_id, message, token)

if __name__ == "__main__":
    main()