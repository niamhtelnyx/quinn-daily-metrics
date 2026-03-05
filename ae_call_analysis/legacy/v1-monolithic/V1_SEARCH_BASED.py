#!/usr/bin/env python3
"""
Search-based call processing for scattered Google Drive files
Processes 2026-03-05 meetings regardless of folder structure
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

def run_gog_command(command, timeout=30):
    """Run gog command with timeout"""
    try:
        print(f"    🔧 Running: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"    ⚠️ Command failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"    ⏰ Command timeout")
        return None

def get_salesforce_token():
    """Get Salesforce token"""
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
        timeout=20
    )
    
    if response.status_code != 200:
        raise Exception(f"Salesforce auth failed: {response.status_code}")
    
    return response.json()

def find_salesforce_event_simple(event_name, access_token, instance_url):
    """Find Salesforce event with simple matching"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try exact match first
    exact_query = f"Meeting Booked: {event_name}"
    soql = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject = '{exact_query}' LIMIT 1"
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': soql},
            headers=headers,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                return result['records'][0], 'exact'
    except:
        pass
    
    return None, None

def process_todays_meetings():
    """Process today's meetings from search results"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Database setup
    db_path = 'v1_search_based.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            call_id TEXT,
            event_name TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'google_drive_search',
            match_type TEXT,
            salesforce_event_id TEXT
        )
    ''')
    conn.commit()
    
    # Search for today's meetings
    search_output = run_gog_command([
        'gog', 'drive', 'search',
        today,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not search_output:
        print("❌ No search results found")
        conn.close()
        return
    
    # Parse search results
    lines = search_output.strip().split('\n')
    meetings = []
    
    for line in lines[1:]:  # Skip header
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                # Skip if not a Gemini notes file
                if 'Notes by Gemini' not in file_name:
                    continue
                    
                # Extract clean meeting name
                clean_name = file_name.replace('Copy of ', '').replace(' - Notes by Gemini', '')
                # Remove date/time pattern
                clean_name = re.sub(r' - \d{4}/\d{2}/\d{2} \d{2}:\d{2}.*$', '', clean_name)
                
                meetings.append({
                    'id': file_id,
                    'name': file_name,
                    'clean_name': clean_name.strip()
                })
    
    print(f"📋 Found {len(meetings)} Gemini notes from today")
    
    # Get Salesforce token
    try:
        sf_token_data = get_salesforce_token()
        access_token = sf_token_data['access_token']
        instance_url = sf_token_data['instance_url']
        print("🔑 Salesforce token obtained")
    except Exception as e:
        print(f"❌ Salesforce token failed: {str(e)}")
        conn.close()
        return
    
    # Process each meeting
    processed = 0
    slack_posts = 0
    
    for meeting in meetings:
        event_name = meeting['clean_name']
        dedup_key = f"{event_name.lower().replace(' ', '_')}_{today}"
        
        # Check if already processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            print(f"      ⏭️ SKIPPING: {event_name[:50]}... (already processed)")
            continue
        
        print(f"    🆕 Processing: '{event_name}'")
        
        try:
            # Find Salesforce event
            sf_event, match_type = find_salesforce_event_simple(
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
                
                print(f"      📱 Would post to Slack: {event_name[:50]}...")
                slack_posts += 1
            else:
                print(f"      🔍 Event: ❌ No Salesforce match")
                
                # Record as unmatched
                cursor.execute('''
                    INSERT OR IGNORE INTO processed_calls 
                    (dedup_key, call_id, event_name, match_type) 
                    VALUES (?, ?, ?, ?)
                ''', (dedup_key, meeting['id'], event_name, 'none'))
                conn.commit()
            
            processed += 1
            time.sleep(0.5)  # Small delay
            
        except Exception as e:
            print(f"      ❌ Processing error: {str(e)[:100]}")
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("📊 SEARCH-BASED PROCESSING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    📁 Meetings found: {len(meetings)}")
    print(f"    🎉 Calls processed: {processed}")
    print(f"    📱 Slack posts: {slack_posts}")
    print(f"    🎯 Database: {db_path}")

def main():
    """Main processing function"""
    print("🔍 V1 Enhanced Call Intelligence - SEARCH-BASED VERSION")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    
    try:
        process_todays_meetings()
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    main()