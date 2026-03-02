#!/usr/bin/env python3
"""
Debug capture - logs exactly what Zapier sends
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/webhook/fellow-call', methods=['POST'])
def capture_zapier():
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    print(f"\n🔔 ZAPIER DEBUG CAPTURE - {timestamp}")
    print("=" * 60)
    
    try:
        # Get raw body
        raw_body = request.get_data(as_text=True)
        print(f"📦 RAW BODY: {raw_body}")
        
        # Parse JSON
        json_data = request.get_json()
        print(f"📋 JSON DATA: {json.dumps(json_data, indent=2)}")
        
        # Extract Fellow Event GUID
        fellow_id = json_data.get('fellow_call_id') if json_data else None
        print(f"🆔 FELLOW EVENT GUID: {fellow_id}")
        print(f"📏 LENGTH: {len(fellow_id) if fellow_id else 0}")
        
        # Return success so Zapier thinks it worked
        return jsonify({
            "status": "debug_captured", 
            "fellow_call_id": fellow_id,
            "timestamp": timestamp
        })
        
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🔍 DEBUG CAPTURE MODE")
    print("=" * 30)
    print("📡 Capturing what Zapier sends...")
    app.run(host='0.0.0.0', port=5003, debug=True)