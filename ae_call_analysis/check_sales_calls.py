#!/usr/bin/env python3
"""
Check if bot has access to #sales-calls channel
"""

import os
import requests

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def check_sales_calls_channel():
    """Check if bot can access #sales-calls"""
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'https://slack.com/api/conversations.list',
        headers=headers,
        params={'types': 'public_channel,private_channel', 'limit': 200}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            channels = result.get('channels', [])
            
            sales_calls_channel = None
            for ch in channels:
                if ch.get('name') == 'sales-calls':
                    sales_calls_channel = ch
                    break
            
            if sales_calls_channel:
                is_member = sales_calls_channel.get('is_member', False)
                print(f"✅ Found #sales-calls channel")
                print(f"📋 Bot member: {'Yes' if is_member else 'No'}")
                
                if is_member:
                    print("🎯 Ready to post to #sales-calls!")
                    return True
                else:
                    print("⚠️ Bot not member of #sales-calls")
                    print("💡 Add bot with: /invite @bot-name")
                    return False
            else:
                print("❌ #sales-calls channel not found")
                print("📋 Available channels with 'sales' in name:")
                for ch in channels:
                    name = ch.get('name', '')
                    if 'sales' in name.lower():
                        is_member = "✅" if ch.get('is_member', False) else "❌"
                        print(f"   {is_member} #{name}")
                return False
    
    return False

if __name__ == "__main__":
    print("🔍 Checking #sales-calls channel access...")
    check_sales_calls_channel()