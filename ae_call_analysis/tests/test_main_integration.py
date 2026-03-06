#!/usr/bin/env python3
"""
Integration tests for main.py orchestrator
"""

import unittest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import *

class TestMainIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Mock database for tests
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Patch database name
        self.db_patcher = patch('database_functions.DATABASE_NAME', self.temp_db.name)
        self.db_patcher.start()
        
        # Initialize test database
        from database_functions import init_database
        init_database()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_patcher.stop()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @patch('main.extract_insights_from_content')
    @patch('main.select_best_content')
    @patch('main.analyze_content_structure')
    @patch('main.extract_meeting_content')
    @patch('main.is_meeting_processed')
    def test_process_single_meeting_success(self, mock_is_processed, mock_extract_content, 
                                          mock_analyze, mock_select, mock_insights):
        """Test successful single meeting processing"""
        
        # Mock that meeting is not processed
        mock_is_processed.return_value = False
        
        # Mock content extraction
        mock_extract_content.return_value = ('Test meeting content', 'gemini_notes')
        
        # Mock content analysis
        mock_analyze.return_value = {
            'full_content': 'Test meeting content',
            'summary': 'Test summary',
            'transcript': 'Test transcript',
            'total_chars': 100,
            'has_transcript': True,
            'has_summary': True
        }
        
        mock_select.return_value = ('Test transcript', 'transcript')
        
        # Mock insights extraction
        mock_insights.return_value = {
            'pain_points': ['Integration challenges'],
            'products': ['Voice API'],
            'next_steps': ['Follow up'],
            'attendees': ['test@example.com']
        }
        
        # Mock Slack posting
        with patch('main.create_and_post_slack_message') as mock_slack:
            mock_slack.return_value = (True, True)
            
            # Mock Salesforce lookup
            with patch('main.lookup_salesforce_info') as mock_sf:
                mock_sf.return_value = (None, "❌ No Salesforce Match")
                
                # Test the function
                meeting_info = {'name': 'Test Meeting', 'id': 'folder123'}
                result = process_single_meeting(meeting_info)
                
                self.assertTrue(result)
                mock_extract_content.assert_called_once()
                mock_slack.assert_called_once()
    
    @patch('main.extract_meeting_content')
    @patch('main.is_meeting_processed')
    def test_process_single_meeting_already_processed(self, mock_is_processed, mock_extract):
        """Test skipping already processed meeting"""
        
        mock_is_processed.return_value = True
        
        meeting_info = {'name': 'Processed Meeting', 'id': 'folder456'}
        result = process_single_meeting(meeting_info)
        
        self.assertFalse(result)
        mock_extract.assert_not_called()
    
    @patch('main.extract_meeting_content')
    @patch('main.is_meeting_processed')
    def test_process_single_meeting_no_content(self, mock_is_processed, mock_extract):
        """Test handling meeting with no content"""
        
        mock_is_processed.return_value = False
        mock_extract.return_value = (None, None)
        
        meeting_info = {'name': 'Empty Meeting', 'id': 'folder789'}
        result = process_single_meeting(meeting_info)
        
        self.assertFalse(result)
    
    @patch('main.get_processing_stats')
    @patch('main.process_single_meeting')
    @patch('main.get_meeting_folders')
    @patch('main.get_todays_folder_id')
    @patch('main.init_database')
    @patch('main.load_dotenv')
    def test_process_todays_meetings_success(self, mock_load_env, mock_init_db, 
                                           mock_get_folder, mock_get_meetings, 
                                           mock_process_meeting, mock_stats):
        """Test complete meeting processing workflow"""
        
        # Mock today's folder
        mock_get_folder.return_value = 'today_folder_123'
        
        # Mock meeting folders
        mock_get_meetings.return_value = [
            {'name': 'Meeting 1', 'id': 'folder1'},
            {'name': 'Meeting 2', 'id': 'folder2'}
        ]
        
        # Mock meeting processing (1 success, 1 failure)
        mock_process_meeting.side_effect = [True, False]
        
        # Mock final stats
        mock_stats.return_value = {
            'total': 2,
            'posted': 1,
            'transcript_count': 1,
            'summary_count': 1,
            'salesforce_matches': 0,
            'success_rate': 50.0
        }
        
        result = process_todays_meetings()
        
        self.assertEqual(result['processed'], 2)
        self.assertEqual(result['posted'], 1)
        self.assertEqual(result['success_rate'], 50.0)
    
    @patch('main.get_todays_folder_id')
    @patch('main.init_database')
    @patch('main.load_dotenv')
    def test_process_todays_meetings_no_folder(self, mock_load_env, mock_init_db, mock_get_folder):
        """Test handling when today's folder is not found"""
        
        mock_get_folder.return_value = None
        
        result = process_todays_meetings()
        
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['posted'], 0)
        self.assertIn('error', result)
    
    @patch('main.get_meeting_folders')
    @patch('main.get_todays_folder_id')
    @patch('main.init_database')
    @patch('main.load_dotenv')
    def test_process_todays_meetings_no_meetings(self, mock_load_env, mock_init_db, 
                                               mock_get_folder, mock_get_meetings):
        """Test handling when no meetings found"""
        
        mock_get_folder.return_value = 'today_folder_123'
        mock_get_meetings.return_value = []
        
        result = process_todays_meetings()
        
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['posted'], 0)
    
    @patch('main.init_database')
    @patch('main.os.getenv')
    @patch('gog_functions.run_gog_command')
    @patch('sf_functions.get_salesforce_token')
    def test_run_health_check_all_healthy(self, mock_sf_token, mock_gog, mock_getenv, mock_init):
        """Test health check with all systems healthy"""
        
        # Mock gog working
        mock_gog.return_value = 'gog version 1.0.0'
        
        # Mock Salesforce working
        mock_sf_token.return_value = {'access_token': 'test_token'}
        
        # Mock Slack token present
        mock_getenv.return_value = 'test_slack_token'
        
        result = run_health_check()
        
        self.assertTrue(result)
    
    @patch('main.init_database')
    @patch('main.os.getenv')
    @patch('gog_functions.run_gog_command')
    @patch('sf_functions.get_salesforce_token')
    def test_run_health_check_some_issues(self, mock_sf_token, mock_gog, mock_getenv, mock_init):
        """Test health check with some systems having issues"""
        
        # Mock gog not working
        mock_gog.return_value = None
        
        # Mock Salesforce failing
        mock_sf_token.return_value = None
        
        # Mock Slack token present
        mock_getenv.return_value = 'test_slack_token'
        
        result = run_health_check()
        
        self.assertFalse(result)
    
    @patch('main.process_todays_meetings')
    @patch('main.run_health_check')
    def test_main_function_success(self, mock_health, mock_process):
        """Test main function successful execution"""
        
        mock_health.return_value = True
        mock_process.return_value = {'processed': 5, 'posted': 4, 'success_rate': 80.0}
        
        result = main()
        
        self.assertEqual(result['processed'], 5)
        self.assertEqual(result['posted'], 4)
    
    @patch('main.process_todays_meetings')
    @patch('main.run_health_check')
    def test_main_function_with_health_issues(self, mock_health, mock_process):
        """Test main function with health issues but continues"""
        
        mock_health.return_value = False  # Health issues
        mock_process.return_value = {'processed': 3, 'posted': 2, 'success_rate': 66.7}
        
        result = main()
        
        # Should continue despite health issues
        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['posted'], 2)
    
    @patch('main.run_health_check')
    def test_main_function_exception_handling(self, mock_health):
        """Test main function exception handling"""
        
        mock_health.side_effect = Exception("Test error")
        
        result = main()
        
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['posted'], 0)
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()