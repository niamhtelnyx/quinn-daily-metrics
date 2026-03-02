#!/usr/bin/env python3
"""
Production deployment script for Call Intelligence API
Supports Railway, Heroku, and DigitalOcean
"""

import subprocess
import sys
import os
import json

def check_requirements():
    """Check if deployment requirements are met"""
    print("🔍 Checking deployment requirements...")
    
    required_files = [
        'demo_call_api.py',
        'requirements.txt', 
        'Dockerfile',
        'railway.json'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} missing")
            return False
    
    return True

def deploy_railway():
    """Deploy to Railway"""
    print("\n🚄 DEPLOYING TO RAILWAY")
    print("=" * 30)
    
    try:
        # Check if railway CLI is installed
        subprocess.run(['railway', '--version'], check=True, capture_output=True)
        print("✅ Railway CLI found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI not found. Install with: npm install -g @railway/cli")
        print("   Or visit: https://docs.railway.app/develop/cli")
        return False
    
    try:
        print("🔑 Logging into Railway...")
        subprocess.run(['railway', 'login'], check=True)
        
        print("📦 Creating Railway project...")
        subprocess.run(['railway', 'init'], check=True)
        
        print("🚀 Deploying to Railway...")
        result = subprocess.run(['railway', 'up'], check=True, capture_output=True, text=True)
        
        print("✅ Deployment successful!")
        print(result.stdout)
        
        # Get the URL
        url_result = subprocess.run(['railway', 'domain'], capture_output=True, text=True)
        if url_result.returncode == 0:
            print(f"🌐 Your production URL: {url_result.stdout.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Railway deployment failed: {str(e)}")
        return False

def deploy_heroku():
    """Deploy to Heroku"""
    print("\n🟣 DEPLOYING TO HEROKU")
    print("=" * 25)
    
    # Create Procfile
    with open('Procfile', 'w') as f:
        f.write('web: python -m uvicorn demo_call_api:app --host 0.0.0.0 --port $PORT\n')
    print("✅ Created Procfile")
    
    try:
        # Check if heroku CLI is installed
        subprocess.run(['heroku', '--version'], check=True, capture_output=True)
        print("✅ Heroku CLI found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Heroku CLI not found. Install from: https://devcenter.heroku.com/articles/heroku-cli")
        return False
    
    app_name = input("Enter Heroku app name (or press Enter for auto-generated): ").strip()
    
    try:
        if app_name:
            subprocess.run(['heroku', 'create', app_name], check=True)
        else:
            subprocess.run(['heroku', 'create'], check=True)
        
        print("🚀 Deploying to Heroku...")
        subprocess.run(['git', 'init'], check=True)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Deploy Call Intelligence API'], check=True)
        subprocess.run(['heroku', 'git:remote', '-a', app_name if app_name else 'auto'], check=True)
        subprocess.run(['git', 'push', 'heroku', 'main'], check=True)
        
        print("✅ Heroku deployment successful!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Heroku deployment failed: {str(e)}")
        return False

def test_local():
    """Test the API locally before deployment"""
    print("\n🧪 TESTING LOCALLY")
    print("=" * 20)
    
    try:
        import requests
        import time
        
        print("🚀 Starting local server for testing...")
        
        # Start the server in background
        process = subprocess.Popen([
            'python', '-m', 'uvicorn', 'demo_call_api:app', 
            '--host', '0.0.0.0', '--port', '8083'
        ])
        
        # Wait for server to start
        time.sleep(3)
        
        # Test health endpoint
        response = requests.get('http://localhost:8083/health', timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            
            # Test main endpoint
            test_call = {
                "prospect_name": "Production Test",
                "title": "Production Test Call",
                "transcript": "Test transcript for production deployment",
                "call_date": "2026-02-28"
            }
            
            response = requests.post(
                'http://localhost:8083/process-call',
                json=test_call,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ API test passed - Call ID: {result['call_id']}")
            else:
                print(f"❌ API test failed: {response.status_code}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
        # Stop the test server
        process.terminate()
        process.wait()
        
        return True
        
    except Exception as e:
        print(f"❌ Local test failed: {str(e)}")
        return False

def main():
    print("🚀 CALL INTELLIGENCE API - PRODUCTION DEPLOYMENT")
    print("=" * 55)
    
    if not check_requirements():
        print("\n❌ Deployment requirements not met")
        sys.exit(1)
    
    # Test locally first
    if not test_local():
        print("\n❌ Local testing failed")
        sys.exit(1)
    
    print("\n🎯 Choose deployment platform:")
    print("1️⃣ Railway (fastest, free tier)")
    print("2️⃣ Heroku (reliable, credit card required)")
    print("3️⃣ Manual (I'll deploy myself)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        success = deploy_railway()
    elif choice == '2':
        success = deploy_heroku()
    elif choice == '3':
        print("\n📋 Manual deployment instructions:")
        print("1. Push code to your Git repository")
        print("2. Connect repository to your cloud platform")
        print("3. Set environment variables if needed")
        print("4. Deploy using platform's interface")
        success = True
    else:
        print("❌ Invalid choice")
        sys.exit(1)
    
    if success:
        print("\n🎉 DEPLOYMENT COMPLETE!")
        print("\n📋 Next steps:")
        print("1. Test your production URL")
        print("2. Update Zapier webhook with new URL")
        print("3. Monitor logs for any issues")
        print("4. Add real API credentials as environment variables")
    else:
        print("\n❌ Deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    main()