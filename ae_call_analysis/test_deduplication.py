#!/usr/bin/env python3
"""
Test script to demonstrate deduplication working
Shows how the system prevents reprocessing of calls
"""

import sys
sys.path.append('.')
from V2_RECENT_CALLS_ONLY import (
    generate_dedup_key, is_call_duplicate, is_call_id_processed,
    save_processed_call, init_database, log_message
)
import sqlite3
from datetime import datetime

def test_deduplication():
    """Test the deduplication system"""
    print("🧪 Testing Enhanced Deduplication System")
    print("=" * 50)
    
    # Initialize database
    init_database()
    
    # Test data
    test_call_1 = {
        'call_id': 'test_doc_123',
        'prospect_name': 'Test Company',
        'prospect_email': 'test@example.com',
        'ae_name': 'Test AE',
        'call_date': '2026-03-04',
        'source': 'test_recent',
        'content': 'Test content'
    }
    
    test_analysis_1 = {
        'summary': 'Test summary',
        'key_points': ['Test point 1'],
        'next_steps': ['Test next step']
    }
    
    # Generate dedup key
    dedup_key_1 = generate_dedup_key(test_call_1['prospect_email'], test_call_1['call_date'])
    print(f"📋 Generated dedup key: {dedup_key_1}")
    
    # Test 1: First time processing (should NOT be duplicate)
    print(f"\n🧪 Test 1: First time processing")
    print(f"   Checking dedup_key: {is_call_duplicate(dedup_key_1)}")
    print(f"   Checking call_id: {is_call_id_processed(test_call_1['call_id'])}")
    
    # Save the call
    print(f"\n💾 Saving call to database...")
    save_processed_call(test_call_1, test_analysis_1, dedup_key_1, 'test_slack_ts', True)
    
    # Test 2: Second time processing (SHOULD be duplicate)  
    print(f"\n🧪 Test 2: Second time processing (should be duplicate)")
    print(f"   Checking dedup_key: {is_call_duplicate(dedup_key_1)}")
    print(f"   Checking call_id: {is_call_id_processed(test_call_1['call_id'])}")
    
    # Test 3: Different call, same company (should NOT be duplicate due to different date)
    test_call_2 = test_call_1.copy()
    test_call_2['call_id'] = 'test_doc_456'
    test_call_2['call_date'] = '2026-03-05'  # Different date
    
    dedup_key_2 = generate_dedup_key(test_call_2['prospect_email'], test_call_2['call_date'])
    print(f"\n🧪 Test 3: Same company, different date")
    print(f"   New dedup key: {dedup_key_2}")
    print(f"   Checking dedup_key: {is_call_duplicate(dedup_key_2)}")
    print(f"   Checking call_id: {is_call_id_processed(test_call_2['call_id'])}")
    
    # Show database contents
    print(f"\n📊 Database Contents:")
    conn = sqlite3.connect('v2_final.db')
    cursor = conn.cursor()
    cursor.execute('SELECT prospect_name, call_id, dedup_key, processed_at FROM processed_calls WHERE source = "test_recent"')
    results = cursor.fetchall()
    
    for row in results:
        prospect, call_id, dedup_key, processed_at = row
        print(f"   📋 {prospect} | {call_id} | {dedup_key} | {processed_at}")
    
    conn.close()
    
    # Clean up test data
    print(f"\n🧹 Cleaning up test data...")
    conn = sqlite3.connect('v2_final.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM processed_calls WHERE source = "test_recent"')
    conn.commit()
    conn.close()
    
    print(f"✅ Deduplication test complete!")

if __name__ == "__main__":
    test_deduplication()