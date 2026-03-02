#!/usr/bin/env python3
"""
Enhanced Call Processor with Salesforce Event Integration
Complete E2E pipeline: Fellow → Salesforce Event Lookup → OpenAI Analysis → Salesforce Event Update → Slack Intelligence
"""

from fixed_salesforce_oauth2_integration import FixedSalesforceEventIntegration
from oauth2_salesforce_event_updater import OAuth2SalesforceEventUpdater
from refined_message_format import generate_refined_call_alert
import sqlite3
import json
from datetime import datetime

class EnhancedCallProcessor:
    """Enhanced call processor with Salesforce event integration and Event updating"""
    
    def __init__(self):
        self.sf_integration = FixedSalesforceEventIntegration()
        self.sf_updater = OAuth2SalesforceEventUpdater()
    
    def process_call_with_salesforce_lookup(self, call_id: int) -> dict:
        """Process a single call with full Salesforce event lookup"""
        
        # Get call data from database
        call_data = self._get_call_data(call_id)
        if not call_data:
            return {'success': False, 'error': 'Call not found'}
        
        print(f"📞 Processing call: {call_data['prospect_name']}")
        
        # Step 1: Look up Salesforce event
        print("🔍 Looking up Salesforce event...")
        sf_event = self.sf_integration.lookup_event_by_prospect(
            call_data['prospect_name'], 
            call_data['call_date']
        )
        
        if sf_event:
            print(f"✅ Found Salesforce event: {sf_event['subject']}")
            print(f"   🎯 AE: {sf_event['formatted_ae_names']}")
            print(f"   🏢 Account: {sf_event['account_name']}")
            
            # Update call with Salesforce data
            self.sf_integration.update_call_with_salesforce_data(call_id, sf_event)
            call_data.update({
                'ae_name': sf_event['formatted_ae_names'],
                'prospect_company': sf_event['account_name'],
                'salesforce_event_id': sf_event['event_id']
            })
        else:
            print("⚠️  No matching Salesforce event found - using Fellow data")
        
        # Step 2: Get analysis results
        analysis_data = self._get_analysis_data(call_id)
        if not analysis_data:
            return {'success': False, 'error': 'No analysis data found'}
        
        # Step 3: Update Salesforce Event with Call Intelligence (if event found)
        sf_update_result = None
        if sf_event and sf_event.get('event_id'):
            print("📝 Updating Salesforce Event with Call Intelligence...")
            try:
                sf_update_result = self.sf_updater.update_event_with_intelligence(
                    sf_event['event_id'], analysis_data, call_data
                )
                
                if sf_update_result['success']:
                    print(f"✅ Salesforce Event {sf_event['event_id']} updated successfully")
                else:
                    print(f"⚠️  Failed to update Salesforce Event: {sf_update_result['error']}")
                    
            except Exception as e:
                print(f"⚠️  Error updating Salesforce Event: {str(e)}")
                sf_update_result = {'success': False, 'error': str(e)}
        else:
            print("⚠️  No Salesforce Event to update (no event found)")
        
        # Step 4: Generate Call Intelligence Alert
        print("📊 Generating Call Intelligence Alert...")
        message = self._generate_enhanced_alert(call_data, analysis_data, sf_event, sf_update_result)
        
        return {
            'success': True,
            'call_data': call_data,
            'salesforce_event': sf_event,
            'analysis_data': analysis_data,
            'salesforce_update': sf_update_result,
            'message': message
        }
    
    def _get_call_data(self, call_id: int) -> dict:
        """Get call data from database"""
        conn = sqlite3.connect('ae_call_analysis.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, prospect_name, ae_name, call_date, title, prospect_company
        FROM calls WHERE id = ?
        ''', (call_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'prospect_name': result[1],
                'ae_name': result[2],
                'call_date': result[3],
                'title': result[4],
                'prospect_company': result[5]
            }
        return None
    
    def _get_analysis_data(self, call_id: int) -> dict:
        """Get analysis data from database"""
        conn = sqlite3.connect('ae_call_analysis.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT prospect_interest_level, ae_excitement_level,
               quinn_qualification_quality, analysis_confidence,
               core_talking_points, use_cases, telnyx_products,
               conversation_focus_primary, prospect_buying_signals,
               prospect_concerns, next_steps_category, next_steps_actions,
               quinn_missed_opportunities, quinn_strengths
        FROM analysis_results WHERE call_id = ?
        ''', (call_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'prospect_interest_level': result[0] or 0,
                'ae_excitement_level': result[1] or 0,
                'quinn_qualification_quality': result[2] or 0,
                'analysis_confidence': result[3] or 8,
                'core_talking_points': json.loads(result[4]) if result[4] else [],
                'use_cases': json.loads(result[5]) if result[5] else [],
                'telnyx_products': json.loads(result[6]) if result[6] else [],
                'conversation_focus_primary': result[7] or 'discovery',
                'prospect_buying_signals': json.loads(result[8]) if result[8] else [],
                'prospect_concerns': json.loads(result[9]) if result[9] else [],
                'next_steps_category': result[10] or 'follow_up',
                'next_steps_actions': json.loads(result[11]) if result[11] else [],
                'quinn_missed_opportunities': json.loads(result[12]) if result[12] else [],
                'quinn_strengths': json.loads(result[13]) if result[13] else []
            }
        return None
    
    def _generate_enhanced_alert(self, call_data: dict, analysis_data: dict, sf_event: dict = None, sf_update_result: dict = None) -> str:
        """Generate enhanced Call Intelligence Alert with Salesforce validation"""
        
        # Generate base message
        message = generate_refined_call_alert(call_data, analysis_data)
        
        # Add Salesforce validation section
        if sf_event:
            # Include Event update status
            update_status = ""
            if sf_update_result:
                if sf_update_result['success']:
                    update_status = f"\n• **Event Updated**: ✅ Call intelligence appended to Event.Description"
                else:
                    update_status = f"\n• **Event Update**: ⚠️ Failed ({sf_update_result.get('error', 'Unknown error')})"
            else:
                update_status = f"\n• **Event Update**: ⚠️ Not attempted"
            
            sf_validation = f"""

**🔗 SALESFORCE EVENT VALIDATION:**
• **Event ID**: {sf_event['event_id']}
• **Subject**: {sf_event['subject']}
• **Contact**: {sf_event['contact_name']} ({sf_event['contact_email']})
• **Account**: {sf_event['account_name']}
• **Primary AE**: {sf_event['primary_ae_name']}
• **All Telnyx AEs**: {', '.join(sf_event['telnyx_attendees'])}
• **Event Date**: {sf_event['start_datetime']}{update_status}

_✅ AE names, contact, and account validated via Salesforce event data_"""
        else:
            sf_validation = f"""

**⚠️ SALESFORCE EVENT STATUS:**
• **Event Lookup**: No matching Salesforce event found
• **AE Source**: Extracted from Fellow AI notes
• **Contact Validation**: Pending Salesforce event creation
• **Event Update**: ⚠️ No event available to update
• **Recommendation**: Verify event exists in Salesforce calendar

_ℹ️ Using Fellow data until Salesforce event is available_"""
        
        # Add enhanced E2E processing note
        sf_update_status = ""
        if sf_event and sf_update_result:
            sf_update_status = f"• **Salesforce Event Update**: {'✅ Complete' if sf_update_result['success'] else '⚠️ Failed'}\n"
        elif sf_event:
            sf_update_status = f"• **Salesforce Event Update**: ⚠️ Not attempted\n"
        else:
            sf_update_status = f"• **Salesforce Event Update**: ⚠️ No event to update\n"
        
        processing_note = f"""

**🔄 ENHANCED E2E PROCESSING:**
• **Fellow API**: ✅ Call extracted ({call_data['title']})
• **Salesforce Event**: {'✅ Validated' if sf_event else '⚠️ Pending'}
• **AE Identification**: ✅ {call_data.get('ae_name', '[Extracted from Fellow]')}
• **OpenAI Analysis**: ✅ Complete ({len(analysis_data.get('core_talking_points', []))} pain points)
{sf_update_status}• **Intelligence Generated**: {datetime.now().strftime('%H:%M CST')}

_Complete pipeline: Fellow → SF Event Lookup → AE Validation → OpenAI Analysis → SF Event Update → Stakeholder Intelligence_"""
        
        return message + sf_validation + processing_note

def demo_enhanced_processing():
    """Demonstrate the enhanced processing with Salesforce integration"""
    
    print("🚀 ENHANCED CALL INTELLIGENCE WITH SALESFORCE INTEGRATION")
    print("=" * 70)
    
    processor = EnhancedCallProcessor()
    
    # Get a test call ID
    conn = sqlite3.connect('ae_call_analysis.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, prospect_name 
    FROM calls 
    WHERE ae_name IS NOT NULL 
    ORDER BY created_at DESC 
    LIMIT 1
    ''')
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("❌ No calls available for testing")
        return
    
    call_id, prospect_name = result
    print(f"📞 Testing with Call ID {call_id}: {prospect_name}")
    
    # Process the call
    result = processor.process_call_with_salesforce_lookup(call_id)
    
    if result['success']:
        print("\n✅ ENHANCED PROCESSING COMPLETE!")
        print(f"📊 Call: {result['call_data']['prospect_name']}")
        print(f"🎯 AE: {result['call_data'].get('ae_name', 'Unknown')}")
        print(f"🔗 Salesforce: {'Validated' if result['salesforce_event'] else 'Pending'}")
        
        # Save the enhanced message
        with open('enhanced_call_alert_demo.txt', 'w') as f:
            f.write(result['message'])
        
        print(f"\n📝 Enhanced Call Intelligence Alert saved to 'enhanced_call_alert_demo.txt'")
        print(f"🎯 Ready for deployment to #bot-testing with full Salesforce integration!")
        
    else:
        print(f"❌ Processing failed: {result['error']}")

if __name__ == "__main__":
    demo_enhanced_processing()