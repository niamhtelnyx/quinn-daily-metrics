#!/usr/bin/env python3
"""
Debug Salesforce events to understand the actual subject patterns
"""

import requests
import os

def load_env():
    """Load environment variables"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_salesforce_token():
    """Get Salesforce OAuth2 access token"""
    client_id = os.getenv('SF_CLIENT_ID')
    client_secret = os.getenv('SF_CLIENT_SECRET')
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    
    if not client_id or not client_secret:
        return None, "Salesforce credentials missing"
    
    try:
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=auth_data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token'), "✅ Salesforce authenticated"
        else:
            return None, f"❌ Salesforce auth failed: {response.status_code}"
            
    except Exception as e:
        return None, f"❌ Salesforce error: {e}"

def debug_recent_events(access_token):
    """Debug recent events to see actual subject patterns"""
    
    if not access_token:
        return
    
    try:
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        search_url = f"https://{domain}.my.salesforce.com/services/data/v57.0/query"
        
        # Get recent events with various patterns
        queries = [
            # Recent events containing key prospect identifiers
            "SELECT Id, Subject, StartDateTime FROM Event WHERE Subject LIKE '%roly%' AND StartDateTime >= LAST_N_DAYS:60 ORDER BY StartDateTime DESC LIMIT 5",
            "SELECT Id, Subject, StartDateTime FROM Event WHERE Subject LIKE '%meetgail%' AND StartDateTime >= LAST_N_DAYS:60 ORDER BY StartDateTime DESC LIMIT 5",
            "SELECT Id, Subject, StartDateTime FROM Event WHERE Subject LIKE '%sruthi%' AND StartDateTime >= LAST_N_DAYS:60 ORDER BY StartDateTime DESC LIMIT 5", 
            "SELECT Id, Subject, StartDateTime FROM Event WHERE Subject LIKE '%eltropy%' AND StartDateTime >= LAST_N_DAYS:60 ORDER BY StartDateTime DESC LIMIT 5",
            # Recent events with "Meeting" in subject
            "SELECT Id, Subject, StartDateTime FROM Event WHERE Subject LIKE '%Meeting%' AND StartDateTime >= LAST_N_DAYS:7 ORDER BY StartDateTime DESC LIMIT 10",
            # All recent events
            "SELECT Id, Subject, StartDateTime FROM Event WHERE StartDateTime >= LAST_N_DAYS:7 ORDER BY StartDateTime DESC LIMIT 15"
        ]
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        all_events = []
        
        for i, query in enumerate(queries):
            print(f"\n🔍 Query {i+1}: {query.split('WHERE')[1].split('ORDER')[0].strip()}")
            
            response = requests.get(search_url, params={'q': query}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('records', [])
                
                if events:
                    for event in events:
                        event_info = (event['Id'], event['Subject'], event['StartDateTime'])
                        if event_info not in all_events:  # Avoid duplicates
                            all_events.append(event_info)
                            print(f"   📅 {event['StartDateTime'][:10]} | {event['Subject']}")
                else:
                    print(f"   (no events found)")
            else:
                print(f"   ❌ Query failed: {response.status_code}")
        
        print(f"\n📊 Total unique events found: {len(all_events)}")
        
    except Exception as e:
        print(f"Error debugging events: {e}")

def main():
    """Debug Salesforce events"""
    print("🔍 Debugging Salesforce Events - Finding Actual Subject Patterns")
    print("=" * 70)
    
    load_env()
    
    # Get Salesforce token
    access_token, auth_msg = get_salesforce_token()
    print(f"🏢 Salesforce: {auth_msg}")
    
    if access_token:
        debug_recent_events(access_token)
    else:
        print("❌ Cannot debug events without Salesforce access")

if __name__ == "__main__":
    main()