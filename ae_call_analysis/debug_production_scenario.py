#!/usr/bin/env python3
"""
Replicate the exact production scenario that causes hanging
Process real Google Drive meetings with actual fuzzy matching logic
"""

import subprocess
import time
import threading
import sqlite3
import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

def run_with_timeout_and_monitoring(func, timeout_seconds=120, description="Function"):
    """Run function with timeout and memory monitoring"""
    print(f"🟡 Starting: {description}")
    result = {"completed": False, "error": None, "output": None, "memory_usage": []}
    
    def target():
        try:
            result["output"] = func()
            result["completed"] = True
        except Exception as e:
            result["error"] = str(e)
    
    def memory_monitor():
        """Monitor memory usage during execution"""
        import psutil
        process = psutil.Process()
        while result["completed"] == False:
            try:
                memory_mb = process.memory_info().rss / 1024 / 1024
                result["memory_usage"].append(memory_mb)
                time.sleep(1)
            except:
                break
    
    start_time = time.time()
    
    # Start memory monitoring
    try:
        import psutil
        memory_thread = threading.Thread(target=memory_monitor)
        memory_thread.daemon = True
        memory_thread.start()
        memory_monitoring = True
    except ImportError:
        memory_monitoring = False
    
    # Start main function
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    duration = time.time() - start_time
    
    # Results
    if thread.is_alive():
        print(f"❌ TIMEOUT: {description} hung after {timeout_seconds}s")
        if memory_monitoring and result["memory_usage"]:
            max_memory = max(result["memory_usage"])
            print(f"   💾 Memory at timeout: {max_memory:.1f}MB")
        return None
    elif result["error"]:
        print(f"❌ ERROR: {description} failed: {result['error']}")
        return None
    else:
        print(f"✅ COMPLETED: {description} in {duration:.2f}s")
        if memory_monitoring and result["memory_usage"]:
            max_memory = max(result["memory_usage"])
            print(f"   💾 Peak memory: {max_memory:.1f}MB")
        return result["output"]

