#!/usr/bin/env python3
"""
Multi-run version: Runs search-based processing 2 times with 15-minute gap
Simulates 15-minute intervals within 30-minute cron job
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
import threading
from datetime import datetime
from dotenv import load_dotenv

def run_gog_command(command, timeout=30):
    """Run gog command with timeout"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except subprocess.TimeoutExpired:
        return None

def process_search_based_calls():
    """Process calls using search (without Salesforce for now)"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Processing date: {today}")
    
    # Database setup
    db_path = 'v1_multi_run.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            call_id TEXT,
            event_name TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'google_drive_search'
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
        return {'processed': 0, 'found': 0}
    
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
                clean_name = re.sub(r' - \d{4}/\d{2}/\d{2} \d{2}:\d{2}.*$', '', clean_name)
                
                meetings.append({
                    'id': file_id,
                    'name': file_name,
                    'clean_name': clean_name.strip()
                })
    
    print(f"📋 Found {len(meetings)} Gemini notes from today")
    
    # Process each meeting (without Salesforce for now)
    processed = 0
    
    for meeting in meetings:
        event_name = meeting['clean_name']
        dedup_key = f"{event_name.lower().replace(' ', '_')}_{today}"
        
        # Check if already processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            continue
        
        # Record the call
        cursor.execute('''
            INSERT OR IGNORE INTO processed_calls 
            (dedup_key, call_id, event_name) 
            VALUES (?, ?, ?)
        ''', (dedup_key, meeting['id'], event_name))
        conn.commit()
        
        print(f"    📝 Logged: {event_name[:50]}...")
        processed += 1
    
    conn.close()
    return {'processed': processed, 'found': len(meetings)}

def main():
    """Run multi-run processing (2 runs with 15-min gap)"""
    print("🔄 V1 MULTI-RUN CALL INTELLIGENCE (15-min intervals)")
    print("=" * 60)
    start_time = datetime.now()
    print(f"Start time: {start_time}")
    
    # First run
    print(f"\n📅 FIRST RUN ({start_time.strftime('%H:%M:%S')})")
    result1 = process_search_based_calls()
    
    # Show first run results
    print(f"✅ First run: {result1['processed']} processed, {result1['found']} found")
    
    # Calculate wait time (15 minutes)
    wait_seconds = 15 * 60
    next_run_time = datetime.fromtimestamp(time.time() + wait_seconds)
    print(f"\n⏰ WAITING 15 MINUTES...")
    print(f"   Next run scheduled: {next_run_time.strftime('%H:%M:%S')}")
    
    # Wait 15 minutes
    time.sleep(wait_seconds)
    
    # Second run
    second_start = datetime.now()
    print(f"\n📅 SECOND RUN ({second_start.strftime('%H:%M:%S')})")
    result2 = process_search_based_calls()
    
    # Show second run results
    print(f"✅ Second run: {result2['processed']} processed, {result2['found']} found")
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'=' * 60}")
    print("📊 MULTI-RUN SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    🕐 Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
    print(f"    📅 First run: {result1['processed']} new calls")
    print(f"    📅 Second run: {result2['processed']} new calls")
    print(f"    📊 Total processed: {result1['processed'] + result2['processed']}")
    print(f"    🎯 Database: v1_multi_run.db")

if __name__ == "__main__":
    main()