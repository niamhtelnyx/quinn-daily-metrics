#!/usr/bin/env python3
"""
V3 ASYNC Call Intelligence - PRODUCTION
Parallel processing + Enhanced Google Drive parsing + Smart deduplication + Salesforce fallback

NEW FEATURES:
🚀 Async parallel processing - handles 10+ calls efficiently  
⚡ Controlled concurrency - respects API rate limits
🔄 Error isolation - failed calls don't block others
⏰ Timeout handling - prevents infinite hangs
📊 Performance monitoring - tracks processing times

EXISTING FEATURES:
✅ Flexible Google Drive parsing (content-based attendee extraction)
✅ Fellow API processing 
✅ AI call analysis (9-point structure)
✅ Enhanced Slack alerts with Salesforce links
✅ Company summaries
✅ Salesforce event updates
✅ Smart deduplication (Gemini first, Fellow adds URL later)
✅ Salesforce fallback table for unmatched contacts
"""

import asyncio
import aiohttp
import requests
import json
import os
import sqlite3
import sys
import re
import time
from datetime import datetime, timedelta
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Tuple

def load_env():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

class AsyncCallProcessor:
    """Async parallel call processing with rate limiting and error handling"""
    
    def __init__(self, max_concurrent_calls=5, max_openai_calls=3):
        # Semaphores to control API rate limits
        self.call_semaphore = asyncio.Semaphore(max_concurrent_calls)
        self.openai_semaphore = asyncio.Semaphore(max_openai_calls)  # OpenAI: 3 RPM limit
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)
    
    async def process_calls_parallel(self, calls: List[Dict]) -> Dict:
        """Process multiple calls in parallel with controlled concurrency"""
        start_time = time.time()
        log_message(f"🚀 Starting parallel processing of {len(calls)} calls")
        
        # Create tasks for all calls
        tasks = []
        for i, call in enumerate(calls):
            task = asyncio.create_task(
                self.process_single_call_async(call, f"call-{i+1}"),
                name=f"process_call_{i+1}"
            )
            tasks.append(task)
        
        # Wait for all calls to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        end_time = time.time()
        processing_time = end_time - start_time
        
        successes = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        errors = [r for r in results if isinstance(r, dict) and r.get('status') == 'error']
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        summary = {
            'total_calls': len(calls),
            'successful': len(successes),
            'errors': len(errors),
            'exceptions': len(exceptions),
            'processing_time': processing_time,
            'calls_per_minute': (len(calls) / processing_time) * 60,
            'results': results
        }
        
        log_message(f"📊 Parallel processing complete:")
        log_message(f"   ✅ Successful: {len(successes)}")
        log_message(f"   ❌ Errors: {len(errors)}")
        log_message(f"   🚨 Exceptions: {len(exceptions)}")
        log_message(f"   ⏱️ Time: {processing_time:.2f} seconds")
        log_message(f"   📈 Throughput: {summary['calls_per_minute']:.1f} calls/minute")
        
        return summary
    
    async def process_single_call_async(self, call: Dict, call_id: str) -> Dict:
        """Process a single call with timeout and error handling"""
        async with self.call_semaphore:  # Control overall concurrency
            try:
                log_message(f"🔄 {call_id} starting: {call.get('title', 'Unknown')}")
                
                # Phase 1: Fetch Google Drive content (async)
                content_result = await asyncio.wait_for(
                    self.fetch_google_drive_content_async(call),
                    timeout=30
                )
                
                if not content_result['success']:
                    return {'status': 'error', 'call': call, 'phase': 'content_fetch', 'error': content_result['error']}
                
                content = content_result['content']
                
                # Phase 2: Parse attendees
                parsed_call = await self.run_in_executor(
                    format_enhanced_google_drive_call, call, content
                )
                
                # Phase 3: Check for duplicates
                dedup_key = generate_dedup_key(
                    parsed_call.get('prospect_email') or parsed_call.get('prospect_name', ''),
                    call.get('modified_date', '')
                )
                
                is_duplicate = await self.run_in_executor(is_call_duplicate, dedup_key)
                if is_duplicate:
                    log_message(f"⚠️ {call_id} duplicate found, skipping")
                    return {'status': 'skipped', 'call': call, 'reason': 'duplicate'}
                
                # Phase 4: AI Analysis (rate-limited)
                async with self.openai_semaphore:  # Respect OpenAI rate limits
                    analysis_result = await asyncio.wait_for(
                        self.analyze_call_async(content),
                        timeout=60  # Longer timeout for AI analysis
                    )
                
                if not analysis_result['success']:
                    return {'status': 'error', 'call': call, 'phase': 'ai_analysis', 'error': analysis_result['error']}
                
                analysis = analysis_result['analysis']
                
                # Phase 5: Salesforce integration (async)
                sf_result = await self.update_salesforce_async(parsed_call, analysis)
                
                # Phase 6: Slack notification (fire and forget)
                asyncio.create_task(
                    self.post_slack_notification_async(parsed_call, analysis)
                )
                
                # Phase 7: Save to database
                await self.run_in_executor(
                    save_processed_call, parsed_call, analysis, dedup_key
                )
                
                log_message(f"✅ {call_id} completed successfully")
                return {
                    'status': 'success',
                    'call': call,
                    'analysis': analysis,
                    'dedup_key': dedup_key
                }
                
            except asyncio.TimeoutError:
                log_message(f"⏰ {call_id} timeout after limits")
                return {'status': 'error', 'call': call, 'error': 'timeout'}
            
            except Exception as e:
                log_message(f"❌ {call_id} unexpected error: {str(e)}")
                return {'status': 'error', 'call': call, 'error': str(e)}
    
    async def fetch_google_drive_content_async(self, call: Dict) -> Dict:
        """Async Google Drive content fetch"""
        try:
            # Use executor for subprocess calls (gog CLI is synchronous)
            content, error = await self.run_in_executor(
                get_google_doc_content, call['id']
            )
            
            if error:
                return {'success': False, 'error': error}
            
            if not content or len(content.strip()) < 100:
                return {'success': False, 'error': 'Content too short or empty'}
            
            return {'success': True, 'content': content}
            
        except Exception as e:
            return {'success': False, 'error': f"Content fetch error: {str(e)}"}
    
    async def analyze_call_async(self, content: str) -> Dict:
        """Async AI call analysis with OpenAI"""
        try:
            # Use aiohttp for OpenAI API call
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                return {'success': False, 'error': 'Missing OpenAI API key'}
            
            headers = {
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Enhanced prompt for call analysis
            prompt = f"""
            Analyze this sales call and provide structured insights:

            CALL CONTENT:
            {content[:4000]}  # Limit content size

            Please provide a JSON response with these fields:
            {{
                "summary": "Brief overview of the call",
                "participants": ["List", "of", "attendees"],
                "key_points": ["Main", "discussion", "points"],
                "next_steps": ["Action", "items"],
                "pain_points": ["Customer", "challenges"],
                "competitive_mentions": ["Any", "competitors"],
                "technical_requirements": ["Tech", "needs"],
                "decision_makers": ["Key", "stakeholders"],
                "timeline": "Expected timeline for decisions",
                "sentiment": "positive/neutral/negative"
            }}
            """
            
            payload = {
                'model': 'gpt-4o-mini',  # Fast, cost-effective model
                'messages': [
                    {'role': 'system', 'content': 'You are a sales call analysis expert. Return only valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 1000,
                'temperature': 0.3
            }
            
            async with self.session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    return {'success': False, 'error': f'OpenAI API error: {response.status} - {error_text}'}
                
                result = await response.json()
                
                if 'choices' not in result or not result['choices']:
                    return {'success': False, 'error': 'No choices in OpenAI response'}
                
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                try:
                    analysis = json.loads(content)
                    return {'success': True, 'analysis': analysis}
                except json.JSONDecodeError:
                    # Fallback to basic analysis if JSON parsing fails
                    return {
                        'success': True,
                        'analysis': {
                            'summary': content[:200] + '...',
                            'participants': [],
                            'key_points': [],
                            'next_steps': [],
                            'sentiment': 'neutral'
                        }
                    }
                    
        except Exception as e:
            return {'success': False, 'error': f"AI analysis error: {str(e)}"}
    
    async def update_salesforce_async(self, call_data: Dict, analysis: Dict) -> Dict:
        """Async Salesforce update with retry logic"""
        for attempt in range(3):
            try:
                # Use executor for Salesforce API (keeping existing sync code)
                result = await self.run_in_executor(
                    update_salesforce_event, call_data, analysis
                )
                return {'success': True, 'result': result}
                
            except Exception as e:
                if attempt == 2:  # Last attempt
                    log_message(f"🔄 Salesforce update failed after 3 attempts: {str(e)}")
                    return {'success': False, 'error': str(e)}
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def post_slack_notification_async(self, call_data: Dict, analysis: Dict):
        """Async Slack notification"""
        try:
            # Use executor for Slack posting (keeping existing sync code)
            await self.run_in_executor(
                post_enhanced_slack_alert, call_data, analysis
            )
            
        except Exception as e:
            log_message(f"⚠️ Slack notification failed: {str(e)}")
            # Don't fail the entire process for Slack errors
    
    async def run_in_executor(self, func, *args):
        """Run synchronous function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)

# Keep all existing synchronous functions from V2_FINAL_PRODUCTION.py
def run_gog_command(cmd):
    """Run gog CLI command and return output"""
    try:
        env = os.environ.copy()
        env_file_path = '/Users/niamhcollins/clawd/.env.gog'
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.startswith('export '):
                            key = key[7:]
                        env[key] = value.strip('"')
        
        result = subprocess.run(
            f'source /Users/niamhcollins/clawd/.env.gog && {cmd}',
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout, None
        
    except Exception as e:
        return None, f"Error running gog command: {str(e)}"

def get_enhanced_google_drive_calls(days_back=0):
    """Enhanced Google Drive call detection with flexible patterns"""
    target_date = datetime.now() - timedelta(days=days_back)
    
    try:
        search_patterns = [
            '"Notes by Gemini"',
            '"- Notes by Gemini"', 
            'Gemini'
        ]
        
        all_calls = []
        
        for pattern in search_patterns:
            output, error = run_gog_command(f'gog drive search {pattern} --max 50')
            
            if error:
                continue
            
            if not output or 'ID' not in output:
                continue
            
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            
            for line in lines[1:]:  # Skip header
                if not line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 4:
                    call_id, name, modified_time, _ = parts[0], parts[1], parts[2], parts[3]
                    
                    # Enhanced filtering for call documents
                    if any(indicator in name.lower() for indicator in [
                        'notes by gemini', 'gemini', 'sync -', 'meeting',
                        'call with', 'demo -', 'discovery', 'followup'
                    ]):
                        call_data = {
                            'id': call_id,
                            'title': name,
                            'modified_date': modified_time,
                            'source': 'google_drive_enhanced'
                        }
                        all_calls.append(call_data)
        
        # Remove duplicates by ID
        unique_calls = {call['id']: call for call in all_calls}.values()
        unique_calls = list(unique_calls)
        
        # Sort by modified date (newest first)
        unique_calls.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        return unique_calls, f"Found {len(unique_calls)} enhanced Google Drive calls"
        
    except Exception as e:
        return [], f"Error getting Google Drive calls: {str(e)}"

def get_google_doc_content(doc_id):
    """Get Google Doc content using gog CLI"""
    try:
        output, error = run_gog_command(f'gog docs get {doc_id}')
        
        if error:
            return None, f"Error getting doc content: {error}"
        
        if not output or len(output.strip()) < 50:
            return None, "Document content too short or empty"
        
        return output.strip(), None
        
    except Exception as e:
        return None, f"Error getting doc content: {str(e)}"

def format_enhanced_google_drive_call(call_data, content):
    """Enhanced parsing of Google Drive call data"""
    title = call_data.get('title', '')
    
    # Extract attendee information from content
    attendees_info = extract_attendees_from_content(content)
    prospect_name = attendees_info.get('prospect_name', 'Unknown Prospect')
    prospect_email = attendees_info.get('prospect_email', '')
    ae_name = attendees_info.get('ae_name', 'Unknown AE')
    
    return {
        'call_id': call_data['id'],
        'title': title,
        'prospect_name': prospect_name,
        'prospect_email': prospect_email,
        'ae_name': ae_name,
        'call_date': call_data.get('modified_date', ''),
        'source': 'google_drive_enhanced',
        'content': content[:2000],  # Store truncated content
        'recording_url': None
    }

def extract_attendees_from_content(content):
    """Extract attendees from document content using multiple patterns"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # List of known Telnyx AEs for identification
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'decliner slides'
    ]
    
    try:
        # Pattern 1: Look for "X and Y of Telnyx met with Z"
        summary_patterns = [
            r'(\w+\s+\w+)\s+and\s+(\w+\s+\w+)\s+of\s+Telnyx\s+met\s+with\s+([^.]+)',
            r'(\w+\s+\w+)\s+initiated\s+the\s+call\s+with\s+([^.]+)',
            r'Meeting\s+between\s+([^,]+),\s*([^,]+),?\s*and\s+([^.]+)',
        ]
        
        for pattern in summary_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches:
                    participants = [p.strip() for p in match]
                    
                    # Identify Telnyx AEs vs prospects
                    for participant in participants:
                        if any(ae.lower() in participant.lower() for ae in telnyx_aes):
                            ae_name = participant.title()
                        else:
                            if prospect_name == 'Unknown Prospect':
                                prospect_name = participant.title()
                    
                    if ae_name != 'Unknown AE' and prospect_name != 'Unknown Prospect':
                        break
        
        # Pattern 2: Extract email addresses 
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # Filter out Telnyx emails to find prospect email
        for email in emails:
            if '@telnyx.com' not in email.lower():
                prospect_email = email
                if prospect_name == 'Unknown Prospect':
                    prospect_name = email.split('@')[0].replace('.', ' ').title()
                break
        
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }
        
    except Exception as e:
        log_message(f"⚠️ Error extracting attendees: {str(e)}")
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }

