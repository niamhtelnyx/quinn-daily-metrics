#!/usr/bin/env python3
"""
Simple Call Intelligence API - FastAPI orchestrator
Simplified version for testing - accepts call data directly
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import sqlite3
import asyncio
from datetime import datetime
import os
from typing import Optional, List

app = FastAPI(title="Simple Call Intelligence API", version="1.0.0")

class CallDataRequest(BaseModel):
    prospect_name: str
    title: str
    transcript: str
    call_date: Optional[str] = None
    fellow_id: Optional[str] = None

class CallResponse(BaseModel):
    status: str
    message: str
    call_id: Optional[int] = None
    prospect_name: Optional[str] = None
    processing_time: Optional[str] = None

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

class SimpleCallOrchestrator:
    def __init__(self):
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect('simple_call_analysis.db')
        cursor = conn.cursor()
        
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
            next_steps TEXT,
            created_at TEXT,
            FOREIGN KEY (call_id) REFERENCES calls (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_salesforce_data(self, prospect_name: str) -> dict:
        """Get Salesforce event data for prospect"""
        print(f"🔍 Looking up Salesforce data for: {prospect_name}")
        
        try:
            # Use existing Salesforce CLI integration
            result = os.popen(f'cd .. && echo "{prospect_name}" | python3 salesforce_client.py').read()
            
            if 'Account Executive:' in result:
                lines = result.strip().split('\n')
                sf_data = {}
                
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        sf_data[key.strip()] = value.strip()
                
                print(f"✅ Found Salesforce event: {sf_data.get('Subject', 'Unknown')}")
                return sf_data
            else:
                print(f"⚠️ No Salesforce event found for {prospect_name}")
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
        Date: {call_data.get('call_date', 'Unknown')}
        
        Transcript Sample:
        {call_data['transcript'][:2000]}...
        
        Salesforce Context:
        {json.dumps(sf_data, indent=2) if sf_data else 'No Salesforce data available'}
        
        Provide analysis in JSON format ONLY (no other text):
        {{
            "prospect_interest_level": "High|Medium|Low",
            "ae_excitement_level": "High|Medium|Low", 
            "analysis_confidence": 0.85,
            "strategic_insights": "Key strategic insights from the call...",
            "company_intelligence": "Company background and research findings...",
            "next_steps": "Recommended next actions..."
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
                    {"role": "system", "content": "You are a strategic sales analyst. Return ONLY valid JSON, no other text."},
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
                analysis_text = result['choices'][0]['message']['content'].strip()
                
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
        
        conn = sqlite3.connect('simple_call_analysis.db')
        cursor = conn.cursor()
        
        # Store call
        cursor.execute('''
        INSERT INTO calls (
            fellow_id, prospect_name, title, call_date, 
            ae_name, prospect_company, created_at, transcript
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data.get('fellow_id', 'manual'),
            call_data['prospect_name'],
            call_data['title'],
            call_data.get('call_date', datetime.now().isoformat()),
            sf_data.get('Account Executive', 'Unknown'),
            sf_data.get('Account', 'Unknown'),
            datetime.now().isoformat(),
            call_data['transcript']
        ))
        
        call_id = cursor.lastrowid
        
        # Store analysis
        cursor.execute('''
        INSERT INTO analysis_results (
            call_id, prospect_interest_level, ae_excitement_level,
            analysis_confidence, strategic_insights, company_intelligence,
            next_steps, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_id,
            analysis['prospect_interest_level'],
            analysis['ae_excitement_level'],
            analysis['analysis_confidence'],
            analysis['strategic_insights'],
            analysis['company_intelligence'],
            analysis['next_steps'],
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

👤 **{call_data['prospect_name']}** | {sf_data.get('Account', 'Unknown Company')}
📊 Interest: **{analysis['prospect_interest_level']}** | AE Excitement: **{analysis['ae_excitement_level']}**
⭐ Confidence: {analysis['analysis_confidence']:.0%}"""

        # Build thread reply
        thread_msg = f"""📋 **Call Details:**
📞 Title: {call_data['title']}
📅 Date: {call_data.get('call_date', 'Unknown')}
🎯 AE: {sf_data.get('Account Executive', 'Unknown')}

🧠 **Strategic Insights:**
{analysis['strategic_insights']}

🏢 **Company Intelligence:**
{analysis['company_intelligence']}

📈 **Next Steps:**
{analysis['next_steps']}

🔗 **Salesforce:** {sf_data.get('Record URL', 'Not available')}"""

        # For now, just print (replace with actual Slack webhook)
        print(f"📨 Slack Alert Ready:")
        print(f"Main: {main_msg}")
        print(f"Thread: {thread_msg}")
        
        # TODO: Send to actual Slack
        return {"main_message": main_msg, "thread_message": thread_msg}
    
    async def process_call(self, call_data: dict) -> dict:
        """Main orchestration method"""
        start_time = datetime.now()
        
        try:
            # Step 1: Get Salesforce data
            print(f"📞 Processing call for: {call_data['prospect_name']}")
            sf_data = self.get_salesforce_data(call_data['prospect_name'])
            
            # Step 2: Analyze with OpenAI
            analysis = self.analyze_with_openai(call_data, sf_data)
            
            # Step 3: Store in database
            call_id = self.store_call_data(call_data, analysis, sf_data)
            
            # Step 4: Send Slack alert
            slack_result = self.send_slack_alert(call_data, analysis, sf_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'message': f'Call processed successfully',
                'call_id': call_id,
                'prospect_name': call_data['prospect_name'],
                'processing_time': f'{processing_time:.1f}s',
                'analysis': analysis,
                'slack_preview': slack_result
            }
            
        except Exception as e:
            print(f"❌ Processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Initialize orchestrator
orchestrator = SimpleCallOrchestrator()

@app.get("/")
async def root():
    return {"message": "Simple Call Intelligence API", "version": "1.0.0", "mode": "direct_input"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/process-call")
async def process_call(request: CallDataRequest):
    """
    Process call data through the intelligence pipeline
    """
    print(f"\n🚀 Processing call: {request.prospect_name}")
    print("=" * 50)
    
    call_data = {
        'prospect_name': request.prospect_name,
        'title': request.title,
        'transcript': request.transcript,
        'call_date': request.call_date,
        'fellow_id': request.fellow_id
    }
    
    result = await orchestrator.process_call(call_data)
    
    print(f"✅ Processing complete: {result['processing_time']}")
    print("=" * 50)
    
    return result

@app.get("/calls")
async def list_calls():
    """List recent calls"""
    conn = sqlite3.connect('simple_call_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.id, c.prospect_name, c.title, c.call_date, c.ae_name,
           a.prospect_interest_level, a.analysis_confidence
    FROM calls c
    LEFT JOIN analysis_results a ON c.id = a.call_id
    ORDER BY c.created_at DESC
    LIMIT 20
    ''')
    
    calls = []
    for row in cursor.fetchall():
        calls.append({
            'id': row[0],
            'prospect_name': row[1],
            'title': row[2],
            'call_date': row[3],
            'ae_name': row[4],
            'interest_level': row[5],
            'confidence': row[6]
        })
    
    conn.close()
    return {"calls": calls}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Simple Call Intelligence API")
    print("📝 Mode: Direct call data input (no Fellow API)")
    uvicorn.run(app, host="0.0.0.0", port=8080)