#!/usr/bin/env python3
"""
Fixed Salesforce Integration using OAuth2 - Replacement for broken CLI approach
"""

from salesforce_oauth2_client import CallIntelligenceSalesforceClient, sf_query
import json

class FixedSalesforceEventIntegration:
    """Working Salesforce integration using OAuth2 instead of broken CLI"""
    
    def __init__(self):
        self.sf_client = CallIntelligenceSalesforceClient()
    
    def lookup_event_by_prospect(self, prospect_name, call_date=None):
        """Look up Salesforce event by prospect name with date range matching"""
        
        print(f"🔍 Looking up Salesforce event for: {prospect_name}")
        
        try:
            # Enhanced search patterns with exact name matching
            search_patterns = [
                f'Meeting Booked: Telnyx Intro Call ({prospect_name})',
                f'Telnyx Intro Call ({prospect_name})', 
                f'Intro Call ({prospect_name})',
                prospect_name
            ]
            
            for pattern in search_patterns:
                print(f"   🔍 Searching: {pattern}")
                event = self._search_events_by_pattern_with_date_range(pattern, call_date)
                if event:
                    print(f"   ✅ Found match: {event['Subject']}")
                    print(f"   📅 Event date: {event.get('StartDateTime')}")
                    return self._enrich_event_data(event)
            
            print("   ❌ No matching events found")
            return None
            
        except Exception as e:
            print(f"❌ Salesforce lookup error: {e}")
            return None
    
    def _search_events_by_pattern(self, pattern):
        """Search for events matching pattern using OAuth2"""
        
        soql_query = f"""
        SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId
        FROM Event 
        WHERE Subject LIKE '%{pattern}%'
        ORDER BY StartDateTime DESC
        LIMIT 5
        """
        
        try:
            result = sf_query(soql_query)
            if result['records']:
                event = result['records'][0]
                return event
            else:
                return None
        except Exception as e:
            print(f"   ❌ Query error: {e}")
            return None
    
    def _search_events_by_pattern_with_date_range(self, pattern, call_date=None):
        """Search for events with ±7 day range to handle rescheduled meetings"""
        
        if call_date:
            # Parse call date and create search window (±7 days for rescheduled meetings)
            try:
                from datetime import datetime, timedelta
                call_dt = datetime.fromisoformat(call_date.replace('Z', '+00:00'))
                start_date = (call_dt - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                end_date = (call_dt + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                
                soql_query = f"""
                SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId
                FROM Event 
                WHERE Subject LIKE '%{pattern}%'
                  AND StartDateTime >= {start_date}
                  AND StartDateTime <= {end_date}
                ORDER BY StartDateTime DESC
                LIMIT 5
                """
            except:
                # Fallback to no date filter if parsing fails
                soql_query = f"""
                SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId
                FROM Event 
                WHERE Subject LIKE '%{pattern}%'
                ORDER BY StartDateTime DESC
                LIMIT 5
                """
        else:
            # No date filtering
            soql_query = f"""
            SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId
            FROM Event 
            WHERE Subject LIKE '%{pattern}%'
            ORDER BY StartDateTime DESC
            LIMIT 5
            """
        
        try:
            result = sf_query(soql_query)
            if result['records']:
                event = result['records'][0]
                print(f"   📋 Found event: {event['Subject']} on {event.get('StartDateTime')}")
                return event
            else:
                print(f"   📋 No events found for pattern: {pattern}")
                return None
        except Exception as e:
            print(f"   ❌ Query error: {e}")
            return None
    
    def _enrich_event_data(self, event):
        """Format event data for Call Intelligence"""
        
        event_id = event.get('Id')
        who_id = event.get('WhoId')
        owner_id = event.get('OwnerId')
        
        # Get contact details if WhoId is available
        contact_name = None
        contact_email = None
        account_name = None
        account_id = None
        
        if who_id:
            try:
                contact_query = f"SELECT Name, Email, AccountId FROM Contact WHERE Id = '{who_id}'"
                contact_result = sf_query(contact_query)
                if contact_result['records']:
                    contact_data = contact_result['records'][0]
                    contact_name = contact_data.get('Name')
                    contact_email = contact_data.get('Email')
                    account_id = contact_data.get('AccountId')
                    
                    # Get account name if AccountId available
                    if account_id:
                        account_query = f"SELECT Name FROM Account WHERE Id = '{account_id}'"
                        account_result = sf_query(account_query)
                        if account_result['records']:
                            account_name = account_result['records'][0]['Name']
            except Exception as e:
                print(f"   ⚠️  Contact lookup failed: {e}")
        
        # Get owner details if OwnerId is available
        owner_name = None
        owner_email = None
        
        if owner_id:
            try:
                owner_query = f"SELECT Name, Email FROM User WHERE Id = '{owner_id}'"
                owner_result = sf_query(owner_query)
                if owner_result['records']:
                    owner_data = owner_result['records'][0]
                    owner_name = owner_data.get('Name')
                    owner_email = owner_data.get('Email')
            except Exception as e:
                print(f"   ⚠️  Owner lookup failed: {e}")
        
        return {
            'event_id': event_id,
            'subject': event.get('Subject'),
            'start_datetime': event.get('StartDateTime'),
            'end_datetime': event.get('EndDateTime'),
            
            # Contact information  
            'contact_name': contact_name,
            'contact_email': contact_email,
            'account_name': account_name,
            'account_id': account_id,
            
            # AE information (event owner)
            'primary_ae_name': owner_name,
            'primary_ae_email': owner_email,
            'owner_name': owner_name,
            'formatted_ae_names': owner_name,
            
            # Additional metadata
            'telnyx_attendees': [],
            'prospect_attendees': []
        }
    
    def update_call_with_salesforce_data(self, call_id, sf_event):
        """Update call record with Salesforce data"""
        
        # This would update the database with enriched data
        print(f"   📊 Updating call {call_id} with Salesforce data")
        print(f"   🎯 AE: {sf_event.get('formatted_ae_names', 'Unknown')}")
        print(f"   🏢 Account: {sf_event.get('account_name', 'Unknown')}")
        
        return True

# Test function
def test_oauth2_event_lookup():
    """Test the working OAuth2 Salesforce integration"""
    
    print("🧪 Testing OAuth2 Salesforce Event Lookup")
    print("=" * 50)
    
    integration = FixedSalesforceEventIntegration()
    
    # Test with a known prospect
    test_prospects = [
        'Olivier MOUILLESEAUX',
        'Devon Johnson', 
        'Ben Lewell'
    ]
    
    for prospect in test_prospects:
        print(f"\n📞 Testing: {prospect}")
        result = integration.lookup_event_by_prospect(prospect)
        
        if result:
            print(f"✅ SUCCESS!")
            print(f"   📋 Event: {result['subject']}")
            print(f"   🎯 AE: {result['formatted_ae_names']}")
            print(f"   🏢 Account: {result['account_name']}")
            print(f"   📅 Date: {result['start_datetime']}")
        else:
            print(f"❌ No event found")
    
    return True

if __name__ == "__main__":
    test_oauth2_event_lookup()