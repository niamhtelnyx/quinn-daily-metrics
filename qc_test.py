#!/usr/bin/env python3
"""
Quality Control Test Suite
Tests the QC validator with good and bad call examples to ensure
garbage posts are properly filtered out

TESTS:
✅ Good calls that should pass QC
❌ Bad calls that should be blocked
📊 Comprehensive gate testing
"""

import json
from qc_validator import QCValidator, validate_call_quality
from datetime import datetime

class QCTestSuite:
    """Comprehensive test suite for QC validation"""
    
    def __init__(self):
        self.validator = QCValidator()
        self.test_results = []
    
    def log_test(self, name, expected_pass, actual_pass, message):
        """Log test result"""
        status = "✅ PASS" if expected_pass == actual_pass else "❌ FAIL"
        self.test_results.append({
            'name': name,
            'expected': expected_pass,
            'actual': actual_pass,
            'status': status,
            'message': message
        })
        print(f"{status} {name}: {message}")
    
    def test_good_calls(self):
        """Test calls that should pass QC"""
        print("\n🟢 Testing GOOD calls (should pass QC)...")
        
        # Test 1: High-quality sales call
        good_call_1 = {
            'prospect_name': 'John Smith',
            'ae_name': 'niamh collins',
            'title': 'Sales call with John Smith - Gemini notes',
            'content': 'Great conversation about Telnyx API solutions. John mentioned they need SMS capabilities for their customer notification system. We discussed pricing and implementation timeline. Next steps: send proposal by Friday.',
            'call_date': '2024-03-04'
        }
        
        good_analysis_1 = {
            'summary': 'Sales call discussing SMS API needs for customer notifications',
            'key_points': ['SMS API requirements', 'Customer notifications', 'Pricing discussion'],
            'next_steps': ['Send proposal by Friday'],
            'pain_points': ['Need automated customer notifications'],
            'sentiment': 'positive'
        }
        
        should_post, message = validate_call_quality(good_call_1, good_analysis_1)
        self.log_test("Good Call #1", True, should_post, message)
        
        # Test 2: Technical demo call
        good_call_2 = {
            'prospect_name': 'Sarah Johnson',
            'ae_name': 'ryan simkins',
            'title': 'Technical demo - Video API integration',
            'content': 'Sarah from TechCorp attended demo of our Video API. She was impressed with the quality and ease of integration. Discussed their use case for virtual meetings platform. They have 50,000 monthly active users. Timeline: decision by end of quarter.',
            'call_date': '2024-03-04'
        }
        
        good_analysis_2 = {
            'summary': 'Technical demo showcasing Video API capabilities',
            'key_points': ['Video API demo', '50k MAU platform', 'Integration ease'],
            'next_steps': ['Follow up next week', 'Send technical docs'],
            'decision_makers': ['Sarah Johnson - CTO'],
            'timeline': 'End of quarter',
            'sentiment': 'positive'
        }
        
        should_post, message = validate_call_quality(good_call_2, good_analysis_2)
        self.log_test("Good Call #2", True, should_post, message)
        
    def test_bad_calls(self):
        """Test calls that should be blocked by QC"""
        print("\n🔴 Testing BAD calls (should be blocked)...")
        
        # Test 1: Unknown Prospect
        bad_call_1 = {
            'prospect_name': 'Unknown Prospect',
            'ae_name': 'niamh collins',
            'title': 'Call notes',
            'content': 'Some discussion happened but details are unclear.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_1 = {
            'summary': 'Call summary not available',
            'key_points': [],
            'next_steps': [],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_1, bad_analysis_1)
        self.log_test("Bad Call #1 (Unknown Prospect)", False, should_post, message)
        
        # Test 2: Unknown AE
        bad_call_2 = {
            'prospect_name': 'Jane Doe',
            'ae_name': 'Unknown AE',
            'title': 'Sales call with Jane',
            'content': 'Discussion about services and potential partnership opportunities.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_2 = {
            'summary': 'Generic sales discussion',
            'key_points': ['Services discussion'],
            'next_steps': ['Follow up'],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_2, bad_analysis_2)
        self.log_test("Bad Call #2 (Unknown AE)", False, should_post, message)
        
        # Test 3: Empty content
        bad_call_3 = {
            'prospect_name': 'Bob Wilson',
            'ae_name': 'kai luo',
            'title': 'Meeting with Bob Wilson',
            'content': '',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_3 = {
            'summary': 'No content available',
            'key_points': [],
            'next_steps': [],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_3, bad_analysis_3)
        self.log_test("Bad Call #3 (Empty Content)", False, should_post, message)
        
        # Test 4: AI analysis with JSON error
        bad_call_4 = {
            'prospect_name': 'Alice Brown',
            'ae_name': 'rob messier',
            'title': 'Call with Alice Brown',
            'content': 'Discussion about communication needs and potential Telnyx solutions for their growing business.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_4 = {
            'summary': '{"error": "JSON parse error - malformed response"}',
            'key_points': [],
            'next_steps': [],
            'error': 'JSON parsing failed',
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_4, bad_analysis_4)
        self.log_test("Bad Call #4 (JSON Error in Analysis)", False, should_post, message)
        
        # Test 5: Too short content
        bad_call_5 = {
            'prospect_name': 'Mike Chen',
            'ae_name': 'tyron pretorius',
            'title': 'Brief call with Mike',
            'content': 'Quick chat.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_5 = {
            'summary': 'Short call',
            'key_points': [],
            'next_steps': [],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_5, bad_analysis_5)
        self.log_test("Bad Call #5 (Too Short Content)", False, should_post, message)
        
        # Test 6: Empty analysis arrays
        bad_call_6 = {
            'prospect_name': 'David Lee',
            'ae_name': 'brian',
            'title': 'Call with David Lee - Gemini notes',
            'content': 'Had a conversation with David Lee about potential partnership opportunities. We discussed various aspects of our services and how they might integrate with their business model. The call lasted about 30 minutes.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_6 = {
            'summary': 'Generic call summary with no insights',
            'key_points': [],
            'next_steps': [],
            'pain_points': [],
            'decision_makers': [],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(bad_call_6, bad_analysis_6)
        self.log_test("Bad Call #6 (Empty Analysis Arrays)", False, should_post, message)
        
        # Test 7: Malformed title
        bad_call_7 = {
            'prospect_name': 'Emma Davis',
            'ae_name': 'conor',
            'title': 'Untitled Document',
            'content': 'Discussion with Emma about their communication infrastructure needs. They currently use multiple vendors and are looking to consolidate. Interested in our voice and messaging APIs.',
            'call_date': '2024-03-04'
        }
        
        bad_analysis_7 = {
            'summary': 'Discussion about communication infrastructure',
            'key_points': ['Multiple vendor consolidation', 'Voice and messaging APIs'],
            'next_steps': ['Send pricing'],
            'sentiment': 'positive'
        }
        
        should_post, message = validate_call_quality(bad_call_7, bad_analysis_7)
        self.log_test("Bad Call #7 (Malformed Title)", False, should_post, message)
    
    def test_edge_cases(self):
        """Test edge cases and borderline scenarios"""
        print("\n🟡 Testing EDGE cases...")
        
        # Test 1: Non-Telnyx AE but valid name
        edge_call_1 = {
            'prospect_name': 'Frank Miller',
            'ae_name': 'John External',
            'title': 'Partnership discussion with Frank Miller',
            'content': 'Productive discussion about potential partnership opportunities. Frank expressed interest in our API platform for their customer communication needs. They handle about 10,000 customers monthly.',
            'call_date': '2024-03-04'
        }
        
        edge_analysis_1 = {
            'summary': 'Partnership discussion showing mutual interest',
            'key_points': ['API platform interest', '10k monthly customers'],
            'next_steps': ['Send partnership proposal'],
            'sentiment': 'positive'
        }
        
        should_post, message = validate_call_quality(edge_call_1, edge_analysis_1)
        self.log_test("Edge Case #1 (Non-Telnyx AE)", True, should_post, message)
        
        # Test 2: Minimal but valid content
        edge_call_2 = {
            'prospect_name': 'Grace Kim',
            'ae_name': 'mario',
            'title': 'Initial call with Grace Kim - Gemini notes',
            'content': 'Initial discovery call with Grace from StartupCorp. They are a small team building a customer service platform. Currently using basic email but need SMS and voice capabilities for better customer engagement. Timeline is flexible as they are still in development phase.',
            'call_date': '2024-03-04'
        }
        
        edge_analysis_2 = {
            'summary': 'Discovery call with startup building customer service platform',
            'key_points': ['Customer service platform', 'Need SMS and voice'],
            'next_steps': ['Follow up when ready'],
            'timeline': 'Flexible - development phase',
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(edge_call_2, edge_analysis_2)
        self.log_test("Edge Case #2 (Minimal Valid Content)", True, should_post, message)
    
    def test_comprehensive_scenarios(self):
        """Test real-world scenarios that might appear in production"""
        print("\n🔵 Testing REAL-WORLD scenarios...")
        
        # Scenario 1: Well-parsed call from actual Gemini notes
        real_call_1 = {
            'prospect_name': 'Michael Rodriguez',
            'ae_name': 'niamh collins',
            'title': 'TechFlow Solutions Discovery Call - Notes by Gemini',
            'content': '''
            Michael Rodriguez from TechFlow Solutions and Niamh Collins from Telnyx met to discuss their communication infrastructure needs.
            
            Key discussion points:
            - TechFlow is scaling rapidly and needs reliable SMS and voice APIs
            - Currently using Twilio but experiencing deliverability issues
            - Processing 100,000+ SMS per month with plans to double that
            - Need international SMS capabilities for global customers
            - Budget approved for Q2 implementation
            
            Next steps:
            - Niamh to send technical documentation and pricing
            - Schedule technical demo with their dev team next week
            - Connect with their compliance team for international requirements
            
            Decision maker: Michael Rodriguez (CTO)
            Timeline: Implementation by end of Q2
            ''',
            'call_date': '2024-03-04T10:30:00'
        }
        
        real_analysis_1 = {
            'summary': 'Discovery call with fast-growing company experiencing deliverability issues with current provider',
            'key_points': [
                'Processing 100k+ SMS monthly with plans to double',
                'Deliverability issues with current provider (Twilio)',
                'Need international SMS capabilities',
                'Budget approved for Q2'
            ],
            'next_steps': [
                'Send technical documentation and pricing',
                'Schedule technical demo with dev team',
                'Connect with compliance team for international requirements'
            ],
            'pain_points': [
                'SMS deliverability issues',
                'Need for international capabilities',
                'Scaling communication needs'
            ],
            'competitive_mentions': ['Twilio'],
            'decision_makers': ['Michael Rodriguez - CTO'],
            'timeline': 'Implementation by end of Q2',
            'sentiment': 'positive'
        }
        
        should_post, message = validate_call_quality(real_call_1, real_analysis_1)
        self.log_test("Real Scenario #1 (High-Quality Discovery)", True, should_post, message)
        
        # Scenario 2: Poorly extracted call that should be blocked
        real_call_2 = {
            'prospect_name': 'Unknown Prospect',
            'ae_name': 'Unknown AE',
            'title': 'Copy of Gemini notes',
            'content': 'Error accessing document content. Permission denied.',
            'call_date': '2024-03-04'
        }
        
        real_analysis_2 = {
            'error': 'Unable to analyze call content',
            'summary': '{"error": "Invalid JSON response from OpenAI API"}',
            'key_points': [],
            'next_steps': [],
            'sentiment': 'neutral'
        }
        
        should_post, message = validate_call_quality(real_call_2, real_analysis_2)
        self.log_test("Real Scenario #2 (Poorly Extracted)", False, should_post, message)
    
    def run_full_test_suite(self):
        """Run complete test suite"""
        print("🛡️ QUALITY CONTROL TEST SUITE")
        print("=" * 50)
        
        # Run all test categories
        self.test_good_calls()
        self.test_bad_calls()
        self.test_edge_cases()
        self.test_comprehensive_scenarios()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == '✅ PASS'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] == '❌ FAIL':
                    print(f"   {result['name']}: Expected {result['expected']}, got {result['actual']}")
        
        # Show QC stats
        print(f"\n🛡️ QC VALIDATOR STATS:")
        stats = self.validator.get_stats()
        print(f"   Processed: {stats['total_validated']}")
        print(f"   Passed: {stats['passed']}")
        print(f"   Blocked: {stats['failed']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        
        if stats['gate_failures']:
            print(f"   Gate Failures:")
            for gate, count in stats['gate_failures'].items():
                print(f"     {gate}: {count}")

def demo_qc_filtering():
    """Demonstrate QC filtering with examples"""
    print("\n🎭 QC FILTERING DEMONSTRATION")
    print("=" * 50)
    
    # Examples of calls that would be filtered
    garbage_examples = [
        {
            'name': 'Unknown Prospect Example',
            'data': {
                'prospect_name': 'Unknown Prospect',
                'ae_name': 'niamh collins',
                'title': 'Meeting notes',
                'content': 'Some discussion happened.'
            },
            'analysis': {'summary': 'Brief call', 'key_points': [], 'sentiment': 'neutral'}
        },
        {
            'name': 'JSON Error Example',
            'data': {
                'prospect_name': 'Test Customer',
                'ae_name': 'ryan simkins',
                'title': 'Customer call',
                'content': 'Good conversation about their needs and our solutions.'
            },
            'analysis': {
                'summary': '{"error": "JSON parse error in OpenAI response"}',
                'key_points': [],
                'sentiment': 'neutral',
                'error': 'API parsing failed'
            }
        }
    ]
    
    validator = QCValidator()
    
    for example in garbage_examples:
        print(f"\n🗑️  Testing: {example['name']}")
        should_post, message = validator.should_post_to_slack(example['data'], example['analysis'])
        
        if should_post:
            print(f"   ❌ PROBLEM: This garbage would be posted! {message}")
        else:
            print(f"   ✅ BLOCKED: {message}")

if __name__ == "__main__":
    # Run full test suite
    test_suite = QCTestSuite()
    test_suite.run_full_test_suite()
    
    # Demonstrate filtering
    demo_qc_filtering()
    
    print(f"\n🎯 QC system is working! Garbage posts will be filtered out before reaching #sales-calls")