#!/usr/bin/env python3
"""
Utility script to check and manage unmatched Salesforce contacts
"""

import sqlite3
import json
from datetime import datetime

def get_unmatched_contacts(days=7):
    """Get unmatched contacts from the last N days"""
    db_path = 'v2_enhanced.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, prospect_name, prospect_email, call_id, source, call_date, created_at, notes
        FROM unmatched_contacts 
        WHERE created_at >= datetime('now', '-{} days')
        ORDER BY created_at DESC
    '''.format(days))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_summary_stats():
    """Get summary statistics for unmatched contacts"""
    db_path = 'v2_enhanced.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total unmatched
    cursor.execute('SELECT COUNT(*) FROM unmatched_contacts')
    total_unmatched = cursor.fetchone()[0]
    
    # Today's unmatched
    cursor.execute('SELECT COUNT(*) FROM unmatched_contacts WHERE DATE(created_at) = DATE("now")')
    today_unmatched = cursor.fetchone()[0]
    
    # This week's unmatched
    cursor.execute('SELECT COUNT(*) FROM unmatched_contacts WHERE created_at >= datetime("now", "-7 days")')
    week_unmatched = cursor.fetchone()[0]
    
    # By source
    cursor.execute('SELECT source, COUNT(*) FROM unmatched_contacts GROUP BY source')
    by_source = cursor.fetchall()
    
    conn.close()
    
    return {
        'total': total_unmatched,
        'today': today_unmatched,
        'this_week': week_unmatched,
        'by_source': by_source
    }

def display_unmatched_contacts():
    """Display unmatched contacts in a readable format"""
    print("🔍 V2 Enhanced Call Intelligence - Unmatched Contacts Report")
    print("=" * 60)
    
    # Get summary stats
    stats = get_summary_stats()
    print(f"📊 Summary Statistics:")
    print(f"   Total unmatched: {stats['total']}")
    print(f"   Today: {stats['today']}")
    print(f"   This week: {stats['this_week']}")
    print(f"   By source: {dict(stats['by_source'])}")
    print()
    
    # Get recent unmatched contacts
    unmatched = get_unmatched_contacts(days=7)
    
    if not unmatched:
        print("✅ No unmatched contacts in the last 7 days!")
        return
    
    print(f"📋 Recent Unmatched Contacts (Last 7 Days): {len(unmatched)} contacts")
    print("-" * 60)
    
    for contact in unmatched:
        id, name, email, call_id, source, call_date, created_at, notes = contact
        print(f"🆔 #{id}")
        print(f"👤 Name: {name}")
        print(f"📧 Email: {email}")
        print(f"📞 Call ID: {call_id}")
        print(f"📁 Source: {source}")
        print(f"📅 Call Date: {call_date}")
        print(f"⏰ Added: {created_at}")
        print(f"📝 Notes: {notes}")
        print("-" * 40)

def export_unmatched_to_csv():
    """Export unmatched contacts to CSV for further processing"""
    import csv
    from datetime import datetime
    
    unmatched = get_unmatched_contacts(days=30)  # Last 30 days
    
    filename = f"unmatched_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Prospect Name', 'Prospect Email', 'Call ID', 'Source', 'Call Date', 'Created At', 'Notes'])
        
        for contact in unmatched:
            writer.writerow(contact)
    
    print(f"📊 Exported {len(unmatched)} unmatched contacts to {filename}")

if __name__ == "__main__":
    try:
        display_unmatched_contacts()
        
        print("\n" + "=" * 60)
        print("🔧 Available Actions:")
        print("1. Export to CSV for review: python3 check_unmatched_contacts.py --export")
        print("2. Check database directly: sqlite3 v2_enhanced.db")
        print("3. Query unmatched: SELECT * FROM unmatched_contacts ORDER BY created_at DESC;")
        
    except Exception as e:
        print(f"❌ Error: {e}")