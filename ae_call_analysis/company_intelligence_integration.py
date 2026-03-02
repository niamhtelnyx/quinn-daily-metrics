#!/usr/bin/env python3
"""
Complete Company Intelligence Integration
Integrates company intelligence with call analysis and message formatting
"""

import sqlite3
import json
from datetime import datetime
from company_intelligence import CompanyIntelligence
from threaded_message_format import generate_summary_and_thread

class CompanyIntelligenceIntegration:
    """Complete integration of company intelligence with call analysis system"""
    
    def __init__(self, db_path: str = "ae_call_analysis.db", org_username: str = "niamh@telnyx.com"):
        self.db_path = db_path
        self.company_intel = CompanyIntelligence(org_username, db_path)
    
    def get_call_data_by_id(self, call_id: int):
        """Get call data from database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT c.id, c.fellow_id, c.title, c.call_date, c.ae_name, c.prospect_name, c.prospect_company,
                   ar.prospect_interest_level, ar.ae_excitement_level, ar.quinn_qualification_quality,
                   ar.core_talking_points, ar.telnyx_products, ar.use_cases, ar.conversation_focus_primary,
                   ar.prospect_buying_signals, ar.prospect_concerns, ar.next_steps_category, ar.next_steps_actions,
                   ar.quinn_strengths, ar.quinn_missed_opportunities, ar.analysis_confidence,
                   sm.contact_id, sm.contact_name
            FROM calls c
            LEFT JOIN analysis_results ar ON c.id = ar.call_id
            LEFT JOIN salesforce_mappings sm ON c.id = sm.call_id
            WHERE c.id = ?
            ''', (call_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None, None, None
            
            # Build call data
            call_data = {
                'id': row[0],
                'fellow_id': row[1],
                'title': row[2],
                'call_date': row[3],
                'ae_name': row[4],
                'prospect_name': row[5],
                'prospect_company': row[6]
            }
            
            # Build analysis data
            analysis_data = {
                'prospect_interest_level': row[7] or 0,
                'ae_excitement_level': row[8] or 0,
                'quinn_qualification_quality': row[9] or 0,
                'core_talking_points': json.loads(row[10]) if row[10] else [],
                'telnyx_products': json.loads(row[11]) if row[11] else [],
                'use_cases': json.loads(row[12]) if row[12] else [],
                'conversation_focus_primary': row[13] or 'discovery',
                'prospect_buying_signals': json.loads(row[14]) if row[14] else [],
                'prospect_concerns': json.loads(row[15]) if row[15] else [],
                'next_steps_category': row[16] or 'follow_up',
                'next_steps_actions': json.loads(row[17]) if row[17] else [],
                'quinn_strengths': json.loads(row[18]) if row[18] else [],
                'quinn_missed_opportunities': json.loads(row[19]) if row[19] else [],
                'analysis_confidence': row[20] or 8
            }
            
            # Build SF event data (simplified)
            sf_event = None
            if row[21]:  # contact_id exists
                sf_event = {
                    'contact_id': row[21],
                    'contact_name': row[22],
                    'event_id': 'mock_event_id',
                    'account_name': 'Retrieved from Contact',
                    'telnyx_attendees': [call_data['ae_name'] or 'Unknown AE'],
                    'start_datetime': call_data['call_date'],
                    'contact_email': 'unknown@example.com'
                }
            
            return call_data, analysis_data, sf_event
            
        except Exception as e:
            print(f"❌ Error getting call data: {e}")
            return None, None, None
    
    def enhance_call_with_full_intelligence(self, call_id: int):
        """Complete enhancement: get call data + company intelligence + generate enhanced messages"""
        
        print(f"🚀 FULL COMPANY INTELLIGENCE ENHANCEMENT")
        print(f"Call ID: {call_id}")
        print("="*60)
        
        # Step 1: Get call data
        call_data, analysis_data, sf_event = self.get_call_data_by_id(call_id)
        
        if not call_data:
            return {
                'success': False,
                'error': f'Call {call_id} not found in database'
            }
        
        print(f"✅ Call data retrieved: {call_data['prospect_name']} | {call_data['ae_name']}")
        
        # Step 2: Check for existing company intelligence
        existing_company_intel = self.company_intel.get_company_intelligence_by_call_id(call_id)
        
        if existing_company_intel:
            print(f"✅ Company intelligence already exists: {existing_company_intel['company_name']}")
            company_intelligence = existing_company_intel
        else:
            # Step 3: Generate new company intelligence
            print("🔍 Generating new company intelligence...")
            intel_result = self.company_intel.enhance_call_from_db(call_id)
            
            if intel_result['success']:
                company_intelligence = {
                    'company_name': intel_result['company_data']['company_name'],
                    'business_insight': intel_result['business_insight'],
                    'website': intel_result['company_data']['website'],
                    'industry': intel_result['company_data']['industry'],
                    'employees': intel_result['company_data']['employees']
                }
                print(f"✅ Company intelligence generated: {company_intelligence['company_name']}")
            else:
                print(f"⚠️ Company intelligence generation failed: {intel_result['error']}")
                company_intelligence = None
        
        # Step 4: Generate enhanced messages
        messages = generate_summary_and_thread(call_data, analysis_data, sf_event, company_intelligence)
        
        print(f"✅ Enhanced messages generated")
        
        return {
            'success': True,
            'call_data': call_data,
            'analysis_data': analysis_data,
            'sf_event': sf_event,
            'company_intelligence': company_intelligence,
            'messages': messages,
            'enhanced_at': datetime.now().isoformat()
        }
    
    def demo_enhancement(self, call_id: int = None):
        """Demo the complete enhancement system"""
        
        if not call_id:
            # Find a call with salesforce mapping
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT c.id, c.prospect_name, c.ae_name, sm.contact_id, sm.contact_name
            FROM calls c
            JOIN salesforce_mappings sm ON c.id = sm.call_id
            WHERE sm.contact_id IS NOT NULL
            ORDER BY c.call_date DESC
            LIMIT 1
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                call_id = row[0]
                print(f"📋 Using call: {row[1]} | {row[2]} | Contact: {row[4]} ({row[3]})")
            else:
                print("❌ No calls with Salesforce mappings found")
                return None
        
        # Run full enhancement
        result = self.enhance_call_with_full_intelligence(call_id)
        
        if result['success']:
            print("\n" + "="*80)
            print("🎯 ENHANCED CALL INTELLIGENCE - MAIN POST")
            print("="*80)
            print(result['messages']['main_post'])
            
            print("\n" + "="*80)
            print("🧵 ENHANCED CALL INTELLIGENCE - THREAD REPLY")
            print("="*80)
            print(result['messages']['thread_reply'])
            
            # Save demo output
            demo_filename = f"enhanced_call_demo_{call_id}.json"
            with open(demo_filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"\n💾 Demo saved to: {demo_filename}")
            print("🎉 Company intelligence integration complete!")
            
            return result
        else:
            print(f"❌ Enhancement failed: {result['error']}")
            return None

def test_with_nick_mihalovich():
    """Test the system with Nick Mihalovich contact specifically"""
    
    print("🧪 TESTING WITH NICK MIHALOVICH CONTACT")
    print("="*60)
    
    # Use the CompanyIntelligence class directly for testing
    company_intel = CompanyIntelligence()
    
    # Test Nick Mihalovich contact
    test_contact_id = "003Qk00000jw4fsIAA"  # Nick Mihalovich
    
    print(f"Contact ID: {test_contact_id}")
    
    # Get company data
    result = company_intel.enhance_call_with_company_intelligence('', test_contact_id)
    
    if result['success']:
        print(f"✅ Company: {result['company_data']['company_name']}")
        print(f"✅ Insight: {result['business_insight']}")
        
        # Save test result
        with open('nick_mihalovich_test.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print("💾 Test result saved to: nick_mihalovich_test.json")
        
        return result
    else:
        print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
        return None

if __name__ == "__main__":
    # Test with Nick Mihalovich first
    test_result = test_with_nick_mihalovich()
    
    if test_result:
        print("\n" + "="*80)
        print("🎯 FULL SYSTEM DEMO")
        print("="*80)
        
        # Run full system demo
        integration = CompanyIntelligenceIntegration()
        integration.demo_enhancement()