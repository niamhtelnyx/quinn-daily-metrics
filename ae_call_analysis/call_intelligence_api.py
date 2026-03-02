#!/usr/bin/env python3
"""
Call Intelligence API - FastAPI orchestrator
Simplified approach: One endpoint triggers full pipeline
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import sqlite3
import asyncio
from datetime import datetime
import os
from typing import Optional

app = FastAPI(title="Call Intelligence API", version="1.0.0")

class CallRequest(BaseModel):
    fellow_call_id: str

class CallResponse(BaseModel):
    status: str
    message: str
    call_id: Optional[int] = None
    prospect_name: Optional[str] = None
    processing_time: Optional[str] = None

# Configuration
FELLOW_API_KEY = os.getenv('FELLOW_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

class CallIntelligenceOrchestrator:
    def __init__(self):
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect('ae_call_analysis.db')
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fellow_id TEXT,
            prospect_name TEXT,
            ae_name TEXT,
            title TEXT,
            call_date TEXT,
            prospect_company TEXT,
            created_at TEXT,
            transcript TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id INTEGER,
            prospect_interest_level TEXT,
            ae_excitement_level TEXT,
            analysis_confidence REAL,
            strategic_insights TEXT,
            company_intelligence TEXT,
            salesforce_event_data TEXT,
            created_at TEXT,
            FOREIGN KEY (call_id) REFERENCES calls (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_fellow_call_data(self, event_guid: str) -> dict:
        """Fetch call data from Fellow API"""
        print(f"🔍 Fetching Fellow call: {event_guid}")
        
        headers = {
            'Authorization': f'Bearer {FELLOW_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Search multiple pages for the event_guid
        for page in range(1, 6):  # Search up to 5 pages
            params = {"page": page} if page > 1 else {}
            
            response = requests.post(
                'https://telnyx.fellow.app/api/v1/recordings',
                headers=headers,
                json=params
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Fellow API error: {response.status_code}")
            
            data = response.json()
            recordings = data.get('recordings', {}).get('data', [])
            
            print(f"📄 Searching page {page}: {len(recordings)} recordings")
            
            for recording in recordings:
                if recording.get('event_guid') == event_guid:
                    print(f"✅ Found call: {recording.get('title', 'N/A')}")
                    return {
                        'fellow_id': event_guid,
                        'title': recording.get('title', ''),
                        'transcript': recording.get('transcript', ''),
                        'call_date': recording.get('created_at'),
                        'participants': recording.get('attendees', []),
                        'prospect_name': self.extract_prospect_name(recording.get('title', ''))
                    }
            
            if not recordings:  # No more pages
                break
        
        raise HTTPException(status_code=404, detail=f"Fellow call {event_guid} not found")
    
    def extract_prospect_name(self, title: str) -> str:
        """Extract prospect name from call title"""
        # Simple extraction - look for patterns like "Name (Company)" or "Company - Name"
        if '(' in title and ')' in title:
            # Extract name before parentheses
            return title.split('(')[0].strip()
        elif ' - ' in title:
            # Extract name after dash
            parts = title.split(' - ')
            return parts[-1].strip() if len(parts) > 1 else title
        else:
            # Use first part of title
            words = title.split()
            return ' '.join(words[:2]) if len(words) >= 2 else title
    
    def get_salesforce_data(self, prospect_name: str) -> dict:
        """Get Salesforce event data for prospect"""
        print(f"🔍 Looking up Salesforce data for: {prospect_name}")
        
        try:
            # Use existing Salesforce CLI integration
            result = os.popen(f'cd .. && echo "{prospect_name}" | python3 salesforce_client.py').read()
            
            if 'Event ID:' in result:
                lines = result.strip().split('\n')
                sf_data = {}
                
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        sf_data[key.strip()] = value.strip()
                
                print(f"✅ Found Salesforce event")
                return sf_data
            else:
                print(f"⚠️ No Salesforce event found")
                return {}
                
        except Exception as e:
            print(f"❌ Salesforce lookup error: {str(e)}")
            return {}
    
    def analyze_with_openai(self, call_data: dict, sf_data: dict) -> dict:
        """Analyze call with OpenAI"""
        print(f"🤖 Analyzing call with OpenAI")
        
        # Build analysis prompt
        prompt = f"""
        Analyze this sales call for strategic insights:
        
        Call: {call_data['title']}
        Prospect: {call_data['prospect_name']}
        Date: {call_data['call_date']}
        
        Transcript:
        {call_data['transcript'][:3000]}...
        
        Salesforce Context:
        {json.dumps(sf_data, indent=2) if sf_data else 'No Salesforce data available'}
        
        Provide analysis in JSON format:
        {{
            "prospect_interest_level": "High|Medium|Low",
            "ae_excitement_level": "High|Medium|Low", 
            "analysis_confidence": 0.95,
            "strategic_insights": "Key insights...",
            "company_intelligence": "Research findings...",
            "next_steps": "Recommended actions..."
        }}
        """
        
        try:
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a sales intelligence analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                
                # Parse JSON from response
                analysis = json.loads(analysis_text)
                print(f"✅ OpenAI analysis complete")
                return analysis
            else:
                print(f"❌ OpenAI API error: {response.status_code}")
                return self.fallback_analysis()
                
        except Exception as e:
            print(f"❌ OpenAI analysis error: {str(e)}")
            return self.fallback_analysis()
    
    def fallback_analysis(self) -> dict:
        """Fallback analysis when OpenAI fails"""
        return {
            "prospect_interest_level": "Medium",
            "ae_excitement_level": "Medium",
            "analysis_confidence": 0.5,
            "strategic_insights": "Analysis unavailable - manual review recommended",
            "company_intelligence": "Manual research needed",
            "next_steps": "Follow up with AE for details"
        }
    
    def store_call_data(self, call_data: dict, analysis: dict, sf_data: dict) -> int:
        """Store call and analysis in database"""
        print(f"💾 Storing call data")
        
        conn = sqlite3.connect('ae_call_analysis.db')
        cursor = conn.cursor()
        
        # Store call
        cursor.execute('''
        INSERT INTO calls (
            fellow_id, prospect_name, title, call_date, 
            ae_name, prospect_company, created_at, transcript
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data['fellow_id'],
            call_data['prospect_name'],
            call_data['title'],
            call_data['call_date'],
            sf_data.get('Account Executive', 'Unknown'),
            sf_data.get('Company', 'Unknown'),
            datetime.now().isoformat(),
            call_data['transcript']
        ))
        
        call_id = cursor.lastrowid
        
        # Store analysis
        cursor.execute('''
        INSERT INTO analysis_results (
            call_id, prospect_interest_level, ae_excitement_level,
            analysis_confidence, strategic_insights, company_intelligence,
            salesforce_event_data, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_id,
            analysis['prospect_interest_level'],
            analysis['ae_excitement_level'],
            analysis['analysis_confidence'],
            analysis['strategic_insights'],
            analysis['company_intelligence'],
            json.dumps(sf_data),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Stored call {call_id}")
        return call_id
    
    def send_slack_alert(self, call_data: dict, analysis: dict, sf_data: dict):
        """Send enhanced alert to Slack"""
        print(f"📱 Sending Slack alert")
        
        # Build main message
        main_msg = f"""🔔 **New Call Intelligence Alert**

