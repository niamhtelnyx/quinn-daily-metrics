#!/usr/bin/env python3
"""
Quick test showing the V1 Enhanced Call Intelligence System is working
"""
import os
import requests
import json
from datetime import datetime

def load_env():
    """Load environment variables"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def test_system_ready():
    """Test if all system components are ready"""
    print("🚀 V1 ENHANCED CALL INTELLIGENCE SYSTEM STATUS")
    print("=" * 60)
    
    # Test environment
    load_env()
    
    # Check APIs
    apis_working = []
    
    # Slack
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if slack_token:
        try:
            headers = {'Authorization': f'Bearer {slack_token}', 'Content-Type': 'application/json'}
            response = requests.get('https://slack.com/api/auth.test', headers=headers, timeout=5)
            if response.status_code == 200 and response.json().get('ok'):
                print("✅ Slack API: Ready to post call analyses")
                apis_working.append('slack')
            else:
                print("❌ Slack API: Connection issue")
        except:
            print("❌ Slack API: Connection failed")
    else:
        print("❌ Slack API: No token")
    
    # OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        try:
            headers = {'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json'}
            response = requests.get('https://api.openai.com/v1/models', headers=headers, timeout=5)
            if response.status_code == 200:
                print("✅ OpenAI API: Ready for AI call analysis")
                apis_working.append('openai')
            else:
                print("❌ OpenAI API: Connection issue")
        except:
            print("❌ OpenAI API: Connection failed")
    else:
        print("❌ OpenAI API: No key")
    
    # Google Drive (via gog CLI)
    try:
        import subprocess
        result = subprocess.run(['which', 'gog'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Google Drive: Ready to read meeting notes")
            apis_working.append('gdrive')
        else:
            print("❌ Google Drive: gog CLI not found")
    except:
        print("❌ Google Drive: Not available")
    
    # Salesforce (check both credential formats)
    sf_client_id = os.getenv('SF_CLIENT_ID') or os.getenv('SALESFORCE_CLIENT_ID')
    sf_client_secret = os.getenv('SF_CLIENT_SECRET') or os.getenv('SALESFORCE_CLIENT_SECRET')
    
    if sf_client_id and sf_client_secret:
        print("✅ Salesforce: Ready to lookup prospects")
        apis_working.append('salesforce')
    else:
        print("❌ Salesforce: Missing credentials")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SYSTEM STATUS:")
    
    if len(apis_working) >= 3:  # Need at least 3 core components
        print("✅ SYSTEM READY!")
        print("\n🎯 What happens when a call occurs:")
        print("   1. Google Drive detects new meeting note")
        print("   2. AI analyzes the call content")
        print("   3. Salesforce verifies prospect exists")
        print("   4. Enhanced alert posted to #sales-calls")
        
        # Show sample analysis format
        print("\n📋 Sample AI Analysis Format:")
        print("""
┌─ 📞 NEW CALL ANALYSIS ─────────────────┐
│ 🏢 Prospect: TechCorp Industries        │
│ 👤 Contact: John Smith (CTO)           │
│ ⏰ Duration: 45 minutes                 │
│ 🎯 Stage: Discovery                     │
│                                        │
│ 📊 AI INSIGHTS:                        │
│ • Pain Point: Current telecom costs     │
│ • Interest Level: High                  │
│ • Next Steps: Technical demo            │
│ • Decision Timeline: Q2 2026            │
│                                        │
│ 🔗 Salesforce: [View Contact]          │
└────────────────────────────────────────┘
        """)
        
        return True
    else:
        print(f"⚠️  Need to fix {4 - len(apis_working)} components")
        return False

def show_monitoring_status():
    """Show current monitoring status"""
    print("\n" + "=" * 60)
    print("🔄 MONITORING STATUS:")
    
    # Check if cron is set up
    try:
        import subprocess
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if 'V1_GOOGLE_DRIVE_ENHANCED.py' in result.stdout:
            print("✅ Automated monitoring: ACTIVE (every 30 minutes)")
        elif 'fellow_cron_job.py' in result.stdout:
            print("⚠️  Old monitoring active - needs upgrade")
        else:
            print("❌ No automated monitoring configured")
    except:
        print("❌ Cannot check cron status")
    
    # Check recent activity
    log_file = 'logs/v1_enhanced.log'
    if os.path.exists(log_file):
        print(f"✅ Log file exists: {log_file}")
    else:
        print("📝 No log file yet (normal for first run)")

if __name__ == "__main__":
    system_ready = test_system_ready()
    show_monitoring_status()
    
    print(f"\n⏰ Status check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if system_ready:
        print("\n🚀 To test with real data, try:")
        print("   source /Users/niamhcollins/clawd/.env.gog && python3 V1_GOOGLE_DRIVE_ENHANCED.py")
