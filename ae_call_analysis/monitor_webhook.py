#!/usr/bin/env python3
"""
Real-time webhook monitoring (CLI version for SSH users)
"""

import requests
import json
import time
from datetime import datetime

def monitor_webhook():
    """Monitor webhook activity in real-time"""
    
    print("🔄 REAL-TIME WEBHOOK MONITOR")
    print("=" * 45)
    print("📡 URL: https://ulrike-defensible-crimsonly.ngrok-free.dev/webhook/fellow-call")
    print("⏰ Monitoring... (Press Ctrl+C to stop)")
    print()
    
    last_request_count = 0
    
    while True:
        try:
            # Check ngrok status
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            data = response.json()
            tunnels = data.get('tunnels', [])
            
            if tunnels:
                tunnel = tunnels[0]
                metrics = tunnel.get('metrics', {}).get('http', {})
                current_count = metrics.get('count', 0)
                
                # Check for new requests
                if current_count > last_request_count:
                    new_requests = current_count - last_request_count
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"🔔 {timestamp} - New request(s): {new_requests}")
                    
                    # Get detailed request info
                    req_response = requests.get('http://localhost:4040/api/requests', timeout=5)
                    if req_response.status_code == 200:
                        req_data = req_response.json()
                        requests_list = req_data.get('requests', [])
                        
                        # Show latest request details
                        if requests_list:
                            latest = requests_list[0]
                            req_time = latest.get('started_at', '')[:19].replace('T', ' ')
                            method = latest.get('method', '')
                            uri = latest.get('uri', '')
                            status = latest.get('response', {}).get('status', 0)
                            
                            print(f"   📊 {req_time} | {method} {uri} | Status: {status}")
                            
                            # Show payload and response for webhook calls
                            if '/webhook/fellow-call' in uri:
                                # Request body
                                if latest.get('request', {}).get('body'):
                                    body = latest['request']['body']
                                    try:
                                        payload = json.loads(body)
                                        fellow_id = payload.get('fellow_call_id', 'Unknown')
                                        print(f"   📦 Fellow Event GUID: {fellow_id}")
                                    except:
                                        print(f"   📦 Raw payload: {body}")
                                
                                # Response body
                                if latest.get('response', {}).get('body'):
                                    resp_body = latest['response']['body']
                                    try:
                                        resp_data = json.loads(resp_body)
                                        if resp_data.get('status') == 'accepted':
                                            prospect = resp_data.get('call_prospect', 'Unknown')
                                            print(f"   ✅ Processing started for: {prospect}")
                                            print(f"   🔄 Enhanced pipeline running (2-3 min to Slack)")
                                        else:
                                            print(f"   ❌ Error: {resp_data}")
                                    except:
                                        print(f"   📋 Raw response: {resp_body[:100]}...")
                            print()
                    
                    last_request_count = current_count
                
                # Show periodic status
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\r💓 {current_time} - Monitoring... (Total: {current_count} requests)", end='', flush=True)
            else:
                print("\r❌ ngrok tunnel down", end='', flush=True)
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped")
            break
        except Exception as e:
            print(f"\n❌ Monitor error: {str(e)}")
            time.sleep(5)

if __name__ == '__main__':
    monitor_webhook()