#!/usr/bin/env python3
"""
Database operations for call processing tracking
"""

import sqlite3
from config import *

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_chars INTEGER,
            content_type TEXT,
            has_transcript BOOLEAN,
            has_summary BOOLEAN,
            salesforce_event_id TEXT,
            main_posted BOOLEAN,
            thread_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("📊 Database initialized")

def is_meeting_processed(meeting_name, today_date):
    """Check if meeting has already been processed"""
    dedup_key = f"{meeting_name.lower().replace(' ', '_').replace('/', '_')}_{today_date}"
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result is not None

def save_processed_meeting(meeting_name, meeting_folder_id, content_data, content_type, 
                         salesforce_info, main_posted, thread_posted):
    """Save processed meeting to database"""
    today_date = get_today_date()
    dedup_key = f"{meeting_name.lower().replace(' ', '_').replace('/', '_')}_{today_date}"
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Extract info from content_data and salesforce_info
    content_chars = content_data.get('total_chars', 0) if content_data else 0
    has_transcript = content_data.get('has_transcript', False) if content_data else False
    has_summary = content_data.get('has_summary', False) if content_data else False
    
    salesforce_event_id = None
    if salesforce_info and isinstance(salesforce_info, dict):
        event_record = salesforce_info.get('event_record')
        if event_record:
            salesforce_event_id = event_record.get('Id')
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO processed_calls 
            (dedup_key, meeting_folder_id, event_name, content_chars, content_type, 
             has_transcript, has_summary, salesforce_event_id, main_posted, thread_posted) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (dedup_key, meeting_folder_id, meeting_name, content_chars, content_type, 
              has_transcript, has_summary, salesforce_event_id, main_posted, thread_posted))
        
        conn.commit()
        print(f"        💾 Saved to database")
        
    except Exception as e:
        print(f"        ❌ Database save error: {str(e)[:50]}")
    
    conn.close()

def get_processing_stats():
    """Get processing statistics"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    today_date = get_today_date()
    
    # Get today's stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN main_posted = 1 THEN 1 ELSE 0 END) as posted,
            SUM(CASE WHEN has_transcript = 1 THEN 1 ELSE 0 END) as transcript_count,
            SUM(CASE WHEN has_summary = 1 THEN 1 ELSE 0 END) as summary_count,
            SUM(CASE WHEN salesforce_event_id IS NOT NULL THEN 1 ELSE 0 END) as salesforce_matches
        FROM processed_calls 
        WHERE DATE(processed_at) = ?
    ''', (today_date,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'total': result[0],
            'posted': result[1], 
            'transcript_count': result[2],
            'summary_count': result[3],
            'salesforce_matches': result[4],
            'success_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0
        }
    else:
        return {
            'total': 0, 'posted': 0, 'transcript_count': 0, 
            'summary_count': 0, 'salesforce_matches': 0, 'success_rate': 0
        }

def cleanup_old_records(days_to_keep=30):
    """Clean up old records to prevent database bloat"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM processed_calls 
        WHERE processed_at < datetime('now', '-{} days')
    '''.format(days_to_keep))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"🗑️ Cleaned up {deleted} old records")
    
    return deleted