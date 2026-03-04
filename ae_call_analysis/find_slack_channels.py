#!/usr/bin/env python3
"""
Find available Slack channels for the bot
"""

import os
import requests

def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def list_slack_channels():
    """List available Slack channels"""
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ SLACK_BOT_TOKEN not found")
        return
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    # Get public channels
    print("📋 Listing Slack channels...")
    
    response = requests.get(
        'https://slack.com/api/conversations.list',
        headers=headers,
        params={'types': 'public_channel,private_channel', 'limit': 100}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            channels = result.get('channels', [])
            
            print(f"✅ Found {len(channels)} channels:")
            print()
            
            # Look for relevant channels
            relevant_channels = []
            for channel in channels:
                name = channel.get('name', '')
                is_member = channel.get('is_member', False)
                
                if any(keyword in name.lower() for keyword in ['call', 'ae', 'intelligence', 'sales', 'demo']):
                    relevant_channels.append(channel)
                    status = "✅ Bot is member" if is_member else "❌ Bot not member"
                    print(f"🎯 #{name} - {status}")
            
            if not relevant_channels:
                print("⚠️ No relevant channels found. Showing first 10 channels:")
                for channel in channels[:10]:
                    name = channel.get('name', '')
                    is_member = channel.get('is_member', False)
                    status = "✅" if is_member else "❌"
                    print(f"   {status} #{name}")
            
            print()
            print("💡 Suggestions:")
            print("1. Create #ae-call-intelligence channel")
            print("2. Add the bot to the channel")
            print("3. Or use an existing channel where bot is member")
            
        else:
            print(f"❌ Slack API error: {result.get('error')}")
    else:
        print(f"❌ HTTP error: {response.status_code}")

if __name__ == "__main__":
    list_slack_channels()