#!/usr/bin/env python3
"""
Debug webhook processing for event_guid
"""

import requests
import json
import os
from webhook_receiver import fetch_fellow_call_data, extract_call_data

def debug_fellow_api():
    """Debug the Fellow API call directly"""
    
    api_key = os.getenv('FELLOW_API_KEY')
    target_id = 'teaiqr3s1fn97qtvf8u6ja7878'
    
    print('🔍 DEBUGGING FELLOW API CALL')
    print('=' * 40)
    
    # Set environment variable
    os.environ['FELLOW_API_KEY'] = api_key
    
    try:
        print(f'📞 Testing Fellow API with event GUID: {target_id}')
        
        # Test direct API call
        headers = {'X-Api-Key': api_key}
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            headers=headers,
            json={'filters': {'event_guid': target_id}}
        )
        
        print(f'📊 API Response Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            recordings = data.get('recordings', {}).get('data', [])
            
            print(f'📈 Recordings found: {len(recordings)}')
            
            if recordings:
                recording = recordings[0]
                print('✅ Found recording:')
                print(f'   📞 ID: {recording.get("id", "N/A")}')
                print(f'   🆔 Event GUID: {recording.get("event_guid", "N/A")}')
                print(f'   📝 Title: {recording.get("title", "N/A")}')
                print()
                
                # Test webhook function
                print('🔧 Testing webhook function...')
                
                try:
                    call_data = fetch_fellow_call_data(target_id)
                    print('✅ fetch_fellow_call_data SUCCESS!')
                    print(f'📋 Call data: {json.dumps(call_data, indent=2)}')
                    
                    # Test extract function
                    payload = {'fellow_call_id': target_id}
                    extracted = extract_call_data(payload)
                    
                    if extracted:
                        print('✅ extract_call_data SUCCESS!')
                        print(f'📋 Extracted: {json.dumps(extracted, indent=2)}')
                    else:
                        print('❌ extract_call_data FAILED!')
                        
                except Exception as e:
                    print(f'❌ Webhook function error: {str(e)}')
                    import traceback
                    traceback.print_exc()
            else:
                print('❌ No recordings found')
        else:
            print(f'❌ API Error: {response.text[:200]}')
            
    except Exception as e:
        print(f'❌ Debug error: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_fellow_api()