def get_real_google_drive_meetings():
    """Get actual meetings from Google Drive today"""
    def get_meetings():
        load_dotenv()
        
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"   📅 Looking for date: {today}")
        
        # Get Meeting Notes folder contents
        result = subprocess.run([
            'gog', 'drive', 'ls', 
            '--parent', '1LGMJSQaFqS0wFJXJCW5-rHCjlO3lQHLc',  # Meeting Notes
            '--max', '20',
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return f"Failed to list Meeting Notes: {result.stderr}"
        
        lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        print(f"   📂 Found {len(lines)} items in Meeting Notes")
        
        # Find today's folder
        today_folder = None
        for line in lines:
            if today in line:
                # Extract folder ID (format: "folder_id folder_name")
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    today_folder = parts[0]
                    print(f"   🎯 Found today's folder: {parts[1]} ({today_folder})")
                    break
        
        if not today_folder:
            return f"No folder found for {today} in {len(lines)} items"
        
        # Get meetings in today's folder
        meeting_result = subprocess.run([
            'gog', 'drive', 'ls', 
            '--parent', today_folder,
            '--max', '20',
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=30)
        
        if meeting_result.returncode != 0:
            return f"Failed to list meetings: {meeting_result.stderr}"
        
        meeting_lines = [line.strip() for line in meeting_result.stdout.strip().split('\n') if line.strip()]
        print(f"   📋 Found {len(meeting_lines)} meetings")
        
        meetings = []
        for line in meeting_lines:
            parts = line.split(None, 1)
            if len(parts) >= 2:
                folder_id = parts[0]
                folder_name = parts[1]
                meetings.append({
                    'id': folder_id,
                    'name': folder_name,
                    'clean_name': folder_name.strip()
                })
                print(f"      📁 {folder_name}")
        
        return f"Retrieved {len(meetings)} real meetings from Google Drive", meetings
    
    return run_with_timeout_and_monitoring(get_meetings, 60, "Real Google Drive Meeting Retrieval")

def test_salesforce_api_with_credentials():
    """Test Salesforce API with real credentials"""
    def sf_api_test():
        load_dotenv()
        
        # Load credentials from environment
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        username = os.getenv('SALESFORCE_USERNAME')
        password = os.getenv('SALESFORCE_PASSWORD')
        
        print(f"   🔑 Client ID: {'✓' if client_id else '✗'}")
        print(f"   🔑 Client Secret: {'✓' if client_secret else '✗'}")
        print(f"   🔑 Username: {'✓' if username else '✗'}")
        print(f"   🔑 Password: {'✓' if password else '✗'}")
        
        if not all([client_id, client_secret, username, password]):
            return "Missing Salesforce credentials in environment"
        
        # Get token
        print(f"   🌐 Requesting Salesforce token...")
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
            timeout=20
        )
        
        if token_response.status_code != 200:
            return f"Token request failed: {token_response.status_code} - {token_response.text}"
        
        token_data = token_response.json()
        access_token = token_data['access_token']
        instance_url = token_data['instance_url']
        
        print(f"   ✅ Token obtained: {access_token[:20]}...")
        print(f"   🏠 Instance URL: {instance_url}")
        
        # Test query
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        query = "SELECT Id, Subject FROM Event WHERE Subject LIKE 'Meeting Booked:%' ORDER BY CreatedDate DESC LIMIT 5"
        
        print(f"   🔍 Testing SOQL query...")
        query_response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': query},
            headers=headers,
            timeout=30
        )
        
        if query_response.status_code == 200:
            results = query_response.json()
            print(f"   📊 Query successful: {results['totalSize']} events found")
            return f"Salesforce API working: {results['totalSize']} events, token valid"
        else:
            return f"Query failed: {query_response.status_code} - {query_response.text[:200]}"
    
    return run_with_timeout_and_monitoring(sf_api_test, 90, "Salesforce API with Real Credentials")

def test_production_fuzzy_matching(meetings_data):
    """Test fuzzy matching with real meeting data"""
    def fuzzy_production_test():
        if not meetings_data or len(meetings_data) < 2:
            return "No real meetings data to test fuzzy matching"
        
        result_text, meetings = meetings_data
        print(f"   🎯 Processing {len(meetings)} real meetings for fuzzy matching")
        
        # Load Salesforce credentials
        load_dotenv()
        
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        username = os.getenv('SALESFORCE_USERNAME')
        password = os.getenv('SALESFORCE_PASSWORD')
        
        if not all([client_id, client_secret, username, password]):
            return "Missing Salesforce credentials for fuzzy matching test"
        
        # Get Salesforce token
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
            timeout=20
        )
        
        if token_response.status_code != 200:
            return f"Token failed for fuzzy test: {token_response.status_code}"
        
        token_data = token_response.json()
        access_token = token_data['access_token']
        instance_url = token_data['instance_url']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Process each meeting with fuzzy matching
        results = []
        for i, meeting in enumerate(meetings[:5]):  # Limit to 5 to avoid overload
            meeting_name = meeting['clean_name']
            print(f"      🔄 Processing {i+1}/{min(5, len(meetings))}: {meeting_name[:50]}")
            
            # Extract event name (remove "Copy of" etc.)
            event_name = meeting_name
            if event_name.startswith("Copy of "):
                event_name = event_name[8:].strip()
            
            # Normalize for fuzzy matching
            normalized = re.sub(r'[^a-zA-Z0-9]', '', event_name.upper())
            
            # Extract keywords
            keywords = re.findall(r'\b[a-zA-Z]{3,}\b', event_name)
            keywords = [word.upper() for word in keywords if word.lower() not in ['meeting', 'booked', 'and', 'the', 'copy', 'of']]
            
            # Try exact match first
            exact_query = f"Meeting Booked: {event_name}"
            soql_exact = f"SELECT Id, Subject FROM Event WHERE Subject = '{exact_query}' LIMIT 1"
            
            try:
                exact_response = requests.get(
                    f"{instance_url}/services/data/v59.0/query",
                    params={'q': soql_exact},
                    headers=headers,
                    timeout=25  # This is where hanging might occur
                )
                
                exact_matches = 0
                if exact_response.status_code == 200:
                    exact_data = exact_response.json()
                    exact_matches = exact_data['totalSize']
                
                # If no exact match, try fuzzy (this is the high-risk part)
                fuzzy_matches = 0
                if exact_matches == 0 and keywords:
                    # Build keyword-based query
                    keyword_conditions = []
                    for keyword in keywords[:3]:  # Limit keywords to prevent complex queries
                        keyword_conditions.append(f"Subject LIKE '%{keyword}%'")
                    
                    if keyword_conditions:
                        fuzzy_query = f"SELECT Id, Subject FROM Event WHERE Subject LIKE 'Meeting Booked:%' AND ({' OR '.join(keyword_conditions)}) LIMIT 5"
                        
                        print(f"         🔍 Fuzzy query: {fuzzy_query[:100]}...")
                        
                        fuzzy_response = requests.get(
                            f"{instance_url}/services/data/v59.0/query",
                            params={'q': fuzzy_query},
                            headers=headers,
                            timeout=30  # Extended timeout for complex queries
                        )
                        
                        if fuzzy_response.status_code == 200:
                            fuzzy_data = fuzzy_response.json()
                            fuzzy_matches = fuzzy_data['totalSize']
                
                results.append({
                    'meeting': meeting_name[:30],
                    'exact_matches': exact_matches,
                    'fuzzy_matches': fuzzy_matches,
                    'keywords': len(keywords)
                })
                
                print(f"         ✅ Exact: {exact_matches}, Fuzzy: {fuzzy_matches}, Keywords: {len(keywords)}")
                
                # Small delay to prevent rate limiting
                time.sleep(0.5)
                
            except requests.exceptions.Timeout:
                results.append({
                    'meeting': meeting_name[:30],
                    'error': 'TIMEOUT',
                    'keywords': len(keywords)
                })
                print(f"         ⏰ TIMEOUT on Salesforce query")
            except Exception as e:
                results.append({
                    'meeting': meeting_name[:30],
                    'error': str(e)[:50],
                    'keywords': len(keywords)
                })
                print(f"         ❌ ERROR: {str(e)[:50]}")
        
        total_processed = len(results)
        total_errors = len([r for r in results if 'error' in r])
        total_timeouts = len([r for r in results if r.get('error') == 'TIMEOUT'])
        
        return f"Fuzzy matching completed: {total_processed} meetings, {total_errors} errors, {total_timeouts} timeouts"
    
    return run_with_timeout_and_monitoring(fuzzy_production_test, 180, "Production Fuzzy Matching")

