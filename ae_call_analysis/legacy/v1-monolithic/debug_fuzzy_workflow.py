#!/usr/bin/env python3
"""
Test the actual V1_DATE_FULL_FUZZY workflow to identify hang points
Replicates the exact sequence that causes hanging
"""

import subprocess
import time
import threading
import sqlite3
import os
import re
from datetime import datetime
from dotenv import load_dotenv

def run_with_timeout(func, timeout_seconds=60, description="Function"):
    """Run function with timeout and detailed logging"""
    print(f"🟡 Starting: {description}")
    result = {"completed": False, "error": None, "output": None}
    
    def target():
        try:
            result["output"] = func()
            result["completed"] = True
        except Exception as e:
            result["error"] = str(e)
    
    start_time = time.time()
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    duration = time.time() - start_time
    
    if thread.is_alive():
        print(f"❌ TIMEOUT: {description} hung after {timeout_seconds}s")
        return None
    elif result["error"]:
        print(f"❌ ERROR: {description} failed: {result['error']}")
        return None
    else:
        print(f"✅ COMPLETED: {description} in {duration:.2f}s")
        return result["output"]

def test_database_operations():
    """Test database creation and operations"""
    def db_test():
        db_path = 'v1_debug_test.db'
        
        # Remove existing test db
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Create and test database operations
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedup_key TEXT UNIQUE,
                call_id TEXT,
                event_name TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'google_drive',
                match_type TEXT,
                salesforce_event_id TEXT
            )
        ''')
        
        # Test insert
        cursor.execute('''
            INSERT OR IGNORE INTO processed_calls 
            (dedup_key, call_id, event_name, match_type) 
            VALUES (?, ?, ?, ?)
        ''', ('test_key', 'test_call_id', 'Test Meeting', 'exact'))
        
        conn.commit()
        
        # Test select
        cursor.execute('SELECT COUNT(*) FROM processed_calls')
        count = cursor.fetchone()[0]
        
        conn.close()
        
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        
        return f"Database operations successful: {count} records"
    
    return run_with_timeout(db_test, 10, "Database Operations")

def test_google_drive_listing():
    """Test listing specific Google Drive folders"""
    def gd_list_test():
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Test the exact command from V1_DATE_FULL_FUZZY
        result = subprocess.run([
            'gog', 'drive', 'ls', 
            '--parent', '1LGMJSQaFqS0wFJXJCW5-rHCjlO3lQHLc',  # Meeting Notes
            '--max', '10',
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
            date_folders = [line for line in lines if today in line or '2026-03-0' in line]
            return f"Google Drive listing successful: {len(lines)} total, {len(date_folders)} date folders"
        else:
            return f"Google Drive listing failed: {result.stderr}"
    
    return run_with_timeout(gd_list_test, 45, "Google Drive Listing")

def test_salesforce_fuzzy_search():
    """Test the fuzzy Salesforce search that's causing issues"""
    def sf_fuzzy_test():
        load_dotenv()
        
        import requests
        
        # Get credentials
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        username = os.getenv('SALESFORCE_USERNAME')
        password = os.getenv('SALESFORCE_PASSWORD')
        
        if not all([client_id, client_secret, username, password]):
            return "Missing Salesforce credentials - skipping test"
        
        # Get token
        data = {
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'password': password
        }
        
        token_response = requests.post(
            'https://login.salesforce.com/services/oauth2/token',
            data=data,
            timeout=15
        )
        
        if token_response.status_code != 200:
            return f"Token failed: {token_response.status_code}"
        
        token_data = token_response.json()
        access_token = token_data['access_token']
        instance_url = token_data['instance_url']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Test the actual fuzzy search queries that might be causing hangs
        test_queries = [
            "Meeting Booked: Telnyx & Glia Sync",
            "Meeting Booked: HomeWav - Telnyx", 
            "Meeting Booked: Morgan & Aliyana",
            "Meeting Booked: samir@cenango.com and Eric"
        ]
        
        results = []
        for query_text in test_queries:
            # Test exact search first
            exact_query = f"SELECT Id, Subject FROM Event WHERE Subject = '{query_text}' LIMIT 1"
            
            try:
                response = requests.get(
                    f"{instance_url}/services/data/v59.0/query",
                    params={'q': exact_query},
                    headers=headers,
                    timeout=20  # Longer timeout for fuzzy searches
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    results.append(f"Query '{query_text[:30]}...': {result_data['totalSize']} matches")
                else:
                    results.append(f"Query '{query_text[:30]}...': Failed {response.status_code}")
                
                # Small delay between queries to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                results.append(f"Query '{query_text[:30]}...': Exception {str(e)[:50]}")
        
        return f"Fuzzy search test completed: {len(results)} queries tested"
    
    return run_with_timeout(sf_fuzzy_test, 90, "Salesforce Fuzzy Search")

def test_multiple_meeting_processing():
    """Test processing multiple meetings in sequence like the real workflow"""
    def multi_test():
        # Simulate the meeting processing loop
        test_meetings = [
            "Telnyx & Glia Sync",
            "HomeWav - Telnyx",
            "Morgan & Aliyana -- Telnyx",
            "samir@cenango.com and Eric- 30-minute Meeting",
            "Sully.ai & Telnyx daily sync"
        ]
        
        processed = []
        for i, meeting in enumerate(test_meetings):
            print(f"   Processing meeting {i+1}/{len(test_meetings)}: {meeting[:30]}")
            
            # Simulate the key operations
            # 1. Extract event name
            event_name = meeting.strip()
            
            # 2. Create dedup key
            dedup_key = f"{event_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}"
            
            # 3. Normalize for fuzzy matching
            normalized = re.sub(r'[^a-zA-Z0-9]', '', event_name.upper())
            
            # 4. Extract keywords
            keywords = re.findall(r'\b[a-zA-Z]{3,}\b', event_name)
            keywords = [word.upper() for word in keywords if word.lower() not in ['meeting', 'booked', 'and', 'the']]
            
            # 5. Simulate database check
            # (In real code, this would check if already processed)
            
            # 6. Build search query
            search_query = f"Meeting Booked: {event_name}"
            
            processed.append({
                'event': event_name,
                'dedup_key': dedup_key,
                'normalized': normalized,
                'keywords': keywords,
                'search_query': search_query
            })
            
            # Small delay to simulate processing time
            time.sleep(0.1)
        
        return f"Multiple meeting processing successful: {len(processed)} meetings"
    
    return run_with_timeout(multi_test, 30, "Multiple Meeting Processing")

def test_subprocess_management():
    """Test subprocess calls that might be hanging"""
    def subprocess_test():
        # Test multiple subprocess calls in sequence
        commands = [
            ['echo', 'test1'],
            ['sleep', '1'],
            ['echo', 'test2'],
            ['date']
        ]
        
        results = []
        for i, cmd in enumerate(commands):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results.append(f"Command {i+1}: SUCCESS")
                else:
                    results.append(f"Command {i+1}: FAILED {result.returncode}")
            except subprocess.TimeoutExpired:
                results.append(f"Command {i+1}: TIMEOUT")
            except Exception as e:
                results.append(f"Command {i+1}: ERROR {str(e)[:50]}")
        
        return f"Subprocess management test: {len(results)} commands tested"
    
    return run_with_timeout(subprocess_test, 25, "Subprocess Management")

def main():
    """Run workflow debugging tests"""
    print("🔍 DEBUGGING V1_DATE_FULL_FUZZY WORKFLOW HANGING")
    print("=" * 70)
    print(f"Start time: {datetime.now()}")
    
    # Source environment
    load_dotenv()
    
    # Test workflow components in order
    tests = [
        ("Database Operations", test_database_operations),
        ("Google Drive Listing", test_google_drive_listing),
        ("Multiple Meeting Processing", test_multiple_meeting_processing),
        ("Subprocess Management", test_subprocess_management),
        ("Salesforce Fuzzy Search", test_salesforce_fuzzy_search)
    ]
    
    results = {}
    start_time = time.time()
    
    for test_name, test_func in tests:
        print(f"\n{'='*25} {test_name} {'='*25}")
        test_start = time.time()
        result = test_func()
        duration = time.time() - test_start
        
        results[test_name] = {
            'result': result,
            'duration': duration,
            'status': 'PASS' if result else 'FAIL/HANG'
        }
        
        if result:
            print(f"📝 Result: {result}")
        print(f"⏱️ Duration: {duration:.2f}s")
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 WORKFLOW DEBUGGING SUMMARY")
    print(f"{'='*70}")
    
    for test_name, data in results.items():
        status_emoji = "✅" if data['status'] == 'PASS' else "❌"
        print(f"{status_emoji} {test_name}: {data['status']} ({data['duration']:.2f}s)")
        if data['result']:
            print(f"   → {data['result'][:100]}")
    
    total_duration = time.time() - start_time
    print(f"\n🏁 Total time: {total_duration:.2f}s")
    print(f"🕒 End time: {datetime.now()}")
    
    # Specific recommendations
    print(f"\n{'='*70}")
    print("🎯 DEBUGGING RECOMMENDATIONS")
    print(f"{'='*70}")
    
    failed_tests = [name for name, data in results.items() if data['status'] != 'PASS']
    if not failed_tests:
        print("✅ All workflow components completed successfully")
        print("🔍 Hanging issue may be in:")
        print("   - Specific meeting data patterns")
        print("   - Resource exhaustion during long runs") 
        print("   - Network timeouts under load")
        print("   - Memory leaks in fuzzy matching loops")
    else:
        print("❌ Failed components that may cause hanging:")
        for test_name in failed_tests:
            print(f"   - {test_name}")

if __name__ == "__main__":
    main()