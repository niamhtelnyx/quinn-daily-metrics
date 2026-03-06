#!/usr/bin/env python3
"""
Salesforce integration functions
"""

import os
import requests
from dotenv import load_dotenv
from config import *
import re

def normalize_meeting_name(meeting_name):
    """Normalize meeting name to match Salesforce Subject_Normalized__c field
    Based on actual Salesforce examples:
    - Convert to uppercase
    - Remove ALL special characters and spaces
    - Keep only letters and numbers
    """
    if not meeting_name:
        return ""
    
    # Convert to uppercase
    normalized = meeting_name.upper()
    
    # Remove ALL characters except letters and numbers (matching Salesforce logic)
    # This removes spaces, special characters, punctuation, etc.
    normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    
    print(f"        🔄 Normalized: '{meeting_name}' → '{normalized}'")
    return normalized

def get_salesforce_token():
    """Get Salesforce authentication token - USING WORKING METHOD"""
    load_dotenv()
    
    client_id = os.getenv('SALESFORCE_CLIENT_ID')
    client_secret = os.getenv('SALESFORCE_CLIENT_SECRET') 
    
    if not all([client_id, client_secret]):
        print("⚠️ Missing Salesforce credentials")
        return None
    
    try:
        # USE CLIENT_CREDENTIALS GRANT TYPE (working approach)
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        # USE TELNYX INSTANCE URL (working approach)
        response = requests.post(
            "https://telnyx.my.salesforce.com/services/oauth2/token",
            data=data,
            timeout=SALESFORCE_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            print("🔑 Salesforce token obtained")
            return {
                'access_token': result['access_token'],
                'instance_url': result.get('instance_url', 'https://telnyx.my.salesforce.com')
            }
        else:
            print(f"❌ Salesforce auth failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Salesforce auth error: {str(e)[:100]}")
        return None

def find_salesforce_event(event_name, access_token, instance_url):
    """Find Salesforce event by name using normalized field"""
    if not access_token or not instance_url:
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Normalize the meeting name to match Salesforce formula field
    normalized_name = normalize_meeting_name(event_name)
    normalized_query = f"MEETINGBOOKED{normalized_name}"
    
    # Search using Subject_Normalized__c field for better matching
    soql = f"SELECT Id, Subject, Subject_Normalized__c, WhoId, WhatId, OwnerId FROM Event WHERE Subject_Normalized__c = '{normalized_query}' LIMIT 1"
    
    print(f"        🔍 Searching for: '{normalized_query}'")
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': soql},
            headers=headers,
            timeout=SALESFORCE_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                event = result['records'][0]
                print(f"        🎯 Salesforce: Found event (Subject: '{event.get('Subject', 'Unknown')}')")
                return event
            else:
                print(f"        ❌ No normalized match found")
                
                # Fallback: Try original exact match for backwards compatibility
                print(f"        🔄 Trying fallback search...")
                fallback_query = f"Meeting Booked: {event_name}"
                fallback_soql = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject = '{fallback_query}' LIMIT 1"
                
                fallback_response = requests.get(
                    f"{instance_url}/services/data/v59.0/query",
                    params={'q': fallback_soql},
                    headers=headers,
                    timeout=SALESFORCE_TIMEOUT
                )
                
                if fallback_response.status_code == 200:
                    fallback_result = fallback_response.json()
                    if fallback_result['totalSize'] > 0:
                        print(f"        🎯 Salesforce: Found via fallback")
                        return fallback_result['records'][0]
        
    except Exception as e:
        print(f"        ⚠️ Salesforce lookup failed: {str(e)[:50]}")
    
    return None

def get_contact_from_salesforce(event_record, access_token, instance_url):
    """Get contact details from Salesforce event"""
    if not event_record or not event_record.get('WhoId'):
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        contact_query = f"SELECT Id, Name, Email, Account.Name FROM Contact WHERE Id = '{event_record['WhoId']}' LIMIT 1"
        
        response = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={'q': contact_query},
            headers=headers,
            timeout=SALESFORCE_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['totalSize'] > 0:
                return result['records'][0]
                
    except Exception as e:
        print(f"        ⚠️ Salesforce contact lookup failed: {str(e)[:50]}")
    
    return None

def build_salesforce_links(event_record):
    """Build Salesforce links for Slack message"""
    if not event_record:
        return "❌ No Salesforce Match"
    
    links = []
    
    contact_id = event_record.get('WhoId', '')
    account_id = event_record.get('WhatId', '')
    event_id = event_record.get('Id', '')
    
    if contact_id:
        links.append(f"<{SALESFORCE_BASE_URL}/Contact/{contact_id}/view|Contact>")
    if account_id:
        links.append(f"<{SALESFORCE_BASE_URL}/Account/{account_id}/view|Account>")
    if event_id:
        links.append(f"<{SALESFORCE_BASE_URL}/Event/{event_id}/view|Event>")
    
    if links:
        return " | ".join(links)
    else:
        return "❌ No Salesforce Match"

def lookup_salesforce_info(meeting_name):
    """Main function to lookup Salesforce information for a meeting"""
    # Get Salesforce token
    sf_token_data = get_salesforce_token()
    if not sf_token_data:
        return None, "❌ No Salesforce Match"
    
    access_token = sf_token_data['access_token']
    instance_url = sf_token_data['instance_url']
    
    # Find event
    event_record = find_salesforce_event(meeting_name, access_token, instance_url)
    if not event_record:
        return None, "❌ No Salesforce Match"
    
    # Get contact details
    contact_info = get_contact_from_salesforce(event_record, access_token, instance_url)
    
    # Build links
    salesforce_links = build_salesforce_links(event_record)
    
    return {
        'event_record': event_record,
        'contact_info': contact_info,
        'salesforce_links': salesforce_links
    }, salesforce_links