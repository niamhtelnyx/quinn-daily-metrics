#!/usr/bin/env python3
"""
Fellow Call Intelligence Cron Job - V1
Queries Fellow API every 30 minutes, processes new calls through enhanced pipeline
"""

import requests
import sqlite3
import json
import os
from datetime import datetime, timedelta
from enhanced_call_processor import EnhancedCallProcessor
import time

class FellowCronProcessor:
    """30-minute Fellow polling with enhanced call intelligence pipeline"""
    
    def __init__(self):
        self.fellow_api_key = os.getenv('FELLOW_API_KEY')
        self.fellow_endpoint = 'https://telnyx.fellow.app/api/v1/recordings'
        self.database_path = 'ae_call_analysis.db'
        self.processor = EnhancedCallProcessor()
        self.setup_database()
    
    def setup_database(self):
        """Ensure database and tracking table exist"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create cron job tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cron_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp TEXT NOT NULL,
            recordings_fetched INTEGER DEFAULT 0,
            new_calls_processed INTEGER DEFAULT 0,
            errors TEXT,
            status TEXT DEFAULT 'running'
        )
        ''')
        
        # Ensure calls table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fellow_id TEXT UNIQUE,
            prospect_name TEXT,
            ae_name TEXT,
            title TEXT,
            call_date TEXT,
            prospect_company TEXT,
            transcript TEXT,
            fellow_ai_notes TEXT,
            raw_fellow_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed_by_enhanced BOOLEAN DEFAULT FALSE
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database setup complete")
    
    def get_last_cron_run_time(self):
        """Get the timestamp of the last successful cron run"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT run_timestamp FROM cron_runs 
        WHERE status = 'completed' 
        ORDER BY run_timestamp DESC 
        LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Parse the timestamp and return datetime
            return datetime.fromisoformat(result[0])
        else:
            # First run - get calls from last 24 hours
            return datetime.now() - timedelta(hours=24)
    
    def fetch_fellow_recordings(self, since_timestamp=None):
        """Fetch recordings from Fellow API"""
        print(f"📡 Fetching Fellow recordings...")
        
        headers = {
            'Authorization': f'Bearer {self.fellow_api_key}',
            'Content-Type': 'application/json'
        }
        
        recordings = []
        
        # Fetch multiple pages to get more recordings
        for page in range(1, 6):  # Up to 5 pages (100 recordings)
            page_params = {"page": page} if page > 1 else {}
            
            try:
                response = requests.post(
                    self.fellow_endpoint,
                    headers=headers,
                    json=page_params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    page_recordings = data.get('recordings', {}).get('data', [])
                    
                    if not page_recordings:
                        break
                    
                    recordings.extend(page_recordings)
                    print(f"   📄 Page {page}: {len(page_recordings)} recordings")
                    
                elif response.status_code == 401:
                    raise Exception(f"Fellow API authentication failed. Check FELLOW_API_KEY environment variable.")
                else:
                    raise Exception(f"Fellow API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Error fetching page {page}: {str(e)}")
                if page == 1:  # If first page fails, abort
                    raise
                else:
                    break  # If later page fails, continue with what we have
        
        # Filter recordings by timestamp if provided
        if since_timestamp:
            filtered_recordings = []
            for recording in recordings:
                created_at = recording.get('created_at')
                if created_at:
                    try:
                        # Parse Fellow timestamp (adjust format as needed)
                        recording_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if recording_time > since_timestamp:
                            filtered_recordings.append(recording)
                    except ValueError:
                        # If timestamp parsing fails, include the recording
                        filtered_recordings.append(recording)
            
            print(f"   🔍 Filtered to {len(filtered_recordings)} new recordings since {since_timestamp}")
            return filtered_recordings
        
        print(f"✅ Fetched {len(recordings)} total recordings")
        return recordings
    
    def extract_prospect_name(self, title):
        """Extract prospect name from Fellow call title"""
        # Handle various Fellow title formats
        if '(' in title and ')' in title:
            # "Call with John Smith (TechCorp)" -> "John Smith"
            before_paren = title.split('(')[0].strip()
            # Remove common prefixes
            prefixes = ['call with', 'meeting with', 'demo with', 'intro call', 'telnyx intro call']
            for prefix in prefixes:
                if before_paren.lower().startswith(prefix):
                    return before_paren[len(prefix):].strip()
            return before_paren
        
        # Simple fallback
        return title.split('-')[0].strip() if '-' in title else title.strip()
    
    def store_fellow_call(self, recording):
        """Store a new Fellow call in database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        fellow_id = recording.get('event_guid') or recording.get('id', f"unknown_{int(time.time())}")
        title = recording.get('title', 'Untitled Call')
        prospect_name = self.extract_prospect_name(title)
        
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO calls (
                fellow_id, prospect_name, title, call_date, transcript,
                fellow_ai_notes, raw_fellow_data, created_at, processed_by_enhanced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fellow_id,
                prospect_name,
                title,
                recording.get('created_at'),
                recording.get('transcript', ''),
                recording.get('ai_notes', ''),
                json.dumps(recording),
                datetime.now().isoformat(),
                False  # Will be processed by enhanced pipeline
            ))
            
            conn.commit()
            
            # Get the call ID
            cursor.execute('SELECT id FROM calls WHERE fellow_id = ?', (fellow_id,))
            result = cursor.fetchone()
            call_id = result[0] if result else None
            
            conn.close()
            
            if call_id:
                print(f"   📞 Stored call {call_id}: {prospect_name}")
                return call_id
            else:
                print(f"   ⚠️ Call already exists: {prospect_name}")
                return None
                
        except Exception as e:
            conn.close()
            print(f"   ❌ Error storing call: {str(e)}")
            return None
    
    def process_new_calls(self, call_ids):
        """Process new calls through enhanced pipeline"""
        print(f"🔄 Processing {len(call_ids)} new calls through enhanced pipeline...")
        
        processed_count = 0
        for call_id in call_ids:
            try:
                print(f"\n🚀 Processing call {call_id}...")
                result = self.processor.process_call_with_salesforce_lookup(call_id)
                
                if result.get('success'):
                    # Mark as processed
                    conn = sqlite3.connect(self.database_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE calls SET processed_by_enhanced = TRUE WHERE id = ?', (call_id,))
                    conn.commit()
                    conn.close()
                    
                    processed_count += 1
                    print(f"✅ Call {call_id} processed successfully")
                else:
                    print(f"❌ Call {call_id} processing failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                print(f"❌ Error processing call {call_id}: {str(e)}")
        
        print(f"✅ Enhanced processing complete: {processed_count}/{len(call_ids)} calls processed")
        return processed_count
    
    def log_cron_run(self, recordings_fetched, new_calls_processed, errors=None, status='completed'):
        """Log the cron run results"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO cron_runs (
            run_timestamp, recordings_fetched, new_calls_processed, errors, status
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            recordings_fetched,
            new_calls_processed,
            errors,
            status
        ))
        
        conn.commit()
        conn.close()
    
    def run_cron_cycle(self):
        """Execute a single cron cycle"""
        start_time = datetime.now()
        print(f"\n🕐 Starting Fellow Cron Job - {start_time}")
        print("=" * 60)
        
        try:
            # Get last run timestamp
            last_run = self.get_last_cron_run_time()
            print(f"⏰ Last run: {last_run}")
            print(f"📊 Looking for new calls since then...")
            
            # Fetch recordings from Fellow
            recordings = self.fetch_fellow_recordings(since_timestamp=last_run)
            
            if not recordings:
                print("📭 No new recordings found")
                self.log_cron_run(0, 0)
                return
            
            # Store new calls in database
            print(f"\n💾 Storing {len(recordings)} new recordings...")
            new_call_ids = []
            
            for recording in recordings:
                call_id = self.store_fellow_call(recording)
                if call_id:
                    new_call_ids.append(call_id)
            
            if not new_call_ids:
                print("📝 All recordings were already in database")
                self.log_cron_run(len(recordings), 0)
                return
            
            # Process through enhanced pipeline
            processed_count = self.process_new_calls(new_call_ids)
            
            # Log successful run
            self.log_cron_run(len(recordings), processed_count)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n✅ Cron cycle completed in {duration:.1f} seconds")
            print(f"📊 Summary:")
            print(f"   • Recordings fetched: {len(recordings)}")
            print(f"   • New calls stored: {len(new_call_ids)}")
            print(f"   • Calls processed: {processed_count}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Cron cycle failed: {error_msg}")
            self.log_cron_run(0, 0, error_msg, 'failed')
            raise

def main():
    """Main entry point for cron job"""
    print("🚀 Fellow Call Intelligence Cron Job - V1")
    print("⏰ 30-minute polling with enhanced pipeline integration")
    print()
    
    processor = FellowCronProcessor()
    
    # Check if running as one-off or continuous
    if os.getenv('CRON_MODE') == 'continuous':
        print("🔄 Running in continuous mode (for testing)")
        while True:
            try:
                processor.run_cron_cycle()
                print(f"😴 Sleeping for 30 minutes...")
                time.sleep(30 * 60)  # 30 minutes
            except KeyboardInterrupt:
                print("\n⏸️ Stopped by user")
                break
            except Exception as e:
                print(f"💥 Unexpected error: {str(e)}")
                print("😴 Sleeping 5 minutes before retry...")
                time.sleep(5 * 60)
    else:
        # Single run (normal cron mode)
        processor.run_cron_cycle()

if __name__ == "__main__":
    main()