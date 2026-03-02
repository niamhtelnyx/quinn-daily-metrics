#!/usr/bin/env python3
"""
Test V1 Components - Validate all parts of the cron job system
"""

import os
import sys
import sqlite3
from datetime import datetime

def test_database():
    """Test database connectivity and setup"""
    print("🔍 Testing database...")
    
    try:
        conn = sqlite3.connect('ae_call_analysis.db')
        cursor = conn.cursor()
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['calls', 'analysis_results', 'cron_runs']
        for table in required_tables:
            if table in tables:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ⚠️ Table '{table}' missing - will be created")
        
        # Check calls count
        cursor.execute("SELECT COUNT(*) FROM calls")
        call_count = cursor.fetchone()[0]
        print(f"   📊 {call_count} calls in database")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {str(e)}")
        return False

def test_enhanced_processor():
    """Test enhanced call processor import"""
    print("🔍 Testing enhanced processor...")
    
    try:
        from enhanced_call_processor import EnhancedCallProcessor
        processor = EnhancedCallProcessor()
        print("   ✅ Enhanced processor imported successfully")
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Processor error: {str(e)}")
        return False

def test_fellow_api_key():
    """Test Fellow API key configuration"""
    print("🔍 Testing Fellow API configuration...")
    
    api_key = os.getenv('FELLOW_API_KEY')
    
    if api_key:
        print(f"   ✅ Fellow API key found: {api_key[:20]}...")
        
        # Test API connectivity (optional - may fail if key is invalid)
        try:
            import requests
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://telnyx.fellow.app/api/v1/recordings',
                headers=headers,
                json={},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                recordings = data.get('recordings', {}).get('data', [])
                print(f"   ✅ Fellow API working: {len(recordings)} recordings accessible")
            elif response.status_code == 401:
                print(f"   ⚠️ Fellow API key unauthorized - may need updating")
            else:
                print(f"   ⚠️ Fellow API returned: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Fellow API test failed: {str(e)}")
            
        return True
    else:
        print(f"   ❌ No Fellow API key found")
        return False

def test_slack_integration():
    """Test Slack integration"""
    print("🔍 Testing Slack integration...")
    
    try:
        import slack_integration
        print("   ✅ Slack integration module available")
        return True
    except ImportError:
        print("   ⚠️ slack_integration.py not found - alerts may not work")
        return False

def test_salesforce_integration():
    """Test Salesforce integration"""
    print("🔍 Testing Salesforce integration...")
    
    try:
        from salesforce_event_integration import SalesforceEventIntegration
        print("   ✅ Salesforce event integration available")
        
        # Test CLI integration
        result = os.popen('cd .. && python3 salesforce_client.py --help 2>/dev/null').read()
        if result:
            print("   ✅ Salesforce CLI integration available")
        else:
            print("   ⚠️ Salesforce CLI may need setup")
            
        return True
    except ImportError:
        print("   ⚠️ Salesforce integration not found")
        return False

def test_cron_job():
    """Test the cron job script"""
    print("🔍 Testing cron job script...")
    
    if os.path.exists('fellow_cron_job.py'):
        print("   ✅ fellow_cron_job.py exists")
        
        # Try importing it
        try:
            from fellow_cron_job import FellowCronProcessor
            processor = FellowCronProcessor()
            print("   ✅ Cron job processor can be imported")
            return True
        except Exception as e:
            print(f"   ❌ Cron job import error: {str(e)}")
            return False
    else:
        print("   ❌ fellow_cron_job.py not found")
        return False

def test_dependencies():
    """Test Python dependencies"""
    print("🔍 Testing Python dependencies...")
    
    dependencies = ['requests', 'sqlite3', 'json', 'datetime']
    all_good = True
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"   ✅ {dep} available")
        except ImportError:
            print(f"   ❌ {dep} missing")
            all_good = False
    
    return all_good

def run_component_test():
    """Run all component tests"""
    print("🧪 V1 COMPONENT VALIDATION")
    print("=" * 40)
    print()
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Database", test_database),
        ("Enhanced Processor", test_enhanced_processor),
        ("Fellow API Key", test_fellow_api_key),
        ("Slack Integration", test_slack_integration),
        ("Salesforce Integration", test_salesforce_integration),
        ("Cron Job Script", test_cron_job),
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"{'='*20}")
        results[name] = test_func()
        print()
    
    # Summary
    print("📊 VALIDATION SUMMARY")
    print("=" * 25)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🚀 V1 SYSTEM READY FOR LAUNCH!")
        print("\nNext steps:")
        print("1. Run: chmod +x setup_cron_v1.sh")
        print("2. Run: ./setup_cron_v1.sh")
        print("3. Set up 30-minute crontab")
        print("4. Monitor first few runs")
    else:
        print("\n⚠️ Some components need attention before launch")
        print("Review failed tests above")
    
    return passed == total

if __name__ == "__main__":
    success = run_component_test()
    sys.exit(0 if success else 1)