#!/usr/bin/env python3
"""
Demo Call Intelligence API - Working orchestration without external API dependencies
Shows complete pipeline architecture that can be enhanced with working credentials
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import sqlite3
from datetime import datetime
import os
from typing import Optional, List

app = FastAPI(title="Demo Call Intelligence API", version="3.0.0", description="Complete orchestration pipeline")

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

class DemoCallOrchestrator:
    def __init__(self):
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database"""
        db_path = os.getenv("DATABASE_PATH", "/app/data/call_analysis.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
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
            pain_points TEXT,
            buying_signals TEXT,
            competitive_mentions TEXT,
            technical_requirements TEXT,
            budget_timeline TEXT,
            created_at TEXT,
            FOREIGN KEY (call_id) REFERENCES calls (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
    
    def get_salesforce_data(self, prospect_name: str) -> dict:
        """Simulate Salesforce integration (replace with real CLI when working)"""
        print(f"🔍 Salesforce lookup: {prospect_name}")
        
        # Demo data based on prospect name patterns
        demo_sf_data = {
            "Michael Chen": {
                "Account Executive": "Sarah Williams", 
                "Account": "TechFlow Solutions",
                "Subject": "Enterprise Voice Solutions Demo", 
                "Record URL": "https://telnyx.lightning.force.com/lightning/r/Event/00U123ABC456/view"
            },
            "Jane Smith": {
                "Account Executive": "Mike Johnson",
                "Account": "DataCorp Inc", 
                "Subject": "Voice Platform Discovery",
                "Record URL": "https://telnyx.lightning.force.com/lightning/r/Event/00U789DEF123/view"
            },
            "John Doe": {
                "Account Executive": "Lisa Rodriguez",
                "Account": "CloudTech LLC",
                "Subject": "Communications Modernization", 
                "Record URL": "https://telnyx.lightning.force.com/lightning/r/Event/00U456GHI789/view"
            }
        }
        
        sf_data = demo_sf_data.get(prospect_name, {
            "Account Executive": "Demo AE",
            "Account": self.extract_company_from_title(prospect_name),
            "Subject": f"Demo Call - {prospect_name}",
            "Record URL": "https://demo.salesforce.com/event/demo123"
        })
        
        if sf_data.get("Account Executive") != "Demo AE":
            print(f"✅ Found Salesforce event: {sf_data['Subject']}")
        else:
            print(f"⚠️ Using demo Salesforce data for {prospect_name}")
            
        return sf_data
    
    def analyze_with_ai(self, call_data: dict, sf_data: dict) -> dict:
        """Intelligent analysis simulation based on transcript content"""
        print(f"🤖 Analyzing call transcript intelligently")
        
        transcript = call_data['transcript'].lower()
        
        # Analyze interest level based on transcript content
        high_interest_signals = [
            "excited", "perfect", "exactly what we need", "when can we start", 
            "budget approved", "ready to move forward", "this sounds great",
            "timeline", "implementation", "next steps"
        ]
        
        medium_interest_signals = [
            "interesting", "sounds good", "tell me more", "what about",
            "how much", "pricing", "demo", "show me"
        ]
        
        # Analyze buying signals
        buying_signals = []
        if any(signal in transcript for signal in ["budget", "approved", "decision", "timeline"]):
            buying_signals.append("Budget and timeline discussed")
        if any(signal in transcript for signal in ["demo", "presentation", "show me"]):
            buying_signals.append("Requested product demonstration")
        if any(signal in transcript for signal in ["technical", "integration", "setup"]):
            buying_signals.append("Technical implementation interest")
        if any(signal in transcript for signal in ["team", "it department", "colleagues"]):
            buying_signals.append("Multiple stakeholders involved")
        
        # Analyze pain points
        pain_points = []
        if any(signal in transcript for signal in ["expensive", "cost", "paying too much"]):
            pain_points.append("Cost concerns with current solution")
        if any(signal in transcript for signal in ["quality", "dropped calls", "poor"]):
            pain_points.append("Call quality issues")
        if any(signal in transcript for signal in ["outdated", "old system", "legacy"]):
            pain_points.append("Outdated infrastructure")
        if any(signal in transcript for signal in ["remote", "distributed", "offices"]):
            pain_points.append("Remote work communication challenges")
        if any(signal in transcript for signal in ["maintenance", "it team", "managing"]):
            pain_points.append("High maintenance overhead")
        
        # Analyze competitive mentions
        competitive_mentions = []
        competitors = ["ringcentral", "8x8", "vonage", "zoom phone", "microsoft teams", "cisco"]
        for competitor in competitors:
            if competitor.replace(" ", "") in transcript.replace(" ", ""):
                competitive_mentions.append(f"Mentioned {competitor.title()}")
        
        # Determine interest and excitement levels
        high_signals = sum(1 for signal in high_interest_signals if signal in transcript)
        medium_signals = sum(1 for signal in medium_interest_signals if signal in transcript)
        
        if high_signals >= 2:
            interest_level = "High"
            ae_excitement = "High"
            confidence = 0.85 + (high_signals * 0.03)
        elif high_signals >= 1 or medium_signals >= 3:
            interest_level = "Medium"
            ae_excitement = "Medium" 
            confidence = 0.70 + (medium_signals * 0.02)
        else:
            interest_level = "Low"
            ae_excitement = "Low"
            confidence = 0.55
        
        # Generate insights based on content
        company = sf_data.get('Account', 'Unknown Company')
        ae_name = sf_data.get('Account Executive', 'Unknown AE')
        
        strategic_insights = f"Analysis of {call_data['prospect_name']}'s call reveals a {interest_level.lower()}-value opportunity with {company}. "
        
        if pain_points:
            strategic_insights += f"Key pain points identified: {', '.join(pain_points[:2])}. "
            
        if buying_signals:
            strategic_insights += f"Positive buying signals detected: {', '.join(buying_signals[:2])}. "
            
        strategic_insights += f"AE {ae_name} should focus on addressing cost and implementation concerns while emphasizing Telnyx's reliability and ROI value proposition."
        
        # Generate next steps
        next_steps = "Recommended immediate actions: "
        if "demo" in transcript:
            next_steps += "1) Schedule technical demo with stakeholders. "
        if "budget" in transcript:
            next_steps += "2) Prepare ROI analysis and cost comparison. "
        if "timeline" in transcript:
            next_steps += "3) Provide implementation timeline and project plan. "
        if not any(word in transcript for word in ["demo", "budget", "timeline"]):
            next_steps += "1) Send follow-up with Telnyx overview. 2) Schedule discovery call with decision makers."
        
        return {
            "prospect_interest_level": interest_level,
            "ae_excitement_level": ae_excitement,
            "analysis_confidence": min(confidence, 0.95),
            "strategic_insights": strategic_insights,
            "company_intelligence": f"{company} is evaluating voice communication solutions. Based on the conversation, they appear to be a growing company with {interest_level.lower()}-priority communication needs. Industry analysis suggests potential for significant ROI with modern cloud communications platform.",
            "pain_points": "; ".join(pain_points) if pain_points else "No specific pain points identified in transcript",
            "buying_signals": "; ".join(buying_signals) if buying_signals else "Limited buying signals detected",
            "competitive_mentions": "; ".join(competitive_mentions) if competitive_mentions else "No competitors mentioned",
            "next_steps": next_steps,
            "technical_requirements": "Voice communications platform with enterprise features" if "enterprise" in transcript else "Standard voice communications solution",
            "budget_timeline": "Budget approved, seeking implementation timeline" if "budget" in transcript and "approved" in transcript else "Budget and timeline to be determined"
        }
    
    def extract_company_from_title(self, title: str) -> str:
        """Extract company name from call title"""
        if '(' in title and ')' in title:
            return title.split('(')[1].split(')')[0].strip()
        elif ' - ' in title:
            parts = title.split(' - ')
            if len(parts) > 1:
                return parts[0].strip()
        return 'Demo Company Inc'
    
    def store_call_data(self, call_data: dict, analysis: dict, sf_data: dict) -> int:
        """Store call and analysis in database"""
        print(f"💾 Storing call and analysis data")
        
        db_path = os.getenv("DATABASE_PATH", "/app/data/call_analysis.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Store call
        cursor.execute('''
        INSERT INTO calls (
            fellow_id, prospect_name, title, call_date, 
            ae_name, prospect_company, created_at, transcript
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data.get('fellow_id', f'demo_{int(datetime.now().timestamp())}'),
            call_data['prospect_name'],
            call_data['title'],
            call_data.get('call_date', datetime.now().isoformat()),
            sf_data.get('Account Executive', 'Demo AE'),
            sf_data.get('Account', self.extract_company_from_title(call_data['title'])),
            datetime.now().isoformat(),
            call_data['transcript'][:5000]  # Truncate very long transcripts
        ))
        
        call_id = cursor.lastrowid
        
        # Store analysis
        cursor.execute('''
        INSERT INTO analysis_results (
            call_id, prospect_interest_level, ae_excitement_level,
            analysis_confidence, strategic_insights, company_intelligence,
            next_steps, pain_points, buying_signals, competitive_mentions,
            technical_requirements, budget_timeline, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_id,
            analysis['prospect_interest_level'],
            analysis['ae_excitement_level'],
            analysis['analysis_confidence'],
            analysis['strategic_insights'],
            analysis['company_intelligence'],
            analysis['next_steps'],
            analysis.get('pain_points', ''),
            analysis.get('buying_signals', ''),
            analysis.get('competitive_mentions', ''),
            analysis.get('technical_requirements', ''),
            analysis.get('budget_timeline', ''),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Stored call {call_id}")
        return call_id
    
    def generate_slack_alert(self, call_data: dict, analysis: dict, sf_data: dict, call_id: int) -> dict:
        """Generate production-ready Slack alert"""
        print(f"📱 Generating Slack alert")
        
        interest = analysis['prospect_interest_level']
        confidence = analysis['analysis_confidence']
        company = sf_data.get('Account', self.extract_company_from_title(call_data['title']))
        ae_name = sf_data.get('Account Executive', 'Demo AE')
        
        # Interest-level emoji
        emoji = "🔥" if interest == "High" else "📊" if interest == "Medium" else "📝"
        
        # Build main alert message
        main_msg = f"""{emoji} **Call Intelligence Alert**

👤 **{call_data['prospect_name']}** | {company}
📊 Interest: **{interest}** | AE Excitement: **{analysis['ae_excitement_level']}**
⭐ Confidence: **{confidence:.0%}** | 🎯 AE: **{ae_name}**"""

        # Build detailed thread message
        thread_msg = f"""📋 **Complete Call Analysis**

🏢 **Company:** {company}
📞 **Call:** {call_data['title']}
📅 **Date:** {call_data.get('call_date', 'Unknown')}
🆔 **Call ID:** {call_id}

🧠 **Strategic Insights:**
{analysis['strategic_insights']}

🔍 **Company Intelligence:**
{analysis['company_intelligence']}

🔴 **Pain Points:**
{analysis.get('pain_points', 'Not identified')}

💡 **Buying Signals:**
{analysis.get('buying_signals', 'Not identified')}

⚔️ **Competitive Landscape:**
{analysis.get('competitive_mentions', 'No competitors mentioned')}

🔧 **Technical Requirements:**
{analysis.get('technical_requirements', 'Standard requirements')}

💰 **Budget & Timeline:**
{analysis.get('budget_timeline', 'To be determined')}

📈 **Immediate Next Steps:**
{analysis['next_steps']}

🔗 **Salesforce Event:** {sf_data.get('Record URL', 'Not available')}
🎯 **Follow-up Priority:** {"🔥 HIGH" if interest == "High" else "📊 MEDIUM" if interest == "Medium" else "📝 LOW"}"""

        return {
            "main_message": main_msg,
            "thread_message": thread_msg,
            "summary": {
                "prospect": call_data['prospect_name'],
                "company": company,
                "interest": interest,
                "confidence": confidence,
                "ae_name": ae_name,
                "call_id": call_id,
                "priority": "HIGH" if interest == "High" else "MEDIUM" if interest == "Medium" else "LOW"
            }
        }
    
    async def process_call(self, call_data: dict) -> dict:
        """Complete orchestration pipeline"""
        start_time = datetime.now()
        
        try:
            print(f"📞 Processing call for: {call_data['prospect_name']}")
            
            # Step 1: Salesforce lookup
            sf_data = self.get_salesforce_data(call_data['prospect_name'])
            
            # Step 2: AI Analysis (intelligent simulation)
            analysis = self.analyze_with_ai(call_data, sf_data)
            
            # Step 3: Database storage
            call_id = self.store_call_data(call_data, analysis, sf_data)
            
            # Step 4: Slack alert generation
            slack_alert = self.generate_slack_alert(call_data, analysis, sf_data, call_id)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'message': f'Call processed successfully with intelligent analysis',
                'call_id': call_id,
                'prospect_name': call_data['prospect_name'],
                'processing_time': f'{processing_time:.1f}s',
                'analysis': analysis,
                'salesforce': sf_data,
                'slack_alert': slack_alert,
                'pipeline_steps': [
                    '✅ Salesforce lookup completed',
                    '✅ Intelligent analysis completed', 
                    '✅ Database storage completed',
                    '✅ Slack alert generated'
                ]
            }
            
        except Exception as e:
            print(f"❌ Processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Initialize orchestrator
orchestrator = DemoCallOrchestrator()

@app.get("/")
async def root():
    return {
        "message": "Demo Call Intelligence API", 
        "version": "3.0.0", 
        "status": "Complete pipeline demonstration",
        "features": [
            "Intelligent transcript analysis ✅",
            "Salesforce integration demo ✅", 
            "Database storage ✅",
            "Professional Slack alerts ✅",
            "Production-ready architecture ✅"
        ],
        "note": "Ready for real API credentials"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "pipeline_ready": True
    }

@app.post("/process-call")
async def process_call(request: CallDataRequest):
    """Process call through complete intelligence pipeline"""
    print(f"\n🚀 Processing call: {request.prospect_name}")
    print("=" * 70)
    
    call_data = {
        'prospect_name': request.prospect_name,
        'title': request.title,
        'transcript': request.transcript,
        'call_date': request.call_date,
        'fellow_id': request.fellow_id
    }
    
    result = await orchestrator.process_call(call_data)
    
    print(f"✅ Processing complete: {result['processing_time']}")
    print("=" * 70)
    
    return result

@app.get("/calls")
async def list_calls():
    """List all processed calls"""
    conn = sqlite3.connect(os.getenv('DATABASE_PATH', '/app/data/call_analysis.db'))
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.id, c.prospect_name, c.title, c.ae_name, c.prospect_company,
           a.prospect_interest_level, a.analysis_confidence, c.created_at
    FROM calls c
    LEFT JOIN analysis_results a ON c.id = a.call_id
    ORDER BY c.created_at DESC
    ''')
    
    calls = []
    for row in cursor.fetchall():
        calls.append({
            'id': row[0],
            'prospect_name': row[1], 
            'title': row[2],
            'ae_name': row[3],
            'company': row[4],
            'interest_level': row[5],
            'confidence': row[6],
            'created_at': row[7]
        })
    
    conn.close()
    return {"calls": calls, "total": len(calls)}

@app.get("/call/{call_id}")
async def get_call_details(call_id: int):
    """Get complete call analysis details"""
    conn = sqlite3.connect(os.getenv('DATABASE_PATH', '/app/data/call_analysis.db'))
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.*, a.*
    FROM calls c
    LEFT JOIN analysis_results a ON c.id = a.call_id
    WHERE c.id = ?
    ''', (call_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call": {
            "id": result[0],
            "fellow_id": result[1],
            "prospect_name": result[2],
            "ae_name": result[3],
            "title": result[4],
            "call_date": result[5],
            "company": result[6],
            "transcript": result[8]
        },
        "analysis": {
            "interest_level": result[10],
            "ae_excitement": result[11],
            "confidence": result[12],
            "strategic_insights": result[13],
            "company_intelligence": result[14],
            "next_steps": result[15],
            "pain_points": result[16],
            "buying_signals": result[17],
            "competitive_mentions": result[18],
            "technical_requirements": result[19],
            "budget_timeline": result[20]
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))  # Railway/Heroku compatible
    print("🚀 Starting Call Intelligence API")
    print("✅ Complete orchestration pipeline ready") 
    print(f"🌐 Running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)