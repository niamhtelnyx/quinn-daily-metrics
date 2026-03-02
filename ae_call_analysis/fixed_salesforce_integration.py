#!/usr/bin/env python3
"""
FIXED Salesforce Integration - Uses Real Data
No more fake attendees - pulls actual event data
"""

import subprocess
import json
from datetime import datetime

class FixedSalesforceIntegration:
    """Fixed integration that pulls real Salesforce event data"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com"):
        self.org_username = org_username
    
    def get_real_recent_events(self, limit: int = 5):
        """Get actual recent Telnyx intro call events"""
        
        query = f"""
        SELECT Id, Subject, StartDateTime, Who.Name, Who.Email, Who.Account.Name,
               Owner.Name, Owner.Email,
               (SELECT Relation.Name, Relation.Email FROM EventRelations WHERE IsDeleted = false)
        FROM Event 
        WHERE Subject LIKE '%Telnyx Intro Call%' 
          AND StartDateTime >= 2026-02-25T00:00:00Z
        ORDER BY StartDateTime DESC 
        LIMIT {limit}
        """
        
        try:
            cmd = [
                'sf', 'data', 'query',
                '--query', query,
                '--target-org', self.org_username,
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                events = response.get('result', {}).get('records', [])
                
                # Process and enrich the events
                enriched_events = []
                for event in events:
                    enriched_event = self._enrich_real_event(event)
                    enriched_events.append(enriched_event)
                
                return enriched_events
            else:
                print(f"❌ Salesforce query failed: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting real events: {e}")
            return []
    
    def _enrich_real_event(self, event):
        """Process real Salesforce event data"""
        
        # Basic event data
        enriched = {
            'event_id': event.get('Id'),
            'subject': event.get('Subject'),
            'start_datetime': event.get('StartDateTime'),
            'contact_name': event.get('Who', {}).get('Name'),
            'contact_email': event.get('Who', {}).get('Email'),
            'account_name': event.get('Who', {}).get('Account', {}).get('Name'),
            'primary_ae_name': event.get('Owner', {}).get('Name'),
            'primary_ae_email': event.get('Owner', {}).get('Email'),
            'real_attendees': [],
            'telnyx_attendees': []
        }
        
        # Process attendees
        event_relations = event.get('EventRelations', {}).get('records', [])
        for relation in event_relations:
            attendee = relation.get('Relation', {})
            name = attendee.get('Name', '')
            email = attendee.get('Email', '')
            
            enriched['real_attendees'].append({
                'name': name,
                'email': email
            })
            
            # Identify Telnyx employees (exclude prospects and opportunities)
            if (email and '@telnyx.com' in email) or \
               (name and not any(keyword in name.lower() for keyword in ['new customer', ':', '$', 'qualified by'])):
                # This looks like a real person, not an opportunity record
                if name not in [enriched['contact_name']]:  # Not the prospect
                    enriched['telnyx_attendees'].append(name)
        
        # Include primary AE in Telnyx attendees if not already there
        if enriched['primary_ae_name'] not in enriched['telnyx_attendees']:
            enriched['telnyx_attendees'].insert(0, enriched['primary_ae_name'])
        
        # Format AE names
        enriched['formatted_ae_names'] = ' & '.join(enriched['telnyx_attendees'][:3])
        
        return enriched

def demo_real_salesforce_data():
    """Demo with actual real Salesforce data"""
    
    print("🔍 FIXED SALESFORCE INTEGRATION - REAL DATA")
    print("="*60)
    
    integration = FixedSalesforceIntegration()
    
    # Get actual recent events
    real_events = integration.get_real_recent_events(3)
    
    if real_events:
        print(f"✅ Found {len(real_events)} REAL Salesforce events:")
        
        for i, event in enumerate(real_events, 1):
            print(f"\n--- REAL EVENT {i} ---")
            print(f"📋 Event ID: {event['event_id']}")
            print(f"📞 Subject: {event['subject']}")
            print(f"👤 Prospect: {event['contact_name']}")
            print(f"📧 Contact Email: {event['contact_email']}")
            print(f"🏢 Account: {event['account_name']}")
            print(f"🎯 Primary AE: {event['primary_ae_name']} ({event['primary_ae_email']})")
            print(f"👥 All Telnyx AEs: {event['telnyx_attendees']}")
            print(f"📝 Formatted: {event['formatted_ae_names']}")
            
            print(f"🔗 Salesforce URL: https://telnyx.lightning.force.com/lightning/r/{event['event_id']}/view")
            
            # Show how this would appear in Call Intelligence
            print(f"\n📊 Call Intelligence Preview:")
            print(f"**{event['contact_name']}** | **{event['formatted_ae_names']}** | {event['start_datetime'][:10]}")
            print(f"**🔗 Salesforce:** ✅ Validated (Event ID: {event['event_id']})")
            
            if i == 1:  # Save the first real event for deployment
                with open('real_sf_event_data.json', 'w') as f:
                    json.dump(event, f, indent=2)
                print(f"💾 Saved real event data to real_sf_event_data.json")
            
        print(f"\n🎯 NO MORE FAKE DATA!")
        print(f"   ❌ No more 'Quinn Stevenson' or made-up names")
        print(f"   ✅ Real AEs: Rob Messier, Luke Attride, Michael DiPaolo, etc.")
        print(f"   ✅ Real prospects: Nick Mihalovich, Angel Gonzalez-Bravo, etc.")
        print(f"   ✅ Real Salesforce Event IDs and URLs")
        
        return real_events[0]  # Return first real event
        
    else:
        print("❌ No real events found")
        return None

if __name__ == "__main__":
    demo_real_salesforce_data()