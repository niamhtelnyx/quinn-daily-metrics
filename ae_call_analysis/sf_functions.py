#!/usr/bin/env python3
"""
Salesforce integration functions
"""

import os
import requests
from dotenv import load_dotenv
from config import *

def get_salesforce_token():
    """Get Salesforce authentication token"""
    load_dotenv()
    
    client_id = os.getenv('SALESFORCE_CLIENT_ID')
    client_secret = os.getenv('SALESFORCE_CLIENT_SECRET') 
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    
    if not all([client_id, client_secret, username, password]):
        print("⚠️ Missing Salesforce credentials")
        return None
    
    try:
        data = {
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'password': password
        }
        
        response = requests.post(
            SALESFORCE_LOGIN_URL,
            data=data,
            timeout=SALESFORCE_TIMEOUT
        )
        
        if response.status_code == 200:
            print("🔑 Salesforce token obtained")
            return response.json()
        else:
            print(f"❌ Salesforce auth failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Salesforce auth error: {str(e)[:100]}")
        return None

def find_salesforce_event(event_name, access_token, instance_url):
    """Find Salesforce event by name"""
    if not access_token or not instance_url:
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try exact match first
    exact_query = f"Meeting Booked: {event_name}"
    soql = f"SELECT Id, Subject, WhoId, WhatId, OwnerId FROM Event WHERE Subject = '{exact_query}' LIMIT 1"
    
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
                print(f"        🎯 Salesforce: Found event")
                return result['records'][0]
        
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