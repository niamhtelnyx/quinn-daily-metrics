#!/usr/bin/env python3
"""
Debug Zapier payload capture
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/webhook/fellow-call', methods=['POST'])
def debug_zapier_webhook():
    """Capture and log exactly what Zapier sends"""
    
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    print(f"\n🔔 ZAPIER WEBHOOK RECEIVED - {timestamp}")
    print("=" * 50)
    
    try:
        # Log all request details
        print(f"📊 Method: {request.method}")
        print(f"📡 URL: {request.url}")
        print(f"🌐 Remote IP: {request.remote_addr}")
        print(f"📋 Headers:")
        for key, value in request.headers:
            print(f"   {key}: {value}")
        
        # Get raw body
        raw_body = request.get_data(as_text=True)
        print(f"📦 Raw Body: {raw_body}")
        
        # Try to parse JSON
        try:
            json_payload = request.get_json()
            print(f"📋 JSON Payload: {json.dumps(json_payload, indent=2)}")
            
            # Extract Fellow Event GUID
            fellow_id = json_payload.get('fellow_call_id') if json_payload else None
            if fellow_id:
                print(f"🆔 Fellow Event GUID: {fellow_id}")
                print(f"📏 GUID Length: {len(fellow_id)}")
                print(f"🔤 GUID Format: {type(fellow_id)}")
            else:
                print("❌ No 'fellow_call_id' found in payload")
                
        except Exception as e:
            print(f"❌ JSON Parse Error: {str(e)}")
        
        # Return success response
        response = {
            "status": "debug_received",
            "message": f"Zapier payload logged at {timestamp}",
            "fellow_call_id": fellow_id if fellow_id else "not_found",
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📤 Sending Response: {json.dumps(response, indent=2)}")
        print("=" * 50)
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response = {"error": f"Debug capture failed: {str(e)}"}
        print(f"💥 Debug Error: {error_response}")
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "debug_mode", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("🔍 ZAPIER DEBUG MODE - CAPTURING PAYLOADS")
    print("=" * 50)
    print("📡 This will capture exactly what Zapier sends")
    print("🎯 Listening on: http://localhost:5002/webhook/fellow-call")
    print("💡 Use this URL in Zapier temporarily")
    print()
    
    app.run(host='0.0.0.0', port=5002, debug=True)