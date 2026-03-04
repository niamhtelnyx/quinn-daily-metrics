#!/usr/bin/env python3
"""
V1 Production - Simple Call Intelligence Automation
Run this script to process Fellow calls and update Salesforce
"""

import requests
import json
import os
import sqlite3
from datetime import datetime
from v1_working import get_recent_fellow_calls, test_salesforce_oauth, format_simple_alert

def update_salesforce_event(call_data, access_token):
    """Update Salesforce event with call info"""
    # This would find and update the relevant Salesforce event
    # For V1, we'll just log what would be updated
    
    prospect_name = call_data.get('title', '').split('(')[1].split(')')[0] if '(' in call_data.get('title', '') else 'Unknown'
    fellow_url = f"https://telnyx.fellow.app/recordings/{call_data.get('id', '')}"
    
    print(f"🏢 SALESFORCE UPDATE (simulated):")
    print(f"   Prospect: {prospect_name}")
    print(f"   Fellow Link: {fellow_url}")
    print(f"   Status: Would update Event record")
    
    return True

def process_new_calls():
    """Process any new Fellow calls"""
    print("🔍 Checking for new Fellow intro calls...")
    
    calls, status = get_recent_fellow_calls()
    if not calls:
        print(f"   {status}")
        return False
    
    print(f"   Found {len(calls)} total intro calls")
    
    # Get the most recent call
    latest_call = calls[0]
    call_id = latest_call.get('id')
    title = latest_call.get('title', 'Unknown')
    
    # Check if we've already processed this call
    db_path = 'v1_processed_calls.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            fellow_id TEXT UNIQUE,
            prospect_name TEXT,
            processed_at TEXT,
            alert_sent BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Check if already processed
    cursor.execute('SELECT * FROM processed_calls WHERE fellow_id = ?', (call_id,))
    if cursor.fetchone():
        print(f"   ✅ Call already processed: {title}")
        conn.close()
        return False
    
    print(f"   🆕 New call found: {title}")
    
    # Process the call
    print(f"📝 Processing call...")
    
    # Generate alert
    alert = format_simple_alert(latest_call)
    print(f"   ✅ Alert generated")
    
    # Test Salesforce
    sf_ok, sf_msg = test_salesforce_oauth()
    if sf_ok:
        print(f"   {sf_msg}")
        # In production, would update Salesforce here
        # update_salesforce_event(latest_call, token)
        print(f"   ✅ Salesforce ready for update")
    else:
        print(f"   ❌ Salesforce issue: {sf_msg}")
    
    # Save to database
    prospect_name = title.split('(')[1].split(')')[0] if '(' in title else 'Unknown'
    cursor.execute('''
        INSERT INTO processed_calls (fellow_id, prospect_name, processed_at, alert_sent)
        VALUES (?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), True))
    
    conn.commit()
    conn.close()
    
    # Save alert for manual posting
    alert_file = f'v1_alert_{call_id}.txt'
    with open(alert_file, 'w') as f:
        f.write(alert)
    
    print(f"💾 Alert saved to: {alert_file}")
    
    print("\n" + "=" * 50)
    print("📱 READY FOR SLACK:")
    print("=" * 50)
    print(alert)
    print("=" * 50)
    print(f"\n✅ V1 processing complete for {prospect_name}")
    
    return True

def main():
    """Run V1 automation"""
    print("🚀 V1 Call Intelligence - Production Run")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if process_new_calls():
        print("\n🎯 Action Required:")
        print("   1. Copy the alert above")
        print("   2. Post to #bot-testing Slack channel")
        print("   3. V1 complete! ✅")
    else:
        print("\n😴 No new calls to process")
    
    print(f"\n🔄 Run this script regularly to check for new calls")

if __name__ == "__main__":
    main()