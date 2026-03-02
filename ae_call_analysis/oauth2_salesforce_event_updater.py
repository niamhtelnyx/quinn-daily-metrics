#!/usr/bin/env python3
"""
OAuth2 Salesforce Event Updater for Call Intelligence
Updates Salesforce Event.Description field using OAuth2 API (not broken CLI)
"""

from salesforce_oauth2_client import sf_query, sf_update
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OAuth2SalesforceEventUpdater:
    """Updates Salesforce Event records using OAuth2 API"""
    
    def __init__(self):
        logger.info("Initialized OAuth2 Salesforce Event Updater")
    
    def get_event_description(self, event_id: str) -> Optional[str]:
        """Get current Event.Description using OAuth2 API"""
        try:
            soql_query = f"SELECT Id, Description FROM Event WHERE Id = '{event_id}'"
            result = sf_query(soql_query)
            
            if result and result.get('records'):
                record = result['records'][0]
                return record.get('Description', '')
            else:
                logger.warning(f"Event {event_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get event description: {e}")
            return None
    
    def update_event_description(self, event_id: str, call_intelligence_summary: str) -> Dict[str, Any]:
        """
        Update Salesforce Event.Description field with call intelligence summary
        Appends to existing description (preserves existing content)
        """
        try:
            logger.info(f"Updating Salesforce Event {event_id} with call intelligence")
            
            # Get current description
            current_description = self.get_event_description(event_id)
            if current_description is None:
                return {
                    'success': False, 
                    'error': f'Could not retrieve Event {event_id}'
                }
            
            # Create separator and timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M CST')
            separator = f"\n\n{'='*50}\n🤖 CALL INTELLIGENCE UPDATE ({timestamp})\n{'='*50}\n"
            
            # Append call intelligence to existing description
            new_description = (current_description or '') + separator + call_intelligence_summary
            
            # Update via OAuth2 API
            update_result = sf_update('Event', event_id, {'Description': new_description})
            
            if update_result and update_result.get('success'):
                logger.info(f"Successfully updated Event {event_id}")
                return {
                    'success': True,
                    'event_id': event_id,
                    'updated_length': len(new_description),
                    'timestamp': timestamp
                }
            else:
                error_msg = update_result.get('error', 'Unknown error') if update_result else 'No response'
                logger.error(f"Failed to update Event {event_id}: {error_msg}")
                return {
                    'success': False,
                    'error': f'Update failed: {error_msg}'
                }
                
        except Exception as e:
            logger.error(f"Exception updating Event {event_id}: {e}")
            return {
                'success': False,
                'error': f'Exception: {str(e)}'
            }
    
    def generate_call_intelligence_summary(self, analysis_data: Dict, call_data: Dict) -> str:
        """Generate formatted call intelligence summary for Salesforce Event"""
        
        # Extract key data
        confidence = analysis_data.get('analysis_confidence', 'N/A')
        interest = analysis_data.get('prospect_interest_level', 'N/A')
        ae_excitement = analysis_data.get('ae_excitement_level', 'N/A')
        qualification = analysis_data.get('quinn_qualification_quality', 'N/A')
        
        talking_points = analysis_data.get('core_talking_points', [])
        use_cases = analysis_data.get('use_cases', [])
        buying_signals = analysis_data.get('prospect_buying_signals', [])
        next_steps = analysis_data.get('next_steps_actions', [])
        
        # Format for Salesforce Event Description
        summary = f"""🤖 CALL INTELLIGENCE ANALYSIS

PERFORMANCE SCORES:
• Analysis Confidence: {confidence}/10
• Prospect Interest: {interest}/10  
• AE Excitement: {ae_excitement}/10
• Qualification Quality: {qualification}/10

PAIN POINTS IDENTIFIED:"""
        
        for point in talking_points[:5]:  # Limit to top 5
            summary += f"\n• {point}"
        
        if use_cases:
            summary += f"\n\nUSE CASES DISCUSSED:"
            for case in use_cases[:3]:
                summary += f"\n• {case}"
        
        if buying_signals:
            summary += f"\n\nBUYING SIGNALS:"
            for signal in buying_signals[:3]:
                summary += f"\n• {signal}"
        
        if next_steps:
            summary += f"\n\nNEXT STEPS:"
            for step in next_steps[:3]:
                summary += f"\n• {step}"
        
        summary += f"\n\n📊 Analyzed by AI Call Intelligence System"
        summary += f"\n🎯 Prospect: {call_data.get('prospect_name', 'Unknown')}"
        summary += f"\n📅 Call Date: {call_data.get('call_date', 'Unknown')}"
        
        return summary
    
    def update_event_with_intelligence(self, event_id: str, analysis_data: Dict, call_data: Dict) -> Dict[str, Any]:
        """High-level method to update event with complete call intelligence"""
        
        # Generate summary
        call_intelligence_summary = self.generate_call_intelligence_summary(analysis_data, call_data)
        
        # Update event
        return self.update_event_description(event_id, call_intelligence_summary)

def test_oauth2_event_update():
    """Test the OAuth2 event updater"""
    
    print("🧪 Testing OAuth2 Salesforce Event Update")
    print("=" * 50)
    
    updater = OAuth2SalesforceEventUpdater()
    
    # Test with known event ID (Olivier's event)
    event_id = "00UQk00000OQr4WMAT"
    
    # Mock analysis data
    analysis_data = {
        'analysis_confidence': 8,
        'prospect_interest_level': 7,
        'ae_excitement_level': 8,
        'quinn_qualification_quality': 7,
        'core_talking_points': ["International number provisioning", "High cost of Swiss numbers"],
        'use_cases': ["International number provisioning"],
        'prospect_buying_signals': ["Interest in Managed Accounts"],
        'next_steps_actions': ["Create a Telnyx account"]
    }
    
    call_data = {
        'prospect_name': 'Olivier MOUILLESEAUX',
        'call_date': '2026-02-27'
    }
    
    print(f"🔄 Testing event update for: {event_id}")
    
    result = updater.update_event_with_intelligence(event_id, analysis_data, call_data)
    
    if result['success']:
        print(f"✅ Event update successful!")
        print(f"📝 Updated length: {result.get('updated_length')} characters")
    else:
        print(f"❌ Event update failed: {result.get('error')}")
    
    return result

if __name__ == "__main__":
    test_oauth2_event_update()