👤 **{call_data['prospect_name']}** | {sf_data.get('Company', 'Unknown Company')}
📊 Interest: **{analysis['prospect_interest_level']}** | AE Excitement: **{analysis['ae_excitement_level']}**
⭐ Confidence: {analysis['analysis_confidence']:.0%}"""

        # Build thread reply
        thread_msg = f"""📋 **Call Details:**
🆔 Fellow ID: `{call_data['fellow_id']}`
📞 Title: {call_data['title']}
📅 Date: {call_data['call_date']}
🎯 AE: {sf_data.get('Account Executive', 'Unknown')}

🧠 **Strategic Insights:**
{analysis['strategic_insights']}

🏢 **Company Intelligence:**
{analysis['company_intelligence']}

📈 **Next Steps:**
{analysis.get('next_steps', 'Follow up with AE')}

🔗 **Salesforce:** {sf_data.get('Event Record URL', 'Not available')}"""

        # For now, just print (replace with actual Slack webhook)
        print(f"📨 Slack Alert Ready:")
        print(f"Main: {main_msg}")
        print(f"Thread: {thread_msg}")
    
    async def process_call(self, fellow_call_id: str) -> dict:
        """Main orchestration method"""
        start_time = datetime.now()
        
        try:
            # Step 1: Get Fellow call data
            call_data = self.get_fellow_call_data(fellow_call_id)
            
            # Step 2: Get Salesforce data
            sf_data = self.get_salesforce_data(call_data['prospect_name'])
            
            # Step 3: Analyze with OpenAI
            analysis = self.analyze_with_openai(call_data, sf_data)
            
            # Step 4: Store in database
            call_id = self.store_call_data(call_data, analysis, sf_data)
            
            # Step 5: Send Slack alert
            self.send_slack_alert(call_data, analysis, sf_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'message': f'Call processed successfully',
                'call_id': call_id,
                'prospect_name': call_data['prospect_name'],
                'processing_time': f'{processing_time:.1f}s'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Initialize orchestrator
orchestrator = CallIntelligenceOrchestrator()

@app.get("/")
async def root():
    return {"message": "Call Intelligence API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/process-call", response_model=CallResponse)
async def process_call(request: CallRequest):
    """
    Process a Fellow call through the full intelligence pipeline
    """
    print(f"\n🚀 Processing Fellow call: {request.fellow_call_id}")
    print("=" * 50)
    
    result = await orchestrator.process_call(request.fellow_call_id)
    
    print(f"✅ Processing complete: {result['processing_time']}")
    print("=" * 50)
    
    return CallResponse(**result)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Call Intelligence API")
    uvicorn.run(app, host="0.0.0.0", port=8080)