#!/usr/bin/env python3
"""
Post Quinn Metrics to Slack
"""

import subprocess
import sys
import json
from pathlib import Path

def post_to_slack(message: str, channel: str = "#quinn-daily-metrics"):
    """Post message to Slack using Clawdbot message tool"""
    
    # Use Clawdbot's message tool to post to Slack
    script_content = f"""
import sys
sys.path.append('/opt/homebrew/lib/node_modules/clawdbot')

# Post using Clawdbot's message API
from clawdbot.message import message

result = message({{
    "action": "send", 
    "channel": "slack",
    "target": "{channel}",
    "message": "{message.replace('"', '\\"')}"
}})

print(json.dumps(result))
"""
    
    try:
        result = subprocess.run([
            'python3', '-c', script_content
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ Posted to {channel}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to post to {channel}: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: post-quinn-metrics.py <message_file_or_text>")
        sys.exit(1)
    
    message_input = sys.argv[1]
    
    # Check if it's a file path
    if Path(message_input).exists():
        with open(message_input, 'r') as f:
            message = f.read().strip()
    else:
        message = message_input
    
    # Post to Slack
    success = post_to_slack(message)
    
    if not success:
        print("❌ Failed to post to Slack")
        sys.exit(1)
    
    print("✅ Quinn metrics posted successfully!")

if __name__ == "__main__":
    main()