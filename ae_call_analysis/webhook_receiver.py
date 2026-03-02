#!/usr/bin/env python3
"""
Real-time Call Intelligence Webhook Receiver
Receives Zapier webhook → Processes through enhanced pipeline → Slack alert
"""

from flask import Flask, request, jsonify
import asyncio
import json
from datetime import datetime
import threading
from enhanced_call_processor import EnhancedCallProcessor

app = Flask(__name__)
processor = EnhancedCallProcessor()

@app.route('/webhook/fellow-call', methods=['POST'])
def receive_fellow_call():
    """Receive Fellow call data from Zapier webhook"""
    
    try:
        # Log the incoming webhook
        print(f"🔔 Webhook received at {datetime.now()}")
        
        # Get the payload from Zapier
        payload = request.get_json()
        
        if not payload:
            return jsonify({'error': 'No JSON payload received'}), 400
        
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        # Debug: Log the exact Fellow Event GUID Zapier sent
        fellow_id = payload.get('fellow_call_id') if payload else None
        print(f"🆔 ZAPIER SENT EVENT GUID: {fellow_id}")
        print(f"📏 EVENT GUID LENGTH: {len(fellow_id) if fellow_id else 0}")
        
        # Extract Fellow call data (format depends on Zapier setup)
        call_data = extract_call_data(payload)
        
        if not call_data:
            return jsonify({'error': 'Could not extract call data from payload'}), 400
        
        # Process the call asynchronously (don't block webhook response)
        thread = threading.Thread(
            target=process_call_async, 
            args=(call_data,)
        )
        thread.start()
        
        # Return immediate success to Zapier
        return jsonify({
            'status': 'accepted',
            'message': 'Call processing started',
            'call_prospect': call_data.get('prospect_name', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def extract_call_data(payload):
    """Extract call data from Zapier payload (Fellow call ID approach)"""
    
    # Get Fellow call ID from payload
    fellow_call_id = None
    
    # Try different payload formats
    if 'fellow_call_id' in payload:
        fellow_call_id = payload['fellow_call_id']
    elif 'call_id' in payload:
        fellow_call_id = payload['call_id']
    elif 'id' in payload:
        fellow_call_id = payload['id']
    
    if not fellow_call_id:
        return None
    
    # Fetch full call data from Fellow API
    try:
        call_data = fetch_fellow_call_data(fellow_call_id)
        return call_data
    except Exception as e:
        print(f"❌ Failed to fetch Fellow call data for ID {fellow_call_id}: {str(e)}")
        return None

def fetch_fellow_call_data(call_id):
    """Fetch complete call data from Fellow API (Telnyx format)"""
    
    import requests
    import os
    
    # Get Fellow API credentials
    fellow_api_key = os.getenv('FELLOW_API_KEY')
    
    if not fellow_api_key:
        raise Exception("FELLOW_API_KEY environment variable not set")
    
    # Use Telnyx Fellow API format (X-Api-Key header)
    headers = {'X-Api-Key': fellow_api_key}
    
    print(f"📡 Fetching Fellow call data for ID: {call_id}")
    
    # Search Fellow API for event_guid (filters don't work, must search manually)
    # Try multiple pages to find older recordings
    max_pages = 5  # Search up to 100 recordings (5 pages * ~20 each)
    found_recording = None
    
    for page in range(max_pages):
        page_params = {"page": page + 1} if page > 0 else {}
        
        response = requests.post(
            'https://telnyx.fellow.app/api/v1/recordings',
            headers=headers,
            json=page_params
        )
        
        if response.status_code != 200:
            raise Exception(f"Fellow API error: {response.status_code} - {response.text}")
        
        data = response.json()
        recordings = data.get('recordings', {}).get('data', [])
        
        if not recordings:  # No more recordings
            break
        
        print(f"📄 Searching page {page + 1}: {len(recordings)} recordings")
        
        # Find the recording by event_guid in this page
        for recording in recordings:
            if recording.get('event_guid') == call_id:
                found_recording = recording
                print(f"✅ Found Event GUID on page {page + 1}")
                break
        
        if found_recording:
            break
    
    if found_recording:
            print(f"✅ Found Fellow call: {found_recording.get('title', 'N/A')}")
            
            # Extract the data we need
            return {
                'fellow_call_id': call_id,
                'prospect_name': extract_prospect_name(found_recording.get('title', '')),
                'title': found_recording.get('title', ''),
                'transcript': found_recording.get('transcript', ''),
                'call_date': found_recording.get('created_at'),
                'participants': found_recording.get('attendees', [])
            }
    
    # Event GUID not found after searching multiple pages
    raise Exception(f"Event GUID {call_id} not found in Fellow recordings (searched {max_pages} pages). May be very old or invalid.")

def extract_prospect_name(title):
    """Extract prospect name from Fellow call title"""
    
    # Format: "Telnyx Intro Call (Prospect Name)"
    if 'Telnyx Intro Call (' in title:
        start = title.find('(') + 1
        end = title.find(')')
        if start > 0 and end > start:
            return title[start:end]
    
    return 'Unknown Prospect'

def process_call_async(call_data):
    """Process call through enhanced pipeline (async to not block webhook)"""
    
    try:
        print(f"🚀 Starting enhanced processing for: {call_data['prospect_name']}")
        
        # Step 1: Store call in database (if not already there)
        call_id = store_call_if_new(call_data)
        
        if call_id is None:
            print("ℹ️  Call already processed, skipping")
            return
        
        # Step 2: Run through enhanced processing pipeline
        result = processor.process_call_with_salesforce_lookup(call_id)
        
        if result['success']:
            print(f"✅ Enhanced processing complete for Call ID {call_id}")
            
            # Step 3: Deploy to Slack (using existing deployment)
            deploy_to_slack(result['message'], call_data['prospect_name'])
            
        else:
            print(f"❌ Processing failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Async processing error: {str(e)}")

def store_call_if_new(call_data):
    """Store call in database if it's new, return call_id or None if duplicate"""
    
    import sqlite3
    from pathlib import Path
    
    # Fix database path - make sure it's absolute
    db_path = Path(__file__).parent / 'ae_call_analysis.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if call already exists (use fellow_id for better duplicate detection)
    cursor.execute('''
    SELECT id FROM calls 
    WHERE fellow_id = ? OR (prospect_name = ? AND title = ?)
    ''', (call_data['fellow_call_id'], call_data['prospect_name'], call_data['title']))
    
    existing = cursor.fetchone()
    
    if existing:
        conn.close()
        return None  # Already processed
    
    # Store new call (fix NOT NULL constraint for fellow_id)
    cursor.execute('''
    INSERT INTO calls (
        fellow_id, prospect_name, title, call_date, 
        ae_name, prospect_company, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        call_data['fellow_call_id'],  # Add fellow_id to fix NOT NULL constraint
        call_data['prospect_name'],
        call_data['title'],
        call_data['call_date'],
        extract_ae_name(call_data),
        extract_company(call_data),
        datetime.now().isoformat()
    ))
    
    call_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"💾 Stored new call ID {call_id}: {call_data['prospect_name']}")
    return call_id

def extract_ae_name(call_data):
    """Extract AE name from call data"""
    participants = call_data.get('participants', [])
    # Look for Telnyx employees in participants
    for participant in participants:
        if '@telnyx.com' in str(participant):
            return participant
    return 'Unknown AE'

def extract_company(call_data):
    """Extract company name from call title"""
    title = call_data.get('title', '')
    if 'Telnyx Intro Call (' in title:
        # Extract company from "Telnyx Intro Call (Company Name)"
        start = title.find('(') + 1
        end = title.find(')')
        if start > 0 and end > start:
            return title[start:end]
    return 'Unknown Company'

def deploy_to_slack(message, prospect_name):
    """Deploy enhanced message to Slack"""
    
    try:
        # Use existing Slack deployment (adjust as needed)
        import subprocess
        
        # Save message to temp file
        with open('temp_webhook_message.txt', 'w') as f:
            f.write(message)
        
        # Deploy to #bot-testing
        result = subprocess.run([
            'python3', 'ae_call_analysis/deploy_slack_phase3.py',
            '--message-file', 'temp_webhook_message.txt',
            '--prospect', prospect_name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Slack alert deployed for {prospect_name}")
        else:
            print(f"⚠️  Slack deployment warning: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Slack deployment error: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Fellow Call Intelligence Webhook'
    })

@app.route('/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for development"""
    
    # Sample test payload
    test_payload = {
        'fellow_call_id': 'test_' + str(int(datetime.now().timestamp())),
        'prospect_name': 'Test Prospect',
        'title': 'Telnyx Intro Call (Test Company)',
        'transcript': 'This is a test call transcript.',
        'call_date': datetime.now().isoformat(),
        'participants': ['test.ae@telnyx.com', 'prospect@testcompany.com']
    }
    
    # Process test call
    thread = threading.Thread(
        target=process_call_async, 
        args=(test_payload,)
    )
    thread.start()
    
    return jsonify({
        'status': 'test_started',
        'test_data': test_payload
    })

if __name__ == '__main__':
    print("🚀 Starting Fellow Call Intelligence Webhook Receiver")
    print("📡 Listening for Zapier webhooks...")
    print("🎯 Endpoint: /webhook/fellow-call")
    print("💊 Health check: /health")
    print("🧪 Test endpoint: /test")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5001, debug=True)