#!/usr/bin/env python3
"""
Unit tests for content_parser.py
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_parser import *

class TestContentParser(unittest.TestCase):
    
    def test_parse_meeting_name_double_dash(self):
        """Test meeting name parsing with double dash"""
        prospect, company = parse_meeting_name("Morgan & Aliyana -- Telnyx")
        self.assertEqual(prospect, "Morgan & Aliyana")
        self.assertEqual(company, "Telnyx")
    
    def test_parse_meeting_name_single_dash(self):
        """Test meeting name parsing with single dash"""
        prospect, company = parse_meeting_name("Andrea Smith - TechCorp")
        self.assertEqual(prospect, "Andrea Smith")
        self.assertEqual(company, "TechCorp")
    
    def test_parse_meeting_name_no_separator(self):
        """Test meeting name parsing without separator"""
        prospect, company = parse_meeting_name("John")
        self.assertEqual(prospect, "John")
        self.assertEqual(company, "")
    
    def test_parse_meeting_name_telnyx_cleanup(self):
        """Test Telnyx cleanup in company name"""
        prospect, company = parse_meeting_name("Test -- TechCorp, Telnyx")
        self.assertEqual(prospect, "Test")
        self.assertEqual(company, "TechCorp")
    
    def test_parse_google_doc_tabs_with_transcript(self):
        """Test parsing content with clear transcript section"""
        content = """Summary:
This is a meeting summary with enough content to be considered valid and useful for analysis.

Transcript Recording
Person A: Hello, how are you doing today? I hope you're having a great day.
Person B: I'm doing well, thanks for asking. How about you? Are you ready to discuss the project?
Person A: Great to hear! Yes, I'm very excited to discuss the new integration possibilities.
Person B: Wonderful! Let's dive into the technical details and requirements.
Person A: Perfect, let's start with the API specifications and implementation timeline."""
        
        summary, transcript = parse_google_doc_tabs(content)
        self.assertIsNotNone(transcript)
        self.assertIn("Hello, how are you", transcript)
        # Summary might be None if it's too short after parsing
    
    def test_parse_google_doc_tabs_summary_only(self):
        """Test parsing content with only summary"""
        content = "This is a short meeting summary without any transcript content."
        
        summary, transcript = parse_google_doc_tabs(content)
        self.assertIsNotNone(summary)
        self.assertIsNone(transcript)
    
    def test_parse_google_doc_tabs_empty_content(self):
        """Test parsing empty content"""
        content = ""
        
        summary, transcript = parse_google_doc_tabs(content)
        self.assertIsNone(summary)
        self.assertIsNone(transcript)
    
    def test_analyze_content_structure(self):
        """Test content structure analysis"""
        content = "This is test content for analysis."
        
        result = analyze_content_structure(content)
        self.assertIsInstance(result, dict)
        self.assertIn('full_content', result)
        self.assertIn('total_chars', result)
        self.assertIn('has_transcript', result)
        self.assertIn('has_summary', result)
        self.assertEqual(result['full_content'], content)
        self.assertEqual(result['total_chars'], len(content))
    
    def test_select_best_content_transcript_priority(self):
        """Test content selection prioritizes transcript"""
        long_transcript = """This is a long transcript with lots of detail about the meeting discussion and various topics covered during the call. 
        The conversation included multiple participants discussing technical requirements, implementation timelines, and business objectives.
        There were detailed discussions about API integration, security considerations, and scalability requirements for the project."""
        
        content_data = {
            'transcript': long_transcript,
            'summary': 'Short summary with basic information about the meeting that happened.',
            'full_content': 'Full content here',
            'has_transcript': True,
            'has_summary': True
        }
        
        selected, content_type = select_best_content(content_data)
        self.assertEqual(selected, long_transcript)
        self.assertEqual(content_type, 'transcript')
    
    def test_select_best_content_fallback_to_summary(self):
        """Test content selection falls back to summary"""
        content_data = {
            'transcript': None,
            'summary': 'This is a good summary with enough content to be useful and contains meaningful information about the meeting that was discussed during the call with various stakeholders',
            'full_content': 'Full content here',
            'has_transcript': False,
            'has_summary': True
        }
        
        selected, content_type = select_best_content(content_data)
        self.assertEqual(selected, 'This is a good summary with enough content to be useful and contains meaningful information about the meeting that was discussed during the call with various stakeholders')
        self.assertEqual(content_type, 'gemini_summary')
    
    def test_extract_insights_from_content_pain_points(self):
        """Test pain point extraction"""
        content = """We're having integration issues with our current API. 
        The main challenge is the documentation complexity. 
        There's a problem with webhook reliability."""
        
        insights = extract_insights_from_content(content)
        self.assertIn('pain_points', insights)
        self.assertGreater(len(insights['pain_points']), 0)
        # Should find at least one pain point
        pain_text = ' '.join(insights['pain_points'])
        self.assertTrue(any(word in pain_text.lower() for word in ['integration', 'challenge', 'problem']))
    
    def test_extract_insights_from_content_products(self):
        """Test product extraction"""
        content = "We discussed Voice API implementation and SMS messaging capabilities."
        
        insights = extract_insights_from_content(content)
        self.assertIn('products', insights)
        # Should detect Voice and SMS products
        self.assertTrue(any('Voice' in product for product in insights['products']))
    
    def test_extract_insights_from_content_emails(self):
        """Test email extraction"""
        content = "Meeting with john@example.com and sarah.smith@techcorp.com about the project."
        
        insights = extract_insights_from_content(content)
        self.assertIn('attendees', insights)
        self.assertIn('john@example.com', insights['attendees'])
        self.assertIn('sarah.smith@techcorp.com', insights['attendees'])
    
    def test_extract_insights_from_content_next_steps(self):
        """Test next steps extraction"""
        content = "We will send the documentation tomorrow. The team plans to review the proposal."
        
        insights = extract_insights_from_content(content)
        self.assertIn('next_steps', insights)
        # Should find action-oriented sentences
        self.assertGreater(len(insights['next_steps']), 0)

if __name__ == '__main__':
    unittest.main()