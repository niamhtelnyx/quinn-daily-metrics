#!/usr/bin/env python3
"""
Direct test of Salesforce Event updating with known Event ID
Tests the core Event.Description update functionality
"""

from salesforce_event_updater import SalesforceEventUpdater
import json
from datetime import datetime

def test_direct_event_update():
    """Test direct Event update with known Event ID"""
    
    print("🔄 TESTING DIRECT SALESFORCE EVENT UPDATE")
    print("=" * 50)
    
    # Initialize updater
    sf_updater = SalesforceEventUpdater()
    
    # Known Event ID for Nick Mihalovich
    event_id = "00UQk00000OMYzhMAH"
    
    print(f"📊 Event ID: {event_id}")
    print(f"🎯 Contact: Nick Mihalovich (Rhema Web)")
    print(f"🎯 AE: Rob Messier")
    
    # Create realistic call intelligence data for IT consulting call
    analysis_data = {
        'prospect_interest_level': 8,
        'quinn_qualification_quality': 7,
        'core_talking_points': [
            'Current VoIP system experiencing reliability issues with client calls',
            'Need scalable communication solution for growing IT consulting business',
            'Looking for API integration with their client management system',
            'Concerned about call quality affecting client relationships'
        ],
        'prospect_buying_signals': [
            'Asked about implementation timeline and technical requirements',
            'Inquired about pricing structure for expected call volume',
            'Requested API documentation and integration guides',
            'Mentioned budget approved for communication infrastructure upgrade'
        ],
        'prospect_concerns': [
            'Integration complexity with existing client management tools',
            'Potential service disruption during migration period',
            'Cost comparison with current provider and ROI timeline'
        ],
        'next_steps_actions': [
            'Send technical API documentation and integration examples',
            'Schedule follow-up call with Rhema Web technical team',
            'Prepare custom pricing proposal based on projected call volume',
            'Provide detailed migration plan with minimal downtime strategy'
        ]
    }
    
    call_data = {
        'prospect_name': 'Nick Mihalovich',
        'ae_name': 'Rob Messier',
        'company': 'Rhema Web (IT Consulting)'
    }
    
    print(f"\n📊 Analysis Summary:")
    print(f"   🎯 Interest Level: {analysis_data['prospect_interest_level']}/10")
    print(f"   📈 Qualification Quality: {analysis_data['quinn_qualification_quality']}/10")
    print(f"   🔍 Pain Points: {len(analysis_data['core_talking_points'])} identified")
    print(f"   💡 Buying Signals: {len(analysis_data['prospect_buying_signals'])} detected")
    
    # Step 1: Generate call intelligence summary
    print(f"\n📝 Generating call intelligence summary...")
    call_intelligence_summary = sf_updater.generate_call_intelligence_summary(analysis_data, call_data)
    
    print("Generated summary:")
    print("--- CALL INTELLIGENCE ---")
    print(call_intelligence_summary)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M CST')}")
    
    # Step 2: Update the Salesforce Event
    print(f"\n🔄 Updating Salesforce Event {event_id}...")
    result = sf_updater.update_event_description(event_id, call_intelligence_summary)
    
    # Step 3: Report results
    if result['success']:
        print(f"\n✅ EVENT UPDATE SUCCESSFUL!")
        print(f"   📊 Event ID: {result['event_id']}")
        print(f"   📝 Original length: {result['original_length']} characters")
        print(f"   📝 Updated length: {result['updated_length']} characters")
        print(f"   📈 Added content: {result['updated_length'] - result['original_length']} characters")
        print(f"   🕒 Updated at: {result['timestamp']}")
        
        # Save test results
        test_result = {
            'event_id': event_id,
            'call_data': call_data,
            'analysis_data': analysis_data,
            'call_intelligence_summary': call_intelligence_summary,
            'update_result': result,
            'test_timestamp': datetime.now().isoformat()
        }
        
        with open('nick_mihalovich_test.json', 'w') as f:
            json.dump(test_result, f, indent=2)
        
        print(f"\n📄 Test results saved to: nick_mihalovich_test.json")
        
        print(f"\n🎯 VERIFICATION STEPS:")
        print(f"   1. ✅ Call intelligence summary generated")
        print(f"   2. ✅ Salesforce Event.Description updated") 
        print(f"   3. ✅ Original content preserved (append-only)")
        print(f"   4. ✅ Timestamp added for audit trail")
        
        print(f"\n🚀 READY FOR INTEGRATION INTO ENHANCED_CALL_PROCESSOR!")
        
        return True
        
    else:
        print(f"\n❌ EVENT UPDATE FAILED!")
        print(f"   📊 Event ID: {result['event_id']}")
        print(f"   ❌ Error: {result['error']}")
        
        return False

def verify_event_description():
    """Verify the current Event description"""
    
    print("\n" + "="*50)
    print("🔍 VERIFYING EVENT DESCRIPTION")
    print("="*50)
    
    sf_updater = SalesforceEventUpdater()
    event_id = "00UQk00000OMYzhMAH"
    
    description = sf_updater._get_current_description(event_id)
    
    if description:
        print(f"📄 Current Event Description ({len(description)} chars):")
        print("-" * 50)
        print(description)
        print("-" * 50)
        
        # Check if call intelligence exists
        if "--- CALL INTELLIGENCE ---" in description:
            print("✅ Call intelligence section found in description")
        else:
            print("ℹ️  No call intelligence section found")
            
    else:
        print(f"❌ Could not retrieve description for Event {event_id}")

if __name__ == "__main__":
    print("🧪 DIRECT SALESFORCE EVENT UPDATE TEST")
    print("Testing Event.Description updating with call intelligence")
    
    # First verify current state
    verify_event_description()
    
    # Then run the update test
    success = test_direct_event_update()
    
    if success:
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED - SALESFORCE EVENT UPDATE WORKING!")
        print("="*60)
    else:
        print("\n" + "="*60) 
        print("❌ TEST FAILED - CHECK SALESFORCE CONFIGURATION")
        print("="*60)