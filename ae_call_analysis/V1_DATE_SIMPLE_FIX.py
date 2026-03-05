#!/usr/bin/env python3
"""
V1 Simple Fix - Handle the one known mismatch
Quick fix for the Morgan/Andrea Aliyana meeting
"""

import os
import sys
from V1_DATE_FULL import *

def find_salesforce_event_simple_fix(access_token, event_name):
    """Simple fix with known name mappings"""
    
    # Known mismatches - map Google Drive names to Salesforce names
    name_mappings = {
        "Morgan & Aliyana -- Telnyx": "Andrea & Aliyana <> replacing twilio",
        "Aliyana": "Andrea & Aliyana <> replacing twilio",  # Partial match
    }
    
    # Try exact match first (original logic)
    exact_subject = f"Meeting Booked: {event_name}"
    escaped_subject = exact_subject.replace("'", "\\'")
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        instance_url = f"https://{domain}.my.salesforce.com"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        query_exact = f"""
        SELECT Id, Subject, WhoId, StartDateTime, EndDateTime 
        FROM Event 
        WHERE Subject = '{escaped_subject}'
        ORDER BY CreatedDate DESC 
        LIMIT 1
        """
        
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': query_exact},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            if results['records']:
                log_message(f"✅ EXACT match found: {results['records'][0]['Subject']}", False)
                return results['records'][0]
        
        # Try known mappings
        for google_name, sf_name in name_mappings.items():
            if google_name.lower() in event_name.lower():
                mapped_subject = f"Meeting Booked: {sf_name}"
                escaped_mapped = mapped_subject.replace("'", "\\'")
                
                query_mapped = f"""
                SELECT Id, Subject, WhoId, StartDateTime, EndDateTime 
                FROM Event 
                WHERE Subject = '{escaped_mapped}'
                ORDER BY CreatedDate DESC 
                LIMIT 1
                """
                
                log_message(f"🔧 Trying mapped name: {google_name} → {sf_name}", False)
                
                response = requests.get(
                    f"{instance_url}/services/data/v57.0/query",
                    params={'q': query_mapped},
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if results['records']:
                        log_message(f"✅ MAPPED match found: {results['records'][0]['Subject']}", False)
                        return results['records'][0]
        
        # Try partial name search for Aliyana
        if "aliyana" in event_name.lower():
            query_aliyana = f"""
            SELECT Id, Subject, WhoId, StartDateTime, EndDateTime 
            FROM Event 
            WHERE Subject LIKE 'Meeting Booked:%Aliyana%'
            AND CreatedDate >= YESTERDAY
            ORDER BY CreatedDate DESC 
            LIMIT 1
            """
            
            log_message(f"🔍 Searching for Aliyana meetings...", False)
            
            response = requests.get(
                f"{instance_url}/services/data/v57.0/query",
                params={'q': query_aliyana},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                if results['records']:
                    log_message(f"✅ ALIYANA match found: {results['records'][0]['Subject']}", False)
                    return results['records'][0]
        
        log_message(f"❌ No matches found for: {event_name}", False)
        return None
        
    except requests.exceptions.Timeout:
        log_message(f"⏰ Salesforce event query timeout for: {event_name}", False)
        return None
    except Exception as e:
        log_message(f"❌ Salesforce event query error: {str(e)}", False)
        return None

# Override the function in the existing system
import V1_DATE_FULL
V1_DATE_FULL.find_salesforce_event_by_exact_subject = find_salesforce_event_simple_fix

if __name__ == "__main__":
    process_date_hierarchy_full(days_back=1, max_meetings_per_day=5)