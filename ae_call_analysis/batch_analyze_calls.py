#!/usr/bin/env python3
"""
Batch analyze all unprocessed calls to populate database for cron job
"""

import sqlite3
import requests
import json
import os
from datetime import datetime

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

def add_analysis_columns():
    """Add analysis columns to database if they don't exist"""
    conn = sqlite3.connect('ae_call_analysis.db')
    cursor = conn.cursor()
    
    # Add analysis columns
    analysis_columns = [
        ('analysis_confidence', 'INTEGER'),
        ('prospect_interest_level', 'INTEGER'), 
        ('ae_excitement_level', 'INTEGER'),
        ('quinn_qualification_quality', 'INTEGER'),
        ('core_talking_points', 'TEXT'),
        ('use_cases', 'TEXT'),
        ('prospect_buying_signals', 'TEXT'),
        ('next_steps_actions', 'TEXT'),
        ('conversation_style', 'TEXT'),
        ('processed_by_enhanced', 'INTEGER DEFAULT 0')
    ]
    
    for column_name, column_type in analysis_columns:
        try:
            cursor.execute(f'ALTER TABLE calls ADD COLUMN {column_name} {column_type}')
            print(f"✅ Added column: {column_name}")
        except sqlite3.OperationalError:
            # Column already exists
            pass
    
    conn.commit()
    conn.close()

def analyze_call_openai(call_data):
    """Analyze call using OpenAI API"""
    
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ No OpenAI API key found")
        return None
    
    # Create analysis prompt
    transcript = call_data.get('transcript', '')
    fellow_notes = call_data.get('fellow_ai_notes', '')
    
    if not transcript and not fellow_notes:
        print("❌ No transcript or notes found")
        return None
    
    prompt = f"""
Analyze this Telnyx intro call and provide numerical scores (1-10) and insights:

CALL DATA:
Title: {call_data.get('title', 'N/A')}
Prospect: {call_data.get('prospect_name', 'N/A')} 
Company: {call_data.get('prospect_company', 'N/A')}

TRANSCRIPT: {transcript[:5000]}

FELLOW AI NOTES: {fellow_notes[:1000]}

Provide analysis in this JSON format:
{{
  "analysis_confidence": 8,
  "prospect_interest_level": 7, 
  "ae_excitement_level": 6,
  "quinn_qualification_quality": 8,
  "core_talking_points": ["pain point 1", "pain point 2", "pain point 3"],
  "use_cases": ["use case 1", "use case 2"],
  "prospect_buying_signals": ["signal 1", "signal 2"],
  "next_steps_actions": ["action 1", "action 2"],
  "conversation_style": "Technical_Deep_Dive"
}}

Return only valid JSON.
"""
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Try to extract JSON from content
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '')
            
            analysis = json.loads(content.strip())
            return analysis
        else:
            print(f"❌ OpenAI API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def batch_analyze():
    """Analyze all calls that need analysis"""
    
    print("🚀 BATCH ANALYZING CALLS FOR CRON JOB")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Add columns first
    add_analysis_columns()
    
    # Get calls that need analysis
    conn = sqlite3.connect('ae_call_analysis.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, prospect_name, title, transcript, fellow_ai_notes, prospect_company
    FROM calls 
    WHERE analysis_confidence IS NULL
    AND prospect_name IS NOT NULL
    LIMIT 10
    ''')
    
    calls_to_analyze = cursor.fetchall()
    
    if not calls_to_analyze:
        print("📋 No calls need analysis")
        conn.close()
        return
    
    print(f"📞 Found {len(calls_to_analyze)} calls to analyze")
    
    analyzed_count = 0
    
    for call_id, prospect_name, title, transcript, fellow_ai_notes, prospect_company in calls_to_analyze:
        
        print(f"\n🔄 Analyzing Call {call_id}: {prospect_name}")
        
        call_data = {
            'id': call_id,
            'prospect_name': prospect_name,
            'title': title,
            'transcript': transcript,
            'fellow_ai_notes': fellow_ai_notes,
            'prospect_company': prospect_company
        }
        
        analysis = analyze_call_openai(call_data)
        
        if analysis:
            try:
                # Update database with analysis
                cursor.execute('''
                UPDATE calls SET
                    analysis_confidence = ?,
                    prospect_interest_level = ?,
                    ae_excitement_level = ?,
                    quinn_qualification_quality = ?,
                    core_talking_points = ?,
                    use_cases = ?,
                    prospect_buying_signals = ?,
                    next_steps_actions = ?,
                    conversation_style = ?
                WHERE id = ?
                ''', (
                    analysis.get('analysis_confidence'),
                    analysis.get('prospect_interest_level'),
                    analysis.get('ae_excitement_level'),
                    analysis.get('quinn_qualification_quality'),
                    json.dumps(analysis.get('core_talking_points', [])),
                    json.dumps(analysis.get('use_cases', [])),
                    json.dumps(analysis.get('prospect_buying_signals', [])),
                    json.dumps(analysis.get('next_steps_actions', [])),
                    analysis.get('conversation_style'),
                    call_id
                ))
                
                print(f"✅ Analysis complete: {analysis.get('analysis_confidence')}/10 confidence")
                analyzed_count += 1
                
            except Exception as e:
                print(f"❌ Database update failed: {e}")
        else:
            print("❌ Analysis failed")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Analyzed {analyzed_count}/{len(calls_to_analyze)} calls successfully")
    print("✅ Database ready for cron job processing!")

if __name__ == "__main__":
    batch_analyze()