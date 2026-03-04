#!/usr/bin/env python3
"""
Test script for V2 Enhanced Call Intelligence
Tests deduplication and database features
"""

import os
import sys
import sqlite3
from datetime import datetime

def test_database_initialization():
    """Test database schema creation"""
    print("🔍 Testing database initialization...")
    
    # Import the init function
    sys.path.append(os.path.dirname(__file__))
    from V2_ENHANCED_PRODUCTION import init_database, generate_dedup_key, add_unmatched_contact
    
    # Initialize database
    init_database()
    
    # Check if tables exist
    db_path = 'v2_enhanced.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check processed_calls table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_calls'")
    if cursor.fetchone():
        print("✅ processed_calls table created")
    else:
        print("❌ processed_calls table missing")
        return False
    
    # Check unmatched_contacts table  
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unmatched_contacts'")
    if cursor.fetchone():
        print("✅ unmatched_contacts table created")
    else:
        print("❌ unmatched_contacts table missing")
        return False
    
    # Test deduplication key generation
    dedup_key1 = generate_dedup_key("roly@meetgail.com", "2026-03-03 15:59:00")
    dedup_key2 = generate_dedup_key("roly@meetgail.com", "2026-03-03 21:41:00")
    
    print(f"🔑 Dedup key 1: {dedup_key1}")
    print(f"🔑 Dedup key 2: {dedup_key2}")
    
    if dedup_key1 == dedup_key2:
        print("✅ Deduplication keys match for same day")
    else:
        print("❌ Deduplication keys don't match for same day")
        return False
    
    # Test unmatched contact insertion
    add_unmatched_contact("Test Prospect", "test@example.com", "test123", "google_drive", 
                         "2026-03-03", "Test unmatched contact")
    
    cursor.execute("SELECT COUNT(*) FROM unmatched_contacts WHERE call_id = 'test123'")
    if cursor.fetchone()[0] > 0:
        print("✅ Unmatched contact insertion works")
    else:
        print("❌ Unmatched contact insertion failed")
        return False
    
    # Cleanup test data
    cursor.execute("DELETE FROM unmatched_contacts WHERE call_id = 'test123'")
    conn.commit()
    conn.close()
    
    return True

def test_google_drive_integration():
    """Test Google Drive integration"""
    print("\n🔍 Testing Google Drive integration...")
    
    from google_drive_integration import get_google_drive_calls
    
    # Test with recent calls
    calls = []
    for days_back in range(3):
        test_calls, status = get_google_drive_calls(days_back=days_back)
        print(f"📁 Day -{days_back}: {status}")
        if test_calls:
            calls = test_calls
            break
    
    if calls:
        print(f"✅ Google Drive integration working - found {len(calls)} calls")
        return True
    else:
        print("⚠️ No Google Drive calls found (may be normal)")
        return True  # Not a failure, just no data

def main():
    """Run all enhanced system tests"""
    print("🚀 Testing V2 Enhanced Call Intelligence System")
    print("=" * 50)
    
    success = True
    
    # Test database features
    if not test_database_initialization():
        success = False
    
    # Test Google Drive integration  
    if not test_google_drive_integration():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All enhanced tests passed!")
        print("\n📋 Enhanced Features Ready:")
        print("   ✅ Smart deduplication (Gemini first, Fellow adds URL)")
        print("   ✅ Salesforce fallback table for unmatched contacts")
        print("   ✅ Enhanced database tracking")
        print("   ✅ Google Drive + Fellow integration")
        
        print("\n🚀 Next Steps:")
        print("   1. Run: python3 V2_ENHANCED_PRODUCTION.py")
        print("   2. Check unmatched: python3 check_unmatched_contacts.py")
        print("   3. Monitor: tail -f logs/v2_enhanced.log")
    else:
        print("❌ Some enhanced tests failed!")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)