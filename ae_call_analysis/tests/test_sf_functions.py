#!/usr/bin/env python3
"""
Unit tests for sf_functions.py
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sf_functions import *

class TestSalesforceFunctions(unittest.TestCase):
    
    def test_normalize_meeting_name_special_characters(self):
        """Test normalization removes special characters"""
        test_cases = [
            ("AiPRL <> Telnyx Contract/Commericals", "AIPRLTELNYXCONTRACTCOMMERICALS"),
            ("Telnyx <> lazyjobber.com", "TELNYXLAZYJOBBERCOM"),
            ("Morgan & Aliyana -- Telnyx", "MORGANALIYANATELNYX"),
            ("TalkToMedi / Telnyx Integration", "TALKTOMEDITELNYXINTEGRATION"),
            ("911Locate.ai - Telnyx Partnership", "911LOCATEAITELNYXPARTNERSHIP")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = normalize_meeting_name(input_name)
                self.assertEqual(result, expected)
    
    def test_normalize_meeting_name_empty(self):
        """Test normalization handles empty input"""
        result = normalize_meeting_name("")
        self.assertEqual(result, "")
        
        result = normalize_meeting_name(None)
        self.assertEqual(result, "")
    
    def test_normalize_meeting_name_case_conversion(self):
        """Test normalization converts to uppercase"""
        result = normalize_meeting_name("lowercase meeting name")
        self.assertEqual(result, "LOWERCASEMEETINGNAME")
    
    def test_normalize_meeting_name_numbers_preserved(self):
        """Test normalization preserves numbers"""
        result = normalize_meeting_name("Meeting 123 with 456")
        self.assertEqual(result, "MEETING123WITH456")
    
    @patch('sf_functions.requests.post')
    @patch('sf_functions.os.getenv')
    def test_get_salesforce_token_success(self, mock_getenv, mock_post):
        """Test successful Salesforce token retrieval"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key: {
            'SALESFORCE_CLIENT_ID': 'test_client_id',
            'SALESFORCE_CLIENT_SECRET': 'test_client_secret'
        }.get(key)
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'instance_url': 'https://test.my.salesforce.com'
        }
        mock_post.return_value = mock_response
        
        result = get_salesforce_token()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['access_token'], 'test_token')
        self.assertEqual(result['instance_url'], 'https://test.my.salesforce.com')
        
        # Verify correct API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://telnyx.my.salesforce.com/services/oauth2/token')
        self.assertEqual(kwargs['data']['grant_type'], 'client_credentials')
    
    @patch('sf_functions.os.getenv')
    def test_get_salesforce_token_missing_credentials(self, mock_getenv):
        """Test Salesforce token with missing credentials"""
        mock_getenv.return_value = None
        
        result = get_salesforce_token()
        self.assertIsNone(result)
    
    @patch('sf_functions.requests.post')
    @patch('sf_functions.os.getenv')
    def test_get_salesforce_token_auth_failure(self, mock_getenv, mock_post):
        """Test Salesforce token with auth failure"""
        mock_getenv.side_effect = lambda key: {
            'SALESFORCE_CLIENT_ID': 'test_client_id',
            'SALESFORCE_CLIENT_SECRET': 'test_client_secret'
        }.get(key)
        
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        result = get_salesforce_token()
        self.assertIsNone(result)
    
    @patch('sf_functions.requests.get')
    def test_find_salesforce_event_success(self, mock_get):
        """Test successful Salesforce event lookup"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'totalSize': 1,
            'records': [{
                'Id': 'test_event_id',
                'Subject': 'Meeting Booked: Test Meeting',
                'WhoId': 'test_contact_id',
                'WhatId': 'test_account_id'
            }]
        }
        mock_get.return_value = mock_response
        
        result = find_salesforce_event('Test Meeting', 'test_token', 'https://test.salesforce.com')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['Id'], 'test_event_id')
        self.assertEqual(result['Subject'], 'Meeting Booked: Test Meeting')
    
    @patch('sf_functions.requests.get')
    def test_find_salesforce_event_not_found(self, mock_get):
        """Test Salesforce event not found"""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'totalSize': 0, 'records': []}
        mock_get.return_value = mock_response
        
        result = find_salesforce_event('Nonexistent Meeting', 'test_token', 'https://test.salesforce.com')
        self.assertIsNone(result)
    
    def test_build_salesforce_links_complete_record(self):
        """Test building Salesforce links with complete event record"""
        event_record = {
            'Id': 'event123',
            'WhoId': 'contact456',
            'WhatId': 'account789'
        }
        
        result = build_salesforce_links(event_record)
        
        self.assertIn('Contact', result)
        self.assertIn('Account', result)
        self.assertIn('Event', result)
        self.assertIn('contact456', result)
        self.assertIn('account789', result)
        self.assertIn('event123', result)
    
    def test_build_salesforce_links_partial_record(self):
        """Test building Salesforce links with partial event record"""
        event_record = {
            'Id': 'event123',
            'WhoId': 'contact456'
            # Missing WhatId (account)
        }
        
        result = build_salesforce_links(event_record)
        
        self.assertIn('Contact', result)
        self.assertIn('Event', result)
        self.assertNotIn('Account', result)
    
    def test_build_salesforce_links_no_record(self):
        """Test building Salesforce links with no record"""
        result = build_salesforce_links(None)
        self.assertEqual(result, "❌ No Salesforce Match")
        
        result = build_salesforce_links({})
        self.assertEqual(result, "❌ No Salesforce Match")
    
    @patch('sf_functions.get_contact_from_salesforce')
    @patch('sf_functions.find_salesforce_event')
    @patch('sf_functions.get_salesforce_token')
    def test_lookup_salesforce_info_complete_flow(self, mock_get_token, mock_find_event, mock_get_contact):
        """Test complete Salesforce lookup workflow"""
        # Mock token
        mock_get_token.return_value = {
            'access_token': 'test_token',
            'instance_url': 'https://test.salesforce.com'
        }
        
        # Mock event
        mock_event = {
            'Id': 'event123',
            'Subject': 'Meeting Booked: Test Meeting',
            'WhoId': 'contact456'
        }
        mock_find_event.return_value = mock_event
        
        # Mock contact
        mock_contact = {
            'Id': 'contact456',
            'Name': 'John Doe',
            'Email': 'john@example.com'
        }
        mock_get_contact.return_value = mock_contact
        
        result, links = lookup_salesforce_info('Test Meeting')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['event_record'], mock_event)
        self.assertEqual(result['contact_info'], mock_contact)
        self.assertIn('Contact', links)
    
    @patch('sf_functions.get_salesforce_token')
    def test_lookup_salesforce_info_no_token(self, mock_get_token):
        """Test Salesforce lookup with no token"""
        mock_get_token.return_value = None
        
        result, links = lookup_salesforce_info('Test Meeting')
        
        self.assertIsNone(result)
        self.assertEqual(links, "❌ No Salesforce Match")

if __name__ == '__main__':
    unittest.main()