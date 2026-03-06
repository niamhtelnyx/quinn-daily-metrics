#!/usr/bin/env python3
"""
Unit tests for config.py
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *

class TestConfig(unittest.TestCase):
    
    def test_get_today_date(self):
        """Test date formatting function"""
        today = get_today_date()
        self.assertRegex(today, r'\d{4}-\d{2}-\d{2}')  # YYYY-MM-DD format
        self.assertEqual(len(today), 10)
    
    def test_get_timestamp(self):
        """Test timestamp function"""
        timestamp = get_timestamp()
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    
    def test_content_type_indicators(self):
        """Test content type mapping"""
        self.assertIn('transcript', CONTENT_TYPE_INDICATORS)
        self.assertIn('gemini_summary', CONTENT_TYPE_INDICATORS)
        self.assertIn('chat_messages', CONTENT_TYPE_INDICATORS)
        self.assertIn('full_content', CONTENT_TYPE_INDICATORS)
    
    def test_transcript_patterns(self):
        """Test transcript detection patterns"""
        self.assertIsInstance(TRANSCRIPT_PATTERNS, list)
        self.assertGreater(len(TRANSCRIPT_PATTERNS), 0)
        # Test pattern compilation
        for pattern in TRANSCRIPT_PATTERNS:
            self.assertIsInstance(pattern, str)
    
    def test_configuration_constants(self):
        """Test configuration constants are properly set"""
        self.assertIsInstance(GOG_TIMEOUT, int)
        self.assertIsInstance(SALESFORCE_TIMEOUT, int)
        self.assertIsInstance(MIN_SUMMARY_LENGTH, int)
        self.assertIsInstance(MIN_TRANSCRIPT_LENGTH, int)
        self.assertEqual(SLACK_CHANNEL, "#sales-calls")

if __name__ == '__main__':
    unittest.main()