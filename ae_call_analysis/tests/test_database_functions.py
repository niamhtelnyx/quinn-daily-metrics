#!/usr/bin/env python3
"""
Unit tests for database_functions.py
"""

import unittest
import sys
import os
import sqlite3
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the DATABASE_NAME to use a temp file
import database_functions
original_db_name = database_functions.DATABASE_NAME

class TestDatabaseFunctions(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        database_functions.DATABASE_NAME = self.temp_db.name
        database_functions.init_database()
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        database_functions.DATABASE_NAME = original_db_name
    
    def test_init_database(self):
        """Test database initialization"""
        # Database should be created
        self.assertTrue(os.path.exists(self.temp_db.name))
        
        # Table should exist with correct schema
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_calls'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        
        # Check table schema
        cursor.execute("PRAGMA table_info(processed_calls)")
        columns = [col[1] for col in cursor.fetchall()]
        expected_columns = [
            'id', 'dedup_key', 'meeting_folder_id', 'event_name', 
            'content_chars', 'content_type', 'has_transcript', 'has_summary',
            'salesforce_event_id', 'main_posted', 'thread_posted', 'processed_at'
        ]
        
        for col in expected_columns:
            self.assertIn(col, columns)
        
        conn.close()
    
    def test_is_meeting_processed_new_meeting(self):
        """Test checking if new meeting is processed"""
        result = database_functions.is_meeting_processed('New Meeting', '2026-03-05')
        self.assertFalse(result)
    
    def test_save_and_check_processed_meeting(self):
        """Test saving a meeting and checking if it's processed"""
        meeting_name = 'Test Meeting'
        meeting_folder_id = 'folder123'
        content_data = {
            'total_chars': 500,
            'has_transcript': True,
            'has_summary': False
        }
        content_type = 'transcript'
        salesforce_info = {
            'event_record': {'Id': 'event123'}
        }
        
        # Save the meeting
        database_functions.save_processed_meeting(
            meeting_name, meeting_folder_id, content_data, content_type,
            salesforce_info, True, True
        )
        
        # Check if it's now processed
        result = database_functions.is_meeting_processed(meeting_name, database_functions.get_today_date())
        self.assertTrue(result)
        
        # Verify data in database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM processed_calls WHERE event_name = ?', (meeting_name,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        # Check some specific fields
        self.assertEqual(row[3], meeting_name)  # event_name
        self.assertEqual(row[4], 500)  # content_chars
        self.assertEqual(row[5], 'transcript')  # content_type
        self.assertEqual(row[6], 1)  # has_transcript (True)
        self.assertEqual(row[7], 0)  # has_summary (False)
        self.assertEqual(row[8], 'event123')  # salesforce_event_id
        
        conn.close()
    
    def test_save_processed_meeting_no_salesforce(self):
        """Test saving meeting without Salesforce info"""
        database_functions.save_processed_meeting(
            'No SF Meeting', 'folder456', {}, 'gemini_summary', None, True, False
        )
        
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT salesforce_event_id FROM processed_calls WHERE event_name = ?', ('No SF Meeting',))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertIsNone(row[0])  # salesforce_event_id should be None
        
        conn.close()
    
    def test_get_processing_stats_empty(self):
        """Test getting stats with empty database"""
        stats = database_functions.get_processing_stats()
        
        expected_keys = ['total', 'posted', 'transcript_count', 'summary_count', 'salesforce_matches', 'success_rate']
        for key in expected_keys:
            self.assertIn(key, stats)
        
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['success_rate'], 0)
    
    def test_get_processing_stats_with_data(self):
        """Test getting stats with sample data"""
        # Add some test data
        test_meetings = [
            ('Meeting 1', 'folder1', {'total_chars': 100, 'has_transcript': True, 'has_summary': False}, 
             'transcript', {'event_record': {'Id': 'event1'}}, True, True),
            ('Meeting 2', 'folder2', {'total_chars': 200, 'has_transcript': False, 'has_summary': True}, 
             'gemini_summary', None, True, False),
            ('Meeting 3', 'folder3', {'total_chars': 150, 'has_transcript': True, 'has_summary': True}, 
             'transcript', {'event_record': {'Id': 'event3'}}, False, False)
        ]
        
        for meeting_data in test_meetings:
            database_functions.save_processed_meeting(*meeting_data)
        
        stats = database_functions.get_processing_stats()
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['posted'], 2)
        self.assertEqual(stats['transcript_count'], 2)
        self.assertEqual(stats['summary_count'], 2)
        self.assertEqual(stats['salesforce_matches'], 2)
        self.assertAlmostEqual(stats['success_rate'], 66.7, places=1)
    
    def test_cleanup_old_records(self):
        """Test cleanup of old records"""
        # Add a test record
        database_functions.save_processed_meeting(
            'Old Meeting', 'folder999', {}, 'summary', None, True, True
        )
        
        # Manually update the timestamp to be old
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE processed_calls SET processed_at = datetime('now', '-35 days') WHERE event_name = 'Old Meeting'"
        )
        conn.commit()
        
        # Add a recent record
        database_functions.save_processed_meeting(
            'Recent Meeting', 'folder888', {}, 'summary', None, True, True
        )
        
        # Cleanup records older than 30 days
        deleted_count = database_functions.cleanup_old_records(30)
        
        self.assertEqual(deleted_count, 1)
        
        # Verify old record is gone, recent record remains
        cursor.execute("SELECT event_name FROM processed_calls")
        remaining_meetings = [row[0] for row in cursor.fetchall()]
        
        self.assertNotIn('Old Meeting', remaining_meetings)
        self.assertIn('Recent Meeting', remaining_meetings)
        
        conn.close()
    
    def test_duplicate_prevention(self):
        """Test that duplicate meetings are prevented"""
        meeting_name = 'Duplicate Test'
        
        # Save first time
        database_functions.save_processed_meeting(
            meeting_name, 'folder1', {}, 'summary', None, True, True
        )
        
        # Try to save again (should be ignored due to UNIQUE constraint)
        database_functions.save_processed_meeting(
            meeting_name, 'folder2', {}, 'transcript', None, False, False
        )
        
        # Should only have one record
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM processed_calls WHERE event_name = ?', (meeting_name,))
        count = cursor.fetchone()[0]
        
        self.assertEqual(count, 1)
        
        conn.close()

if __name__ == '__main__':
    unittest.main()