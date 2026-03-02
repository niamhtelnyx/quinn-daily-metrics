#!/usr/bin/env python3
"""
AE Call Analysis - Authentication Status Check

Diagnoses Claude API authentication status and provides guidance
for refreshing expired tokens.
"""
import json
import time
from pathlib import Path
from datetime import datetime

def check_auth_status():
    """Check all authentication sources and report status."""
    
    print("=" * 70)
    print("🔍 AE Call Analysis - Authentication Status Check")
    print("=" * 70)
    print()
    
    current_time_ms = int(time.time() * 1000)
    valid_token_found = False
    
    # Check 1: Environment Variables
    print("📋 CHECK 1: Environment Variables")
    print("-" * 40)
    import os
    env_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        print(f"   ✅ Found API key: {env_key[:15]}...{env_key[-5:]}")
        valid_token_found = True
    else:
        print("   ⚪ No CLAUDE_API_KEY or ANTHROPIC_API_KEY set")
    print()
    
    # Check 2: Claude CLI Credentials
    print("📋 CHECK 2: Claude CLI (~/.claude/.credentials.json)")
    print("-" * 40)
    cli_path = Path.home() / ".claude" / ".credentials.json"
    if cli_path.exists():
        with open(cli_path) as f:
            creds = json.load(f)
        oauth = creds.get('claudeAiOauth', {})
        token = oauth.get('accessToken')
        expires = oauth.get('expiresAt', 0)
        
        if token:
            print(f"   Token: {token[:25]}...{token[-10:]}")
            expire_date = datetime.fromtimestamp(expires / 1000)
            
            if expires > current_time_ms:
                days = (expires - current_time_ms) // 86400000
                print(f"   ✅ Valid! Expires: {expire_date} ({days} days)")
                valid_token_found = True
            else:
                hours_ago = (current_time_ms - expires) // 3600000
                print(f"   ❌ EXPIRED: {expire_date} ({hours_ago} hours ago)")
                print(f"   💡 Run: claude    (to refresh)")
        else:
            print("   ⚪ No OAuth token found")
    else:
        print("   ⚪ File not found")
    print()
    
    # Check 3: Clawdbot Auth Profiles
    print("📋 CHECK 3: Clawdbot (~/.clawdbot/agents/main/agent/auth-profiles.json)")
    print("-" * 40)
    clawdbot_path = Path.home() / ".clawdbot" / "agents" / "main" / "agent" / "auth-profiles.json"
    if clawdbot_path.exists():
        with open(clawdbot_path) as f:
            auth_data = json.load(f)
        
        profiles = auth_data.get('profiles', {})
        for name, profile in profiles.items():
            if 'anthropic' not in name.lower():
                continue
            
            print(f"   Profile: {name}")
            
            if profile.get('type') == 'oauth':
                token = profile.get('access', '')[:25] + "..."
                expires = profile.get('expires', 0)
                expire_date = datetime.fromtimestamp(expires / 1000) if expires else "N/A"
                
                if expires > current_time_ms:
                    days = (expires - current_time_ms) // 86400000
                    print(f"      ✅ Valid OAuth! Expires: {expire_date} ({days} days)")
                    valid_token_found = True
                else:
                    hours_ago = (current_time_ms - expires) // 3600000 if expires else 0
                    print(f"      ❌ EXPIRED OAuth: {expire_date} ({hours_ago}h ago)")
            elif profile.get('type') == 'token':
                token = profile.get('token', '')[:20] + "..."
                print(f"      Token: {token}")
                print(f"      ⚠️ Simple token (may be invalid)")
        
        if not any('anthropic' in n.lower() for n in profiles):
            print("   ⚪ No Anthropic profiles found")
    else:
        print("   ⚪ File not found")
    print()
    
    # Summary
    print("=" * 70)
    if valid_token_found:
        print("✅ RESULT: Valid authentication found!")
        print()
        print("You can test with:")
        print("   cd /Users/niamhcollins/clawd/ae_call_analysis")
        print("   python3 e2e_test.py")
    else:
        print("❌ RESULT: All tokens expired or missing!")
        print()
        print("TO FIX - Choose one option:")
        print()
        print("  Option 1 - Refresh Claude CLI (easiest):")
        print("     $ claude")
        print("     (Opens Claude Code, which refreshes your OAuth token)")
        print()
        print("  Option 2 - Set API key directly:")
        print("     $ export ANTHROPIC_API_KEY='sk-ant-api...'")
        print("     (Get from console.anthropic.com if you have access)")
    print("=" * 70)

if __name__ == "__main__":
    check_auth_status()
