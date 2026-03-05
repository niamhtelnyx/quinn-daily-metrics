#!/usr/bin/env python3
"""
Systematic debugging for V1_DATE_FULL_FUZZY hanging issues
Tests individual components in isolation to identify the hang point
"""

import subprocess
import time
import signal
import os
import threading
from datetime import datetime

def run_with_timeout(func, timeout_seconds=30):
    """Run function with timeout to detect hangs"""
    result = {"completed": False, "error": None, "output": None}
    
    def target():
        try:
            result["output"] = func()
            result["completed"] = True
        except Exception as e:
            result["error"] = str(e)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        print(f"❌ TIMEOUT: Function hung after {timeout_seconds}s")
        return None
    elif result["error"]:
        print(f"❌ ERROR: {result['error']}")
        return None
    else:
        print(f"✅ COMPLETED: {timeout_seconds}s timeout")
        return result["output"]

def test_basic_imports():
    """Test if basic imports work without hanging"""
    print("\n=== Testing Basic Imports ===")
    
    def import_test():
        try:
            import requests
            import sqlite3
            import json
            import os
            import re
            from datetime import datetime
            return "Basic imports successful"
        except Exception as e:
            return f"Import failed: {e}"
    
    return run_with_timeout(import_test, 10)

def test_salesforce_token():
    """Test Salesforce token retrieval in isolation"""
    print("\n=== Testing Salesforce Token ===")
    
    def sf_token_test():
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        import requests
        
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        username = os.getenv('SALESFORCE_USERNAME')
        password = os.getenv('SALESFORCE_PASSWORD')
        
        if not all([client_id, client_secret, username, password]):
            return "Missing Salesforce credentials"
        
        # Test token request
        data = {
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'password': password
        }
        
        response = requests.post(
            'https://login.salesforce.com/services/oauth2/token',
            data=data,
            timeout=10  # Short timeout for debugging
        )
        
        if response.status_code == 200:
            return f"Salesforce token successful: {response.json()['access_token'][:20]}..."
        else:
            return f"Salesforce token failed: {response.status_code} - {response.text}"
    
    return run_with_timeout(sf_token_test, 15)

def test_google_drive_access():
    """Test Google Drive access in isolation"""
    print("\n=== Testing Google Drive Access ===")
    
    def gog_test():
        # Simple gog command test
        result = subprocess.run([
            'gog', 'drive', 'ls', 
            '--parent', '1LGMJSQaFqS0wFJXJCW5-rHCjlO3lQHLc',  # Meeting Notes folder
            '--max', '3',
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return f"Google Drive access successful: {len(result.stdout.split())} items"
        else:
            return f"Google Drive failed: {result.stderr}"
    
    return run_with_timeout(gog_test, 20)

def test_salesforce_query():
    """Test Salesforce SOQL query in isolation"""
    print("\n=== Testing Salesforce Query ===")
    
    def sf_query_test():
        from dotenv import load_dotenv
        load_dotenv()
        
        import requests
        import os
        
        # Get token first
        data = {
            'grant_type': 'password',
            'client_id': os.getenv('SALESFORCE_CLIENT_ID'),
            'client_secret': os.getenv('SALESFORCE_CLIENT_SECRET'),
            'username': os.getenv('SALESFORCE_USERNAME'),
            'password': os.getenv('SALESFORCE_PASSWORD')
        }
        
        token_response = requests.post(
            'https://login.salesforce.com/services/oauth2/token',
            data=data,
            timeout=10
        )
        
        if token_response.status_code != 200:
            return f"Token failed: {token_response.status_code}"
        
        token_data = token_response.json()
        access_token = token_data['access_token']
        instance_url = token_data['instance_url']
        
        # Simple test query
        query = "SELECT Id, Subject FROM Event WHERE Subject LIKE 'Meeting Booked:%' ORDER BY CreatedDate DESC LIMIT 3"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        query_response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': query},
            headers=headers,
            timeout=15  # Specific timeout for query
        )
        
        if query_response.status_code == 200:
            results = query_response.json()
            return f"Salesforce query successful: {results['totalSize']} events found"
        else:
            return f"Salesforce query failed: {query_response.status_code} - {query_response.text[:200]}"
    
    return run_with_timeout(sf_query_test, 25)

def test_fuzzy_logic_isolation():
    """Test the fuzzy matching logic without external APIs"""
    print("\n=== Testing Fuzzy Matching Logic ===")
    
    def fuzzy_test():
        import re
        
        def normalize_text(text):
            """Normalize text for fuzzy matching"""
            normalized = re.sub(r'[^a-zA-Z0-9]', '', text.upper())
            return normalized
        
        def extract_keywords(text):
            """Extract meaningful keywords"""
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
            return [word.upper() for word in words if word.lower() not in ['meeting', 'booked', 'and', 'the']]
        
        # Test cases
        test_cases = [
            "Morgan & Aliyana -- Telnyx",
            "samir@cenango.com and Eric- 30-minute Meeting",
            "Telnyx & Glia Sync",
            "HomeWav - Telnyx"
        ]
        
        results = []
        for case in test_cases:
            normalized = normalize_text(case)
            keywords = extract_keywords(case)
            results.append(f"{case[:30]} → {normalized[:20]} | Keywords: {keywords}")
        
        return f"Fuzzy logic test completed: {len(results)} cases processed"
    
    return run_with_timeout(fuzzy_test, 5)

def main():
    """Run all debugging tests"""
    print("🔍 DEBUGGING V1_DATE_FULL_FUZZY HANGING ISSUES")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    # Test each component
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Google Drive Access", test_google_drive_access),
        ("Fuzzy Logic", test_fuzzy_logic_isolation),
        ("Salesforce Token", test_salesforce_token),
        ("Salesforce Query", test_salesforce_query)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        start_time = time.time()
        result = test_func()
        duration = time.time() - start_time
        results[test_name] = {
            'result': result,
            'duration': duration,
            'status': 'PASS' if result else 'FAIL/HANG'
        }
        print(f"Duration: {duration:.2f}s")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 DEBUGGING SUMMARY")
    print(f"{'='*60}")
    for test_name, data in results.items():
        status_emoji = "✅" if data['status'] == 'PASS' else "❌"
        print(f"{status_emoji} {test_name}: {data['status']} ({data['duration']:.2f}s)")
        if data['result']:
            print(f"   → {data['result']}")
    
    print(f"\nTotal time: {time.time() - start_time:.2f}s")
    print(f"End time: {datetime.now()}")

if __name__ == "__main__":
    main()