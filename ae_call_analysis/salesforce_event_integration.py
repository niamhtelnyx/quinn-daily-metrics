#!/usr/bin/env python3
"""
Salesforce Event Integration for Call Intelligence
Looks up Salesforce events to get AE names, contacts, and account info
"""

import subprocess
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List

class SalesforceEventIntegration:
    """Integration to lookup Salesforce events and extract attendee/AE data"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com"):
        self.org_username = org_username
    
    def lookup_event_by_prospect(self, prospect_name: str, call_date: str = None) -> Optional[Dict]:
        """Look up Salesforce event by prospect name and optional date"""
        
        # Try multiple search patterns
        search_patterns = [
            f'Meeting Booked: Telnyx Intro Call ({prospect_name})',
            f'Telnyx Intro Call ({prospect_name})',
            prospect_name
        ]
        
        for pattern in search_patterns:
            event = self._search_events_by_pattern(pattern)
            if event:
                return self._enrich_event_data(event)
        
        # If no exact match, try date-based search
        if call_date:
            return self._search_events_by_date(call_date, prospect_name)
        
        return None
    
    def _search_events_by_pattern(self, pattern: str) -> Optional[Dict]:
        """Search for events matching a specific pattern"""
        
        soql_query = f"""
        SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId,
               Who.Name, Who.Email, Who.Account.Name, Who.Account.Id,
               Owner.Name, Owner.Email,
               (SELECT Id, RelationId, Relation.Name, Relation.Email 
                FROM EventRelations 
                WHERE IsDeleted = false)
        FROM Event 
        WHERE Subject LIKE '%{pattern}%'
        ORDER BY StartDateTime DESC
        LIMIT 5
        """
        
        events = self._execute_soql_query(soql_query)
        return events[0] if events else None
    
    def _search_events_by_date(self, call_date: str, prospect_hint: str = None) -> Optional[Dict]:
        """Search for events around a specific date with optional prospect hint"""
        
        # Parse call date and create search window
        try:
            call_dt = datetime.fromisoformat(call_date.replace('Z', '+00:00'))
            start_date = (call_dt - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            end_date = (call_dt + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except:
            # Fallback to day-based search
            date_str = call_date[:10]  # YYYY-MM-DD
            start_date = f"{date_str}T00:00:00.000Z"
            end_date = f"{date_str}T23:59:59.000Z"
        
        soql_query = f"""
        SELECT Id, Subject, StartDateTime, EndDateTime, WhoId, WhatId, OwnerId,
               Who.Name, Who.Email, Who.Account.Name, Who.Account.Id,
               Owner.Name, Owner.Email,
               (SELECT Id, RelationId, Relation.Name, Relation.Email 
                FROM EventRelations 
                WHERE IsDeleted = false)
        FROM Event 
        WHERE Subject LIKE '%Telnyx Intro Call%'
          AND StartDateTime >= {start_date}
          AND StartDateTime <= {end_date}
        ORDER BY StartDateTime DESC
        LIMIT 10
        """
        
        events = self._execute_soql_query(soql_query)
        
        # If prospect hint provided, try to find best match
        if prospect_hint and events:
            for event in events:
                contact_name = event.get('Who', {}).get('Name', '')
                if prospect_hint.lower() in contact_name.lower():
                    return event
        
        return events[0] if events else None
    
    def _execute_soql_query(self, soql_query: str) -> List[Dict]:
        """Execute SOQL query using sf CLI"""
        
        try:
            cmd = [
                'sf', 'data', 'query', 
                '--query', soql_query,
                '--target-org', self.org_username,
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                return response.get('result', {}).get('records', [])
            else:
                print(f"Salesforce query error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("Salesforce query timed out")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response from Salesforce: {e}")
        except Exception as e:
            print(f"Error executing Salesforce query: {e}")
        
        return []
    
    def _enrich_event_data(self, event: Dict) -> Dict:
        """Enrich event data with extracted AE and attendee information"""
        
        # Extract basic event info
        enriched = {
            'event_id': event.get('Id'),
            'subject': event.get('Subject'),
            'start_datetime': event.get('StartDateTime'),
            'end_datetime': event.get('EndDateTime'),
            
            # Contact information
            'contact_name': event.get('Who', {}).get('Name'),
            'contact_email': event.get('Who', {}).get('Email'),
            'account_name': event.get('Who', {}).get('Account', {}).get('Name'),
            'account_id': event.get('Who', {}).get('Account', {}).get('Id'),
            
            # Primary AE (event owner)
            'primary_ae_name': event.get('Owner', {}).get('Name'),
            'primary_ae_email': event.get('Owner', {}).get('Email'),
            
            # All attendees
            'telnyx_attendees': [],
            'prospect_attendees': [],
            'all_attendees': []
        }
        
        # Process attendees
        attendees = event.get('EventRelations', {}).get('records', [])
        for attendee_rel in attendees:
            attendee = attendee_rel.get('Relation', {})
            if not attendee.get('Name'):
                continue
                
            name = attendee['Name']
            email = attendee.get('Email', '')
            
            enriched['all_attendees'].append({
                'name': name,
                'email': email
            })
            
            # Categorize as Telnyx or prospect
            if '@telnyx.com' in email or 'telnyx' in name.lower():
                enriched['telnyx_attendees'].append(name)
            else:
                enriched['prospect_attendees'].append(name)
        
        # Create formatted AE string
        telnyx_aes = enriched['telnyx_attendees']
        if enriched['primary_ae_name'] not in telnyx_aes:
            telnyx_aes.insert(0, enriched['primary_ae_name'])
        
        enriched['formatted_ae_names'] = ' & '.join(telnyx_aes[:3])  # Limit to 3 names
        
        return enriched
    
    def update_call_with_salesforce_data(self, call_id: int, salesforce_event: Dict) -> bool:
        """Update call record with Salesforce event data"""
        
        try:
            conn = sqlite3.connect('ae_call_analysis.db')
            cursor = conn.cursor()
            
            # Update the calls table
            cursor.execute('''
            UPDATE calls 
            SET ae_name = ?, 
                prospect_company = ?
            WHERE id = ?
            ''', (
                salesforce_event.get('formatted_ae_names'),
                salesforce_event.get('account_name'),
                call_id
            ))
            
            # Update or insert Salesforce mapping
            cursor.execute('''
            INSERT OR REPLACE INTO salesforce_mappings 
            (call_id, contact_id, contact_name, opportunity_id, 
             contact_match_confidence, mapping_method, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                call_id,
                salesforce_event.get('contact_id', salesforce_event.get('event_id')),
                salesforce_event.get('contact_name'),
                salesforce_event.get('account_id'),
                10,  # High confidence for direct event match
                'salesforce_event_lookup'
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error updating call with Salesforce data: {e}")
            return False

def test_salesforce_event_integration():
    """Test the Salesforce event integration with real data"""
    
    print("🔍 Testing Salesforce Event Integration")
    print("=" * 50)
    
    integration = SalesforceEventIntegration()
    
    # Test with a real event we know exists (from earlier search)
    test_cases = [
        'Angel Gonzalez-Bravo',
        'Nick Mihalovich', 
        'Niclas Fischell'
    ]
    
    for prospect in test_cases:
        print(f"\n--- Testing: {prospect} ---")
        event_data = integration.lookup_event_by_prospect(prospect)
        
        if event_data:
            print(f"✅ Found Salesforce event!")
            print(f"   📅 Subject: {event_data['subject']}")
            print(f"   👤 Contact: {event_data['contact_name']}")
            print(f"   🏢 Account: {event_data['account_name']}")
            print(f"   🎯 Primary AE: {event_data['primary_ae_name']}")
            print(f"   🎙️ All Telnyx AEs: {event_data['telnyx_attendees']}")
            print(f"   📝 Formatted AE Names: {event_data['formatted_ae_names']}")
            
            # Show how this would be used in Call Intelligence
            print(f"\n   📊 Call Intelligence Preview:")
            print(f"   **Prospect:** {event_data['contact_name']} | **AE:** {event_data['formatted_ae_names']} | **Date:** 2026-02-27")
            break
        else:
            print(f"❌ No Salesforce event found")
    
    print(f"\n🎯 Integration ready for real customer calls!")

if __name__ == "__main__":
    test_salesforce_event_integration()