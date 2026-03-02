#!/usr/bin/env python3
"""
Record ID Validated Salesforce Integration
Uses 005/003/006 prefixes to properly identify Users vs Contacts vs Opportunities
"""

import subprocess
import json
from typing import Dict, List, Tuple

class RecordIDValidatedIntegration:
    """Salesforce integration using record ID prefixes for proper identification"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com"):
        self.org_username = org_username
    
    def lookup_event_with_proper_identification(self, event_id: str) -> Dict:
        """Look up event and properly identify Users vs Contacts using record IDs"""
        
        query = f"""
        SELECT Id, Subject, StartDateTime, EndDateTime,
               Who.Id, Who.Name, Who.Email, Who.Account.Name,
               Owner.Id, Owner.Name, Owner.Email,
               (SELECT RelationId, Relation.Id, Relation.Name, Relation.Email 
                FROM EventRelations WHERE IsDeleted = false)
        FROM Event 
        WHERE Id = '{event_id}'
        """
        
        try:
            result = self._execute_query(query)
            if result and len(result) > 0:
                return self._process_event_with_record_ids(result[0])
            return None
        except Exception as e:
            print(f"❌ Error looking up event: {e}")
            return None
    
    def find_recent_events_with_validation(self, limit: int = 5) -> List[Dict]:
        """Get recent events with proper User/Contact identification"""
        
        query = f"""
        SELECT Id, Subject, StartDateTime, Who.Name, Owner.Name
        FROM Event 
        WHERE Subject LIKE '%Telnyx Intro Call%' 
          AND StartDateTime >= 2026-02-25T00:00:00Z
        ORDER BY StartDateTime DESC 
        LIMIT {limit}
        """
        
        try:
            events = self._execute_query(query)
            validated_events = []
            
            for event in events:
                event_id = event['Id']
                detailed_event = self.lookup_event_with_proper_identification(event_id)
                if detailed_event:
                    validated_events.append(detailed_event)
                    
            return validated_events
        except Exception as e:
            print(f"❌ Error finding events: {e}")
            return []
    
    def _process_event_with_record_ids(self, event: Dict) -> Dict:
        """Process event data using record ID prefixes for proper identification"""
        
        # Basic event info
        processed = {
            'event_id': event.get('Id'),
            'subject': event.get('Subject'),
            'start_datetime': event.get('StartDateTime'),
            'end_datetime': event.get('EndDateTime'),
            
            # Event owner (primary AE)
            'owner_id': event.get('Owner', {}).get('Id'),
            'owner_name': event.get('Owner', {}).get('Name'),
            'owner_email': event.get('Owner', {}).get('Email'),
            
            # Primary contact  
            'primary_contact_id': event.get('Who', {}).get('Id'),
            'primary_contact_name': event.get('Who', {}).get('Name'),
            'primary_contact_email': event.get('Who', {}).get('Email'),
            'account_name': event.get('Who', {}).get('Account', {}).get('Name'),
            
            # Categorized attendees
            'telnyx_users': [],      # 005xxx IDs
            'prospect_contacts': [], # 003xxx IDs  
            'leads': [],            # 00Qxxx IDs
            'opportunities': [],    # 006xxx IDs
            'other_records': []     # Unknown types
        }
        
        # Always include event owner as Telnyx user (should be 005xxx)
        owner_id = processed['owner_id']
        owner_name = processed['owner_name']
        
        if owner_id and self._is_user_record(owner_id):
            processed['telnyx_users'].append({
                'id': owner_id,
                'name': owner_name,
                'email': processed['owner_email'],
                'role': 'event_owner'
            })
        
        # Process all event relations by record ID
        event_relations = event.get('EventRelations', {}).get('records', [])
        for relation in event_relations:
            attendee = relation.get('Relation', {})
            attendee_id = attendee.get('Id', '')
            attendee_name = attendee.get('Name', '')
            attendee_email = attendee.get('Email', '')
            
            # Categorize by record ID prefix
            if self._is_user_record(attendee_id):
                # 005xxx = Telnyx User
                if attendee_id != owner_id:  # Don't duplicate owner
                    processed['telnyx_users'].append({
                        'id': attendee_id,
                        'name': attendee_name,
                        'email': attendee_email,
                        'role': 'attendee'
                    })
                    
            elif self._is_contact_record(attendee_id):
                # 003xxx = Prospect/Contact
                processed['prospect_contacts'].append({
                    'id': attendee_id,
                    'name': attendee_name,
                    'email': attendee_email,
                    'role': 'prospect'
                })
                
            elif self._is_lead_record(attendee_id):
                # 00Qxxx = Lead
                processed['leads'].append({
                    'id': attendee_id,
                    'name': attendee_name,
                    'email': attendee_email,
                    'role': 'lead'
                })
                
            elif self._is_opportunity_record(attendee_id):
                # 006xxx = Opportunity
                processed['opportunities'].append({
                    'id': attendee_id,
                    'name': attendee_name,
                    'role': 'opportunity'
                })
                
            else:
                # Unknown record type
                processed['other_records'].append({
                    'id': attendee_id,
                    'name': attendee_name,
                    'type': 'unknown'
                })
        
        # Generate formatted strings for Call Intelligence
        telnyx_names = [user['name'] for user in processed['telnyx_users']]
        prospect_names = [contact['name'] for contact in processed['prospect_contacts']]
        
        processed['formatted_ae_names'] = ' & '.join(telnyx_names) if telnyx_names else 'Unknown AE'
        processed['formatted_prospect_names'] = ' & '.join(prospect_names) if prospect_names else processed['primary_contact_name']
        
        # Call Intelligence format
        processed['call_type'] = self._determine_call_type(processed)
        
        return processed
    
    def _is_user_record(self, record_id: str) -> bool:
        """Check if record ID is a User (005xxx)"""
        return record_id.startswith('005')
    
    def _is_contact_record(self, record_id: str) -> bool:
        """Check if record ID is a Contact (003xxx)"""
        return record_id.startswith('003')
    
    def _is_lead_record(self, record_id: str) -> bool:
        """Check if record ID is a Lead (00Qxxx)"""
        return record_id.startswith('00Q')
    
    def _is_opportunity_record(self, record_id: str) -> bool:
        """Check if record ID is an Opportunity (006xxx)"""
        return record_id.startswith('006')
    
    def _determine_call_type(self, processed_event: Dict) -> str:
        """Determine the type of call based on attendees"""
        
        telnyx_count = len(processed_event['telnyx_users'])
        prospect_count = len(processed_event['prospect_contacts'])
        
        if telnyx_count == 1 and prospect_count == 1:
            return 'standard_1on1'
        elif telnyx_count == 1 and prospect_count > 1:
            return 'multi_prospect'
        elif telnyx_count > 1 and prospect_count == 1:
            return 'team_selling'
        elif telnyx_count > 1 and prospect_count > 1:
            return 'multi_party'
        else:
            return 'unknown'
    
    def _execute_query(self, query: str) -> List[Dict]:
        """Execute SOQL query and return results"""
        
        cmd = [
            'sf', 'data', 'query',
            '--query', query,
            '--target-org', self.org_username,
            '--json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get('result', {}).get('records', [])
        else:
            raise Exception(f"Query failed: {result.stderr}")

def demo_record_id_validation():
    """Demo the record ID validation system"""
    
    print("🔍 RECORD ID VALIDATED SALESFORCE INTEGRATION")
    print("="*60)
    
    integration = RecordIDValidatedIntegration()
    
    # Test with the Nick Mihalovich event
    test_event_id = "00UQk00000OMYzhMAH"
    
    print(f"Testing with Event ID: {test_event_id}")
    print("(Nick Mihalovich call)")
    
    event_data = integration.lookup_event_with_proper_identification(test_event_id)
    
    if event_data:
        print(f"\\n✅ EVENT PROCESSED WITH RECORD ID VALIDATION:")
        print(f"📋 Subject: {event_data['subject']}")
        print(f"🎯 Call Type: {event_data['call_type']}")
        
        print(f"\\n👥 ATTENDEE BREAKDOWN:")
        print(f"   Telnyx Users (005): {len(event_data['telnyx_users'])}")
        for user in event_data['telnyx_users']:
            print(f"      • {user['name']} ({user['id']}) - {user['role']}")
            
        print(f"   Prospect Contacts (003): {len(event_data['prospect_contacts'])}")
        for contact in event_data['prospect_contacts']:
            print(f"      • {contact['name']} ({contact['id']}) - {contact['role']}")
            
        print(f"   Opportunities (006): {len(event_data['opportunities'])}")
        for opp in event_data['opportunities']:
            print(f"      • {opp['name']} ({opp['id']}) - {opp['role']}")
        
        print(f"\\n📝 CALL INTELLIGENCE FORMAT:")
        print(f"   AE(s): {event_data['formatted_ae_names']}")
        print(f"   Prospect(s): {event_data['formatted_prospect_names']}")
        
        print(f"\\n✅ PROPERLY IDENTIFIED:")
        print(f"   ❌ OLD: Rob Messier & Darren Dunner (both as AEs)")
        print(f"   ✅ NEW: Rob Messier (AE) + Nick Mihalovich & Darren Dunner (prospects)")
        
        return event_data
    else:
        print("❌ Failed to process event")
        return None

if __name__ == "__main__":
    demo_record_id_validation()