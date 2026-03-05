#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence with Hanging Prevention
Resilient version with circuit breakers, timeouts, and memory management
"""

import subprocess
import time
import signal
import sqlite3
import requests
import json
import os
import re
import threading
from datetime import datetime
from dotenv import load_dotenv

# Global circuit breaker for Salesforce API
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker OPEN - Salesforce API unavailable")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            
            raise e

# Global circuit breaker instance
sf_circuit_breaker = CircuitBreaker()

def run_gog_command(command, timeout=30, max_retries=2):
    """Run gog command with timeout and retries"""
    for attempt in range(max_retries + 1):
        try:
            print(f"    🔧 Running (attempt {attempt + 1}): {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"    ⚠️ Command failed (attempt {attempt + 1}): {result.stderr}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Command timeout (attempt {attempt + 1})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"    ❌ Command error (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    
    raise Exception(f"Command failed after {max_retries + 1} attempts")

def get_salesforce_token(timeout=20):
    """Get Salesforce token with circuit breaker protection"""
    def _get_token():
        load_dotenv()
        
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET') 
        username = os.getenv('SALESFORCE_USERNAME')
        password = os.getenv('SALESFORCE_PASSWORD')
        
        if not all([client_id, client_secret, username, password]):
            raise Exception("Missing Salesforce credentials")
        
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
            timeout=timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"Salesforce auth failed: {response.status_code}")
        
        return response.json()
    
    return sf_circuit_breaker.call(_get_token)

def find_salesforce_event_with_resilience(event_name, access_token, instance_url, timeout=25):
    """Find Salesforce event with timeout and error handling"""
    def _find_event():
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Try exact match first (fastest)
        exact_query = f"Meeting Booked: {event_name}"
        soql = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject = '{exact_query}' LIMIT 1"
        
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': soql},
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                return result['records'][0], 'exact'
        
        # Skip fuzzy matching if in production and under time pressure
        if os.getenv('SKIP_FUZZY_MATCHING', '').lower() == 'true':
            return None, None
        
        # Simplified fuzzy matching (reduced complexity)
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', event_name)  # Longer keywords only
        keywords = [word.upper() for word in keywords[:2] if word.lower() not in ['meeting', 'booked', 'and', 'the', 'copy']]
        
        if not keywords:
            return None, None
        
        # Single keyword search to reduce query complexity
        main_keyword = keywords[0]
        fuzzy_query = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject LIKE 'Meeting Booked:%{main_keyword}%' LIMIT 3"
        
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': fuzzy_query},
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                # Return first match for simplicity
                return result['records'][0], 'fuzzy'
        
        return None, None
    
    return sf_circuit_breaker.call(_find_event)

def process_meetings_with_batching(meetings, batch_size=3):
    """Process meetings in small batches to prevent resource exhaustion"""
    results = {
        'processed': 0,
        'slack_posts': 0,
        'errors': 0,
        'skipped': 0
    }
    
    # Set up database
    db_path = 'v1_date_resilient.db'
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
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
    conn.commit()
    
    # Get Salesforce token once for all meetings
    try:
        sf_token_data = get_salesforce_token()
        access_token = sf_token_data['access_token']
        instance_url = sf_token_data['instance_url']
        print("🔑 Salesforce token obtained")
    except Exception as e:
        print(f"❌ Salesforce token failed: {str(e)}")
        conn.close()
        return results
    
    # Process in batches
    for batch_start in range(0, len(meetings), batch_size):
        batch = meetings[batch_start:batch_start + batch_size]
        print(f"\n📦 Processing batch {batch_start//batch_size + 1}: {len(batch)} meetings")
        
        for meeting in batch:
            try:
                meeting_name = meeting['clean_name']
                
                # Extract clean event name
                event_name = meeting_name
                if event_name.startswith("Copy of "):
                    event_name = event_name[8:].strip()
                
                # Create dedup key
                dedup_key = f"{event_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}"
                
                # Check if already processed
                cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
                if cursor.fetchone():
                    print(f"      ⏭️ SKIPPING: Already processed ({dedup_key[:30]}...)")
                    results['skipped'] += 1
                    continue
                
                print(f"    🆕 Processing: '{event_name}'")
                
                # Find Salesforce event with resilience
                try:
                    sf_event, match_type = find_salesforce_event_with_resilience(
                        event_name, access_token, instance_url
                    )
                    
                    if sf_event:
                        print(f"      🎯 Event: ✅ Found via {match_type} match")
                        
                        # Record in database
                        cursor.execute('''
                            INSERT OR IGNORE INTO processed_calls 
                            (dedup_key, call_id, event_name, match_type, salesforce_event_id) 
                            VALUES (?, ?, ?, ?, ?)
                        ''', (dedup_key, meeting['id'], event_name, match_type, sf_event['Id']))
                        conn.commit()
                        
                        # Simulate Slack posting (skip actual posting for debugging)
                        print(f"      📱 Would post to Slack: {event_name[:50]}...")
                        results['slack_posts'] += 1
                    else:
                        print(f"      🔍 Event: ❌ No event found")
                        
                        # Record as unmatched
                        cursor.execute('''
                            INSERT OR IGNORE INTO processed_calls 
                            (dedup_key, call_id, event_name, match_type) 
                            VALUES (?, ?, ?, ?)
                        ''', (dedup_key, meeting['id'], event_name, 'none'))
                        conn.commit()
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    print(f"      ❌ Salesforce error: {str(e)[:100]}")
                    results['errors'] += 1
                
                # Small delay between meetings to prevent overload
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      ❌ Meeting processing error: {str(e)[:100]}")
                results['errors'] += 1
        
        # Longer delay between batches
        if batch_start + batch_size < len(meetings):
            print(f"    💤 Batch delay: 2 seconds")
            time.sleep(2)
    
    conn.close()
    return results

def main():
    """Main resilient processing function"""
    print("🛡️ V1 Enhanced Call Intelligence - RESILIENT VERSION")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    # Set environment for resilient mode
    os.environ['SKIP_FUZZY_MATCHING'] = 'false'  # Enable fuzzy but simplified
    
    try:
        # Step 1: Get today's date folder
        load_dotenv()
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Processing date: {today}")
        
        # Step 2: List Meeting Notes folder
        meeting_notes_output = run_gog_command([
            'gog', 'drive', 'ls',
            '--parent', '1LGMJSQaFqS0wFJXJCW5-rHCjlO3lQHLc',
            '--max', '20',
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], timeout=45)
        
        if not meeting_notes_output.strip():
            print("❌ No items found in Meeting Notes folder")
            return
        
        lines = [line.strip() for line in meeting_notes_output.strip().split('\n') if line.strip()]
        print(f"📂 Found {len(lines)} items in Meeting Notes")
        
        # Step 3: Find today's folder
        today_folder = None
        for line in lines:
            if today in line:
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    today_folder = parts[0]
                    print(f"🎯 Found today's folder: {parts[1]} ({today_folder})")
                    break
        
        if not today_folder:
            print(f"❌ No folder found for {today}")
            return
        
        # Step 4: Get meetings in today's folder
        meetings_output = run_gog_command([
            'gog', 'drive', 'ls',
            '--parent', today_folder,
            '--max', '15',  # Limit to prevent overload
            '--plain',
            '--account', 'niamh@telnyx.com'
        ], timeout=45)
        
        if not meetings_output.strip():
            print("❌ No meetings found in today's folder")
            return
        
        meeting_lines = [line.strip() for line in meetings_output.strip().split('\n') if line.strip()]
        print(f"📋 Found {len(meeting_lines)} meetings")
        
        meetings = []
        for line in meeting_lines:
            parts = line.split(None, 1)
            if len(parts) >= 2:
                meetings.append({
                    'id': parts[0],
                    'name': parts[1],
                    'clean_name': parts[1].strip()
                })
        
        print(f"📊 Prepared {len(meetings)} meetings for processing")
        
        # Step 5: Process with resilient batching
        results = process_meetings_with_batching(meetings, batch_size=3)
        
        # Final summary
        print(f"\n{'=' * 60}")
        print("📊 RESILIENT PROCESSING SUMMARY:")
        print(f"{'=' * 60}")
        print(f"    📁 Meetings found: {len(meetings)}")
        print(f"    🎉 Calls processed: {results['processed']}")
        print(f"    📱 Slack posts: {results['slack_posts']}")
        print(f"    ⏭️ Skipped: {results['skipped']}")
        print(f"    ❌ Errors: {results['errors']}")
        print(f"    🎯 Database: v1_date_resilient.db")
        print(f"    ⚡ Circuit breaker: {sf_circuit_breaker.state}")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        print(f"⚡ Circuit breaker state: {sf_circuit_breaker.state}")

if __name__ == "__main__":
    main()