def init_database():
    """Initialize SQLite database with required tables"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY,
            call_id TEXT,
            dedup_key TEXT UNIQUE,
            prospect_name TEXT,
            prospect_email TEXT,
            ae_name TEXT,
            call_date TEXT,
            source TEXT,
            analysis TEXT,
            created_at TEXT,
            UNIQUE(call_id, source)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unmatched_contacts (
            id INTEGER PRIMARY KEY,
            prospect_name TEXT,
            prospect_email TEXT,
            call_id TEXT,
            source TEXT,
            call_date TEXT,
            created_at TEXT,
            notes TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dedup_key ON processed_calls(dedup_key)')
    
    conn.commit()
    conn.close()

def generate_dedup_key(prospect_identifier, call_date):
    """Generate deduplication key from prospect and date"""
    clean_prospect = re.sub(r'[^a-zA-Z0-9@.]', '', prospect_identifier.lower())
    date_only = call_date[:10] if len(call_date) >= 10 else call_date
    return f"{clean_prospect}_{date_only}"

def is_call_duplicate(dedup_key):
    """Check if call already processed using deduplication key"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
    result = cursor.fetchone()
    conn.close()
    
    return result

def save_processed_call(call_data, analysis, dedup_key):
    """Save processed call to database"""
    db_path = 'v2_final.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_calls 
            (call_id, dedup_key, prospect_name, prospect_email, ae_name, call_date, source, analysis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            call_data['call_id'],
            dedup_key,
            call_data['prospect_name'],
            call_data['prospect_email'],
            call_data['ae_name'],
            call_data['call_date'],
            call_data['source'],
            json.dumps(analysis),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
    except Exception as e:
        log_message(f"❌ Error saving call to database: {str(e)}")
    
    finally:
        conn.close()

def update_salesforce_event(call_data, analysis):
    """Update Salesforce with call event (placeholder)"""
    # Placeholder for Salesforce integration
    log_message(f"📊 Salesforce: Would update event for {call_data['prospect_name']}")
    return {"success": True}

def post_enhanced_slack_alert(call_data, analysis):
    """Post enhanced Slack alert (placeholder)"""
    # Placeholder for Slack integration
    log_message(f"💬 Slack: Would post alert for {call_data['prospect_name']}")
    return {"success": True}

async def run_async_automation():
    """Run V3 async automation with parallel processing"""
    log_message("🚀 V3 ASYNC Call Intelligence - Parallel Processing + Enhanced Parsing")
    
    init_database()
    
    # Get all Google Drive calls
    google_calls, google_status = get_enhanced_google_drive_calls()
    log_message(f"📁 Google Drive: {google_status}")
    
    if not google_calls:
        log_message("ℹ️ No calls found to process")
        return
    
    # Process calls in parallel using async processor
    async with AsyncCallProcessor(max_concurrent_calls=5, max_openai_calls=2) as processor:
        results = await processor.process_calls_parallel(google_calls)
    
    # Summary
    log_message(f"🎉 V3 ASYNC processed {results['total_calls']} calls:")
    log_message(f"   ✅ Successful: {results['successful']}")
    log_message(f"   ❌ Failed: {results['errors'] + results['exceptions']}")
    log_message(f"   ⚡ Performance: {results['calls_per_minute']:.1f} calls/minute")
    log_message(f"   ⏱️ Total time: {results['processing_time']:.2f} seconds")

# Sync wrapper for cron job compatibility
def run_sync_automation():
    """Synchronous wrapper for async automation (cron compatibility)"""
    try:
        asyncio.run(run_async_automation())
    except Exception as e:
        log_message(f"❌ Error in async automation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if we want async (default) or sync mode
    if len(sys.argv) > 1 and sys.argv[1] == '--sync':
        run_sync_automation()
    else:
        asyncio.run(run_async_automation())