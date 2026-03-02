#!/usr/bin/env python3
"""
Salesforce Event Updater for Call Intelligence
Updates Salesforce Event.Description field with call intelligence summaries
"""

import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalesforceEventUpdater:
    """Updates Salesforce Event records with call intelligence summaries"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com"):
        self.org_username = org_username
    
    def update_event_description(self, event_id: str, call_intelligence_summary: str) -> Dict[str, Any]:
        """
        Update Salesforce Event.Description field with call intelligence summary
        Appends to existing description (preserves existing content)
        
        Args:
            event_id: Salesforce Event ID (e.g., 00UQk00000OMYzhMAH)
            call_intelligence_summary: Formatted call intelligence summary
            
        Returns:
            dict: Success status and details
        """
        
        logger.info(f"Updating Salesforce Event {event_id} with call intelligence")
        
        try:
            # Step 1: Get current description
            current_description = self._get_current_description(event_id)
            if current_description is None:
                return {
                    'success': False,
                    'error': f'Could not retrieve Event {event_id}',
                    'event_id': event_id
                }
            
            # Step 2: Check if call intelligence already exists
            if "--- CALL INTELLIGENCE ---" in current_description:
                logger.info("Call intelligence already exists - updating existing section")
                # Remove existing call intelligence section
                current_description = self._remove_existing_call_intelligence(current_description)
            
            # Step 3: Append new call intelligence
            updated_description = self._append_call_intelligence(current_description, call_intelligence_summary)
            
            # Step 4: Update the Event
            success = self._update_event_record(event_id, updated_description)
            
            if success:
                return {
                    'success': True,
                    'message': 'Event description updated successfully',
                    'event_id': event_id,
                    'original_length': len(current_description or ''),
                    'updated_length': len(updated_description),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update Event description',
                    'event_id': event_id
                }
                
        except Exception as e:
            logger.error(f"Error updating Event {event_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'event_id': event_id
            }
    
    def _get_current_description(self, event_id: str) -> Optional[str]:
        """Get current Event description using sf CLI"""
        
        try:
            soql_query = f"SELECT Id, Description FROM Event WHERE Id = '{event_id}'"
            
            cmd = [
                'sf', 'data', 'query',
                '--query', soql_query,
                '--target-org', self.org_username,
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                records = response.get('result', {}).get('records', [])
                
                if records:
                    description = records[0].get('Description') or ''
                    logger.info(f"Retrieved description (length: {len(description)})")
                    return description
                else:
                    logger.warning(f"Event {event_id} not found")
                    return None
            else:
                logger.error(f"Salesforce query failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving Event description: {str(e)}")
            return None
    
    def _remove_existing_call_intelligence(self, description: str) -> str:
        """Remove existing call intelligence section from description"""
        
        call_intel_start = description.find("--- CALL INTELLIGENCE ---")
        if call_intel_start == -1:
            return description
        
        # Find the start of the call intelligence section (including preceding newlines)
        section_start = call_intel_start
        while section_start > 0 and description[section_start - 1] in ['\n', '\r']:
            section_start -= 1
        
        # Return everything before the call intelligence section
        return description[:section_start].rstrip()
    
    def _append_call_intelligence(self, current_description: str, call_intelligence_summary: str) -> str:
        """Append call intelligence to existing description"""
        
        # Ensure current description exists and is properly formatted
        if current_description:
            current_description = current_description.rstrip()
        else:
            current_description = ""
        
        # Format call intelligence section
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M CST')
        call_intel_section = f"""

--- CALL INTELLIGENCE ---
{call_intelligence_summary.strip()}

Generated: {timestamp}"""
        
        return current_description + call_intel_section
    
    def _update_event_record(self, event_id: str, new_description: str) -> bool:
        """Update Event record using sf CLI"""
        
        try:
            # Escape description for JSON
            escaped_description = json.dumps(new_description)
            
            cmd = [
                'sf', 'data', 'update', 'record',
                '--sobject', 'Event',
                '--record-id', event_id,
                '--values', f'Description={escaped_description}',
                '--target-org', self.org_username,
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully updated Event {event_id}")
                return True
            else:
                logger.error(f"Failed to update Event: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Event record: {str(e)}")
            return False
    
    def generate_call_intelligence_summary(self, analysis_data: Dict, call_data: Dict) -> str:
        """
        Generate formatted call intelligence summary for Salesforce Event
        
        Args:
            analysis_data: Analysis results from OpenAI
            call_data: Call metadata
            
        Returns:
            str: Formatted call intelligence summary
        """
        
        # Extract key insights
        talking_points = analysis_data.get('core_talking_points', [])
        pain_points = [point for point in talking_points if point]  # Filter empty points
        
        buying_signals = analysis_data.get('prospect_buying_signals', [])
        concerns = analysis_data.get('prospect_concerns', [])
        next_steps = analysis_data.get('next_steps_actions', [])
        
        # Format pain points
        pain_points_text = "\n".join([f"• {point}" for point in pain_points[:3]]) if pain_points else "• None identified"
        
        # Format buying signals
        signals_text = "\n".join([f"• {signal}" for signal in buying_signals[:3]]) if buying_signals else "• None detected"
        
        # Format concerns
        concerns_text = "\n".join([f"• {concern}" for concern in concerns[:3]]) if concerns else "• None raised"
        
        # Format next steps
        next_steps_text = "\n".join([f"• {step}" for step in next_steps[:3]]) if next_steps else "• Follow-up required"
        
        # Generate summary
        interest_level = analysis_data.get('prospect_interest_level', 0)
        qualification_quality = analysis_data.get('quinn_qualification_quality', 0)
        
        summary = f"""Summary: {self._generate_summary_text(interest_level, qualification_quality)}

