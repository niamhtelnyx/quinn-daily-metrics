#!/usr/bin/env python3
"""
FIXED Fellow Cron Job - Working by 1 PM
Fellow → Salesforce (OAuth2) → Generate Alert → Post to Slack
"""

import requests
import sqlite3
import json
import os
from datetime import datetime
from fixed_salesforce_oauth2_integration import FixedSalesforceEventIntegration
from oauth2_salesforce_event_updater import OAuth2SalesforceEventUpdater
from refined_message_format import generate_refined_call_alert

def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file()

def post_to_slack_via_clawdbot(message):
    """Post to Slack using Clawdbot gateway API"""
    try:
        # Try Clawdbot gateway first
        gateway_url = "http://localhost:18789"
        auth_token = "ceb83b64e8061a9544bfac74db0eea9cefe2e5d46d5323f2"
        
        payload = {
            "action": "send",
            "channel": "slack", 
            "target": "C38URQASH",  # bot-testing channel
            "message": message
        }
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{gateway_url}/message",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Posted to Slack via Clawdbot")
            return True
            
    except Exception as e:
        print(f"⚠️  Clawdbot posting failed: {e}")
    
    # Fallback: Save to file
    timestamp = datetime.now().strftime('%H%M%S')
    filename = f"slack_alert_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write(message)
    print(f"💾 Alert saved to {filename} for manual posting")
    return False

def process_analyzed_calls():
    """Process calls that have been analyzed"""
    
    print("🚀 FIXED CRON JOB - Call Intelligence Processing")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    conn = sqlite3.connect('ae_call_analysis.db')
    cursor = conn.cursor()
    
    # Get analyzed calls that haven't been processed yet
    cursor.execute('''
    SELECT id, prospect_name, ae_name, call_date, title, prospect_company,
           analysis_confidence, prospect_interest_level, ae_excitement_level,
           quinn_qualification_quality, core_talking_points, use_cases,
           prospect_buying_signals, next_steps_actions, conversation_style
    FROM calls 
    WHERE analysis_confidence IS NOT NULL
    AND (processed_by_enhanced IS NULL OR processed_by_enhanced = 0)
    AND prospect_name IS NOT NULL
    LIMIT 5
    ''')
    
    analyzed_calls = cursor.fetchall()
    
    if not analyzed_calls:
        print("📋 No analyzed calls ready for processing")
        # Check if any calls are being analyzed
        cursor.execute('''
        SELECT COUNT(*) FROM calls 
        WHERE analysis_confidence IS NULL AND prospect_name IS NOT NULL
        ''')
        pending_count = cursor.fetchone()[0]
        print(f"⏳ {pending_count} calls pending analysis")
        conn.close()
        return
    
    print(f"📞 Found {len(analyzed_calls)} analyzed calls to process")
    
    sf_integration = FixedSalesforceEventIntegration()
    sf_updater = OAuth2SalesforceEventUpdater()
    processed_count = 0
    
    for call_row in analyzed_calls:
        call_id = call_row[0]
        prospect_name = call_row[1]
        
        try:
            print(f"\n🔄 Processing Call {call_id}: {prospect_name}")
            
            # Build call data
            call_data = {
                'id': call_id,
                'prospect_name': call_row[1],
                'ae_name': call_row[2],
                'call_date': call_row[3],
                'title': call_row[4],
                'prospect_company': call_row[5]
            }
            
            # Build analysis data
            analysis_data = {
                'analysis_confidence': call_row[6],
                'prospect_interest_level': call_row[7],
                'ae_excitement_level': call_row[8],
                'quinn_qualification_quality': call_row[9],
                'core_talking_points': json.loads(call_row[10]) if call_row[10] else [],
                'use_cases': json.loads(call_row[11]) if call_row[11] else [],
                'prospect_buying_signals': json.loads(call_row[12]) if call_row[12] else [],
                'next_steps_actions': json.loads(call_row[13]) if call_row[13] else [],
                'conversation_style': call_row[14]
            }
            
            # Salesforce lookup (working OAuth2)
            print("🔍 Salesforce lookup...")
            sf_event = sf_integration.lookup_event_by_prospect(
                prospect_name, call_data['call_date']
            )
            
            if sf_event:
                print(f"✅ Found SF event: {sf_event['formatted_ae_names']}")
                # Update call data with real SF info
                call_data['ae_name'] = sf_event['formatted_ae_names']
                call_data['prospect_company'] = sf_event['account_name']
                
                # Update database with SF data
                cursor.execute('''
                UPDATE calls SET ae_name = ?, prospect_company = ?
                WHERE id = ?
                ''', (sf_event['formatted_ae_names'], sf_event['account_name'], call_id))
                
                # Update Salesforce Event with call intelligence
                print("📝 Updating Salesforce Event...")
                try:
                    update_result = sf_updater.update_event_with_intelligence(
                        sf_event['event_id'], analysis_data, call_data
                    )
                    if update_result['success']:
                        print(f"✅ SF Event {sf_event['event_id']} updated")
                    else:
                        print(f"⚠️  SF Event update failed: {update_result['error']}")
                except Exception as e:
                    print(f"⚠️  SF Event update error: {e}")
                
            else:
                print("⚠️  No SF event found - using Fellow data")
            
            # Generate alert message
            print("📝 Generating alert...")
            message = generate_refined_call_alert(call_data, analysis_data)
            
            if sf_event:
                # Add Salesforce validation section
                sf_validation = f"""

**🔗 SALESFORCE EVENT VALIDATION:**
• **Event ID**: {sf_event.get('event_id', 'N/A')}
• **AE**: {sf_event.get('formatted_ae_names', 'N/A')}
• **Contact**: {sf_event.get('contact_name', 'N/A')}
• **Account**: {sf_event.get('account_name', 'N/A')}
• **Event Date**: {sf_event.get('start_datetime', 'N/A')}

_✅ Data validated via Salesforce OAuth2 integration_"""
                message += sf_validation
            
            # Post to Slack
            print("📮 Posting to Slack...")
            slack_success = post_to_slack_via_clawdbot(message)
            
            # Mark as processed
            cursor.execute('''
            UPDATE calls SET processed_by_enhanced = 1 WHERE id = ?
            ''', (call_id,))
            
            processed_count += 1
            
            status = "✅ SUCCESS" if slack_success else "⚠️  SAVED TO FILE"
            print(f"{status} - Call {call_id} processed")
            
        except Exception as e:
            print(f"❌ Failed to process call {call_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 PROCESSING COMPLETE: {processed_count}/{len(analyzed_calls)} calls")
    
    if processed_count > 0:
        print("✅ Call Intelligence alerts generated!")
        print("📮 Check #bot-testing Slack channel for results")
    
    print("=" * 60)

if __name__ == "__main__":
    process_analyzed_calls()