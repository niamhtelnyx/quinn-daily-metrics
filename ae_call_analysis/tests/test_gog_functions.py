#!/usr/bin/env python3
"""
Unit tests for gog_functions.py
"""

import unittest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gog_functions import *

class TestGogFunctions(unittest.TestCase):
    
    @patch('gog_functions.subprocess.run')
    def test_run_gog_command_success(self, mock_run):
        """Test successful gog command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'Command output'
        mock_run.return_value = mock_result
        
        result = run_gog_command(['gog', '--version'])
        
        self.assertEqual(result, 'Command output')
        mock_run.assert_called_once()
    
    @patch('gog_functions.subprocess.run')
    def test_run_gog_command_failure(self, mock_run):
        """Test failed gog command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = run_gog_command(['gog', '--version'])
        
        self.assertIsNone(result)
    
    @patch('gog_functions.subprocess.run')
    def test_run_gog_command_timeout(self, mock_run):
        """Test gog command timeout"""
        mock_run.side_effect = Exception('Timeout')
        
        result = run_gog_command(['gog', '--version'])
        
        self.assertIsNone(result)
    
    @patch('gog_functions.run_gog_command')
    @patch('gog_functions.get_today_date')
    def test_get_todays_folder_id_success(self, mock_get_date, mock_run_command):
        """Test successful folder discovery"""
        mock_get_date.return_value = '2026-03-05'
        mock_run_command.return_value = 'folder123\t2026-03-05\tfolder\nfolder456\tother-folder\tfolder'
        
        result = get_todays_folder_id()
        
        self.assertEqual(result, 'folder123')
    
    @patch('gog_functions.run_gog_command')
    @patch('gog_functions.get_today_date')
    def test_get_todays_folder_id_not_found(self, mock_get_date, mock_run_command):
        """Test folder not found"""
        mock_get_date.return_value = '2026-03-05'
        mock_run_command.return_value = 'folder456\tother-folder\tfolder'
        
        result = get_todays_folder_id()
        
        self.assertIsNone(result)
    
    @patch('gog_functions.run_gog_command')
    @patch('gog_functions.get_today_date')
    def test_get_todays_folder_id_no_output(self, mock_get_date, mock_run_command):
        """Test no command output"""
        mock_get_date.return_value = '2026-03-05'
        mock_run_command.return_value = None
        
        result = get_todays_folder_id()
        
        self.assertIsNone(result)
    
    @patch('gog_functions.run_gog_command')
    def test_get_meeting_folders_success(self, mock_run_command):
        """Test successful meeting folder retrieval"""
        mock_run_command.return_value = """folder1\tMorgan & Aliyana -- Telnyx\tfolder
folder2\tTalkToMedi Meeting\tfolder
file123\tsome_file.txt\tfile"""
        
        result = get_meeting_folders('parent_folder_id')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'folder1')
        self.assertEqual(result[0]['name'], 'Morgan & Aliyana -- Telnyx')
        self.assertEqual(result[1]['id'], 'folder2')
        self.assertEqual(result[1]['name'], 'TalkToMedi Meeting')
    
    @patch('gog_functions.run_gog_command')
    def test_get_meeting_folders_empty(self, mock_run_command):
        """Test empty meeting folders"""
        mock_run_command.return_value = None
        
        result = get_meeting_folders('parent_folder_id')
        
        self.assertEqual(result, [])
    
    @patch('gog_functions.run_gog_command')
    def test_get_meeting_files_success(self, mock_run_command):
        """Test successful file listing"""
        mock_run_command.return_value = """file1\tNotes by Gemini.gdoc\tfile
file2\tChat.txt\tfile
file3\tOther document.pdf\tfile"""
        
        result = get_meeting_files('meeting_folder_id')
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'Notes by Gemini.gdoc')
        self.assertEqual(result[1]['name'], 'Chat.txt')
    
    @patch('gog_functions.os.path.exists')
    @patch('gog_functions.os.unlink')
    @patch('gog_functions.subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data='Test file content')
    @patch('gog_functions.tempfile.NamedTemporaryFile')
    def test_download_file_content_success(self, mock_temp, mock_file, mock_subprocess, mock_unlink, mock_exists):
        """Test successful file download"""
        # Mock temporary file
        mock_temp_obj = MagicMock()
        mock_temp_obj.name = '/tmp/test_file.txt'
        mock_temp.return_value.__enter__.return_value = mock_temp_obj
        
        # Mock subprocess success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Mock file exists
        mock_exists.return_value = True
        
        result = download_file_content('file123')
        
        self.assertEqual(result, 'Test file content')
        mock_subprocess.assert_called_once()
        mock_unlink.assert_called_once_with('/tmp/test_file.txt')
    
    @patch('gog_functions.os.path.exists')
    @patch('gog_functions.subprocess.run')
    @patch('gog_functions.tempfile.NamedTemporaryFile')
    def test_download_file_content_failure(self, mock_temp, mock_subprocess, mock_exists):
        """Test failed file download"""
        # Mock temporary file
        mock_temp_obj = MagicMock()
        mock_temp_obj.name = '/tmp/test_file.txt'
        mock_temp.return_value.__enter__.return_value = mock_temp_obj
        
        # Mock subprocess failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        result = download_file_content('file123')
        
        self.assertIsNone(result)
    
    @patch('gog_functions.get_meeting_files')
    def test_find_content_files_gemini_and_chat(self, mock_get_files):
        """Test finding both Gemini and chat files"""
        mock_get_files.return_value = [
            {'id': 'file1', 'name': 'Notes by Gemini.gdoc', 'type': 'file'},
            {'id': 'file2', 'name': 'Chat.txt', 'type': 'file'},
            {'id': 'file3', 'name': 'Other.pdf', 'type': 'file'}
        ]
        
        result = find_content_files('meeting_folder_id')
        
        self.assertIsNotNone(result['gemini_notes'])
        self.assertEqual(result['gemini_notes']['id'], 'file1')
        self.assertIsNotNone(result['chat_file'])
        self.assertEqual(result['chat_file']['id'], 'file2')
    
    @patch('gog_functions.get_meeting_files')
    def test_find_content_files_gemini_only(self, mock_get_files):
        """Test finding only Gemini file"""
        mock_get_files.return_value = [
            {'id': 'file1', 'name': 'Notes by Gemini.gdoc', 'type': 'file'},
            {'id': 'file3', 'name': 'Other.pdf', 'type': 'file'}
        ]
        
        result = find_content_files('meeting_folder_id')
        
        self.assertIsNotNone(result['gemini_notes'])
        self.assertIsNone(result['chat_file'])
    
    @patch('gog_functions.download_file_content')
    @patch('gog_functions.find_content_files')
    def test_extract_meeting_content_success(self, mock_find_files, mock_download):
        """Test successful content extraction"""
        mock_find_files.return_value = {
            'gemini_notes': {'id': 'file1', 'name': 'Notes by Gemini.gdoc'},
            'chat_file': None
        }
        mock_download.return_value = 'This is the meeting content with enough characters to be valid.'
        
        content, content_type = extract_meeting_content('folder_id', 'Test Meeting')
        
        self.assertIsNotNone(content)
        self.assertEqual(content_type, 'gemini_notes')
        self.assertEqual(content, 'This is the meeting content with enough characters to be valid.')
    
    @patch('gog_functions.download_file_content')
    @patch('gog_functions.find_content_files')
    def test_extract_meeting_content_fallback_to_chat(self, mock_find_files, mock_download):
        """Test fallback to chat file when Gemini fails"""
        mock_find_files.return_value = {
            'gemini_notes': {'id': 'file1', 'name': 'Notes by Gemini.gdoc'},
            'chat_file': {'id': 'file2', 'name': 'Chat.txt'}
        }
        # First call (Gemini) returns None, second call (Chat) succeeds
        mock_download.side_effect = [None, 'Chat content here with sufficient length.']
        
        content, content_type = extract_meeting_content('folder_id', 'Test Meeting')
        
        self.assertIsNotNone(content)
        self.assertEqual(content_type, 'chat_messages')
        self.assertEqual(content, 'Chat content here with sufficient length.')
    
    @patch('gog_functions.find_content_files')
    def test_extract_meeting_content_no_files(self, mock_find_files):
        """Test content extraction with no valid files"""
        mock_find_files.return_value = {
            'gemini_notes': None,
            'chat_file': None
        }
        
        content, content_type = extract_meeting_content('folder_id', 'Test Meeting')
        
        self.assertIsNone(content)
        self.assertIsNone(content_type)

if __name__ == '__main__':
    unittest.main()