def main():
    """Run production scenario debugging"""
    print("🔍 DEBUGGING PRODUCTION SCENARIO - FUZZY MATCHING HANGING")
    print("=" * 80)
    print(f"Start time: {datetime.now()}")
    
    # Load environment
    load_dotenv()
    
    print("\n" + "="*30 + " STEP 1: Get Real Meetings " + "="*30)
    meetings_result = get_real_google_drive_meetings()
    
    print("\n" + "="*30 + " STEP 2: Test Salesforce API " + "="*30)
    salesforce_result = test_salesforce_api_with_credentials()
    
    print("\n" + "="*30 + " STEP 3: Production Fuzzy Matching " + "="*30)
    if meetings_result and isinstance(meetings_result, tuple):
        fuzzy_result = test_production_fuzzy_matching(meetings_result)
    else:
        print("❌ Skipping fuzzy matching - no meeting data")
        fuzzy_result = None
    
    # Final summary
    print("\n" + "="*80)
    print("📊 PRODUCTION DEBUGGING SUMMARY")
    print("="*80)
    
    if meetings_result:
        print("✅ Google Drive: Success")
        if isinstance(meetings_result, tuple):
            print(f"   → {meetings_result[0]}")
    else:
        print("❌ Google Drive: Failed")
    
    if salesforce_result:
        print("✅ Salesforce API: Success")
        print(f"   → {salesforce_result}")
    else:
        print("❌ Salesforce API: Failed")
    
    if fuzzy_result:
        print("✅ Fuzzy Matching: Success")
        print(f"   → {fuzzy_result}")
    else:
        print("❌ Fuzzy Matching: Failed/Skipped")
    
    print(f"\n🏁 End time: {datetime.now()}")
    
    # Final recommendations
    print("\n" + "="*80)
    print("🎯 PRODUCTION ISSUE ANALYSIS")
    print("="*80)
    
    if meetings_result and salesforce_result and fuzzy_result:
        print("✅ All production components working - hanging may be due to:")
        print("   🔄 Resource exhaustion during long cron runs")
        print("   🌐 Network latency during peak Salesforce usage")
        print("   💾 Memory leaks in fuzzy matching loops")
        print("   🐛 Race conditions in subprocess management")
        print("\n💡 RECOMMENDED FIXES:")
        print("   1. Add circuit breaker pattern for Salesforce API")
        print("   2. Implement exponential backoff for retries") 
        print("   3. Add memory usage monitoring and cleanup")
        print("   4. Process meetings in smaller batches")
        print("   5. Add health checks and auto-restart on hang detection")
    else:
        print("❌ Production components failing - fix these first:")
        if not meetings_result:
            print("   - Fix Google Drive access")
        if not salesforce_result:
            print("   - Fix Salesforce authentication")
        if not fuzzy_result:
            print("   - Fix fuzzy matching logic")

if __name__ == "__main__":
    main()