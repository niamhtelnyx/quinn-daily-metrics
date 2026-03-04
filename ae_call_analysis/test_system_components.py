#!/usr/bin/env python3
"""
Quick test to verify all system components are working
"""
import os
import requests
import json
from datetime import datetime

def test_environment():
    """Test environment variables are loaded"""
    print("🔧 Testing Environment...")
    
    # Load .env
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Check required env vars
    required_vars = ['OPENAI_API_KEY', 'SLACK_BOT_TOKEN', 'SALESFORCE_CLIENT_ID']
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Configured")
        else:
            print(f"❌ {var}: Missing")

def test_slack_connection():
    """Test Slack API connection"""
    print("\n💬 Testing Slack Connection...")
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ No Slack token found")
        return False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get('https://slack.com/api/auth.test', headers=headers)
        if response.status_code == 200 and response.json().get('ok'):
            print("✅ Slack API: Connected")
            return True
        else:
            print(f"❌ Slack API: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Slack API: Error - {str(e)}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI Connection...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return False
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Simple models list call to test auth
        response = requests.get('https://api.openai.com/v1/models', headers=headers)
        if response.status_code == 200:
            print("✅ OpenAI API: Connected")
            return True
        else:
            print(f"❌ OpenAI API: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ OpenAI API: Error - {str(e)}")
        return False

def test_google_drive():
    """Test Google Drive via gog CLI"""
    print("\n📁 Testing Google Drive...")
    
    try:
        import subprocess
        result = subprocess.run(['gog', 'drive', 'search', '"newer_than:30d"', '--max', '1'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Google Drive: Connected via gog CLI")
            return True
        else:
            print(f"❌ Google Drive: Failed - {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Google Drive: Error - {str(e)}")
        return False

def test_salesforce():
    """Test Salesforce connection"""
    print("\n🏢 Testing Salesforce...")
    
    client_id = os.getenv('SALESFORCE_CLIENT_ID')
    client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    security_token = os.getenv('SALESFORCE_SECURITY_TOKEN')
    
    if not all([client_id, client_secret, username, password, security_token]):
        print("❌ Missing Salesforce credentials")
        return False
    
    try:
        # Test auth
        auth_data = {
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'password': password + security_token
        }
        
        response = requests.post('https://login.salesforce.com/services/oauth2/token', data=auth_data)
        
        if response.status_code == 200:
            print("✅ Salesforce: Connected")
            return True
        else:
            print(f"❌ Salesforce: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Salesforce: Error - {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 TESTING V1 ENHANCED CALL INTELLIGENCE SYSTEM")
    print("=" * 60)
    
    test_environment()
    slack_ok = test_slack_connection()
    openai_ok = test_openai_connection()
    gdrive_ok = test_google_drive()
    sf_ok = test_salesforce()
    
    print("\n" + "=" * 60)
    print("📊 SYSTEM STATUS SUMMARY:")
    
    if all([slack_ok, openai_ok, gdrive_ok, sf_ok]):
        print("✅ ALL SYSTEMS GO! Ready to process calls.")
        print("\n💡 To see the system in action:")
        print("   1. When new Google Drive meeting notes are created")
        print("   2. The system will automatically detect and process them")
        print("   3. AI analysis will be posted to #sales-calls Slack channel")
    else:
        print("⚠️  Some components need attention (see above)")
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