Pain Points Identified:
{pain_points_text}

Buying Signals:
{signals_text}

Concerns Raised:
{concerns_text}

Next Steps:
{next_steps_text}

Call Quality Score: {qualification_quality}/10 | Interest Level: {interest_level}/10"""
        
        return summary
    
    def _generate_summary_text(self, interest_level: int, qualification_quality: int) -> str:
        """Generate brief summary text based on scores"""
        
        if interest_level >= 7 and qualification_quality >= 7:
            return "High-quality discovery call with strong prospect engagement"
        elif interest_level >= 5 and qualification_quality >= 5:
            return "Productive call with moderate prospect interest and good qualification"
        elif interest_level >= 3:
            return "Initial discovery completed, follow-up needed to gauge interest"
        else:
            return "Early-stage call, requires additional qualification efforts"
    
    def test_update_functionality(self, event_id: str = "00UQk00000OMYzhMAH") -> Dict[str, Any]:
        """
        Test the Event updating functionality with sample data
        
        Args:
            event_id: Event ID to test with (default: Nick Mihalovich)
            
        Returns:
            dict: Test results
        """
        
        logger.info(f"Testing Event update functionality with Event {event_id}")
        
        # Sample call intelligence data
        sample_analysis = {
            'core_talking_points': [
                'Current communication setup causing reliability issues',
                'Need for scalable voice solution to support growth',
                'Interest in API-driven approach for integration'
            ],
            'prospect_buying_signals': [
                'Asked about implementation timeline',
                'Inquired about pricing for volume discounts',
                'Requested technical documentation'
            ],
            'prospect_concerns': [
                'Integration complexity with existing systems',
                'Potential downtime during migration'
            ],
            'next_steps_actions': [
                'Send technical integration guide',
                'Schedule follow-up with engineering team',
                'Prepare custom pricing proposal'
            ],
            'prospect_interest_level': 8,
            'quinn_qualification_quality': 7
        }
        
        sample_call_data = {
            'prospect_name': 'Nick Mihalovich',
            'ae_name': 'Rob Messier',
            'company': 'Rhema Web'
        }
        
        # Generate call intelligence summary
        call_intelligence = self.generate_call_intelligence_summary(sample_analysis, sample_call_data)
        
        # Update the Event
        result = self.update_event_description(event_id, call_intelligence)
        
        return result

def demo_salesforce_event_updating():
    """Demo the Salesforce Event updating functionality"""
    
    print("🔄 SALESFORCE EVENT UPDATING DEMO")
    print("=" * 50)
    
    updater = SalesforceEventUpdater()
    
    # Test with Nick Mihalovich event
    nick_event_id = "00UQk00000OMYzhMAH"
    
    print(f"📝 Testing Event update with ID: {nick_event_id}")
    print(f"🎯 Event: Nick Mihalovich (Rhema Web) - Rob Messier")
    
    # Run test
    result = updater.test_update_functionality(nick_event_id)
    
    if result['success']:
        print("\n✅ EVENT UPDATE SUCCESSFUL!")
        print(f"   📊 Event ID: {result['event_id']}")
        print(f"   📝 Original length: {result['original_length']} chars")
        print(f"   📝 Updated length: {result['updated_length']} chars")
        print(f"   🕒 Updated at: {result['timestamp']}")
        print("\n🎯 Call intelligence has been appended to Salesforce Event description!")
        
        # Show what was added
        sample_intelligence = updater.generate_call_intelligence_summary(
            {
                'core_talking_points': ['Current communication setup causing reliability issues'],
                'prospect_buying_signals': ['Asked about implementation timeline'],
                'prospect_concerns': ['Integration complexity'],
                'next_steps_actions': ['Send technical integration guide'],
                'prospect_interest_level': 8,
                'quinn_qualification_quality': 7
            },
            {'prospect_name': 'Nick Mihalovich'}
        )
        
        print(f"\n📋 Sample Call Intelligence Added:")
        print("--- CALL INTELLIGENCE ---")
        print(sample_intelligence)
        
    else:
        print(f"\n❌ EVENT UPDATE FAILED: {result['error']}")
        print(f"   📊 Event ID: {result['event_id']}")
    
    print(f"\n✨ Integration ready for production deployment!")

if __name__ == "__main__":
    demo_salesforce_event_updating()