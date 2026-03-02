"""
Database client for AE Call Analysis System
Handles SQLite operations for calls, analysis, and Salesforce mappings
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class AECallAnalysisDB:
    """SQLite database client for AE call analysis system"""
    
    def __init__(self, db_path: str = "ae_call_analysis.db"):
        self.db_path = Path(db_path)
        self.schema_path = Path(__file__).parent / "schema.sql"
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            self.initialize_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with JSON support"""
        conn = sqlite3.connect(
            self.db_path, 
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def initialize_database(self):
        """Initialize database with schema"""
        logger.info(f"Initializing database at {self.db_path}")
        
        with open(self.schema_path, 'r') as f:
            schema = f.read()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            conn.executescript(schema)
            
            # Ensure enhanced schema updates are applied
            self._ensure_enhanced_analysis_schema(cursor)
            self._ensure_salesforce_mapping_schema(cursor)
            
            conn.commit()
        
        logger.info("Database initialized successfully")
    
    def _ensure_salesforce_mapping_schema(self, cursor):
        """Ensure salesforce_mappings table has all required columns for exact matching"""
        # Check if table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salesforce_mappings'")
        if not cursor.fetchone():
            logger.debug("salesforce_mappings table doesn't exist yet, will be created by schema.sql")
            return
        
        # Check if new columns exist and add them if needed
        cursor.execute("PRAGMA table_info(salesforce_mappings)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        new_columns = {
            'quinn_user_id': 'TEXT',
            'opportunity_created_date': 'DATETIME',
            'confidence_score': 'INTEGER',
            'confidence_reasoning': 'TEXT',
            'duplicate_flag': 'BOOLEAN DEFAULT FALSE'
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                logger.info(f"Adding column {column_name} to salesforce_mappings table")
                cursor.execute(f"ALTER TABLE salesforce_mappings ADD COLUMN {column_name} {column_type}")
        
        # Add indexes for new fields
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sf_mappings_contact_name ON salesforce_mappings(contact_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sf_mappings_confidence_score ON salesforce_mappings(confidence_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sf_mappings_duplicate_flag ON salesforce_mappings(duplicate_flag)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sf_mappings_quinn_user_id ON salesforce_mappings(quinn_user_id)")
        except Exception as e:
            logger.debug(f"Index creation info: {e}")  # Indexes may already exist
    
    def _ensure_enhanced_analysis_schema(self, cursor):
        """Ensure analysis_results table has enhanced Claude metadata columns AND dual-output columns"""
        # Check if table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'")
        if not cursor.fetchone():
            logger.debug("analysis_results table doesn't exist yet, will be created by schema.sql")
            return
        
        # Check if new columns exist and add them if needed
        cursor.execute("PRAGMA table_info(analysis_results)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        new_columns = {
            'token_usage_input': 'INTEGER',
            'token_usage_output': 'INTEGER', 
            'token_usage_total': 'INTEGER',
            'claude_model_used': 'TEXT',
            'analysis_metadata': 'JSON',
            'claude_response_id': 'TEXT',
            'claude_request_timestamp': 'DATETIME',
            # NEW: Dual-output columns for simple summary + detailed analysis
            'simple_summary': 'JSON',
            'detailed_analysis': 'JSON'
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                logger.info(f"Adding column {column_name} to analysis_results table")
                cursor.execute(f"ALTER TABLE analysis_results ADD COLUMN {column_name} {column_type}")
        
        # Add indexes for enhanced analysis fields
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_claude_model ON analysis_results(claude_model_used)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_token_usage ON analysis_results(token_usage_total)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_claude_timestamp ON analysis_results(claude_request_timestamp)")
        except Exception as e:
            logger.debug(f"Index creation info: {e}")  # Indexes may already exist
    
    def log_operation(self, operation_type: str, status: str, start_time: datetime,
                     end_time: datetime = None, records_processed: int = 0,
                     records_succeeded: int = 0, records_failed: int = 0,
                     error_details: str = None, metadata: Dict = None) -> int:
        """Log a processing operation"""
        if end_time is None:
            end_time = datetime.now()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO processing_logs (
                    operation_type, status, start_time, end_time,
                    records_processed, records_succeeded, records_failed,
                    error_details, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation_type, status, start_time, end_time,
                records_processed, records_succeeded, records_failed,
                error_details, json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid
    
    # === CALLS TABLE METHODS ===
    
    def insert_call(self, fellow_id: str, title: str, call_date: datetime,
                   duration_minutes: int = None, ae_name: str = None,
                   prospect_name: str = None, prospect_company: str = None,
                   transcript: str = None, fellow_ai_notes: str = None,
                   raw_fellow_data: Dict = None) -> int:
        """Insert a new call record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO calls (
                    fellow_id, title, call_date, duration_minutes, ae_name,
                    prospect_name, prospect_company, transcript, fellow_ai_notes,
                    raw_fellow_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fellow_id, title, call_date, duration_minutes, ae_name,
                prospect_name, prospect_company, transcript, fellow_ai_notes,
                json.dumps(raw_fellow_data) if raw_fellow_data else None
            ))
            return cursor.lastrowid
    
    def get_call_by_fellow_id(self, fellow_id: str) -> Optional[sqlite3.Row]:
        """Get call by Fellow ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM calls WHERE fellow_id = ?', (fellow_id,))
            return cursor.fetchone()
    
    def get_unprocessed_calls(self, limit: int = 100) -> List[sqlite3.Row]:
        """Get unprocessed calls for analysis"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM unprocessed_calls 
                ORDER BY call_date DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def mark_call_processed(self, call_id: int):
        """Mark a call as processed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE calls SET processed = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (call_id,))
    
    def get_calls_by_date_range(self, start_date: datetime, end_date: datetime) -> List[sqlite3.Row]:
        """Get calls within a date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM calls 
                WHERE call_date BETWEEN ? AND ?
                ORDER BY call_date DESC
            ''', (start_date, end_date))
            return cursor.fetchall()
    
    # === SALESFORCE MAPPINGS METHODS ===
    
    def insert_salesforce_mapping(self, call_id: int, contact_id: str = None,
                                 contact_name: str = None, opportunity_id: str = None,
                                 quinn_active_latest: datetime = None,
                                 contact_match_confidence: int = None,
                                 mapping_method: str = None, quinn_user_id: str = None,
                                 opportunity_created_date: datetime = None,
                                 confidence_score: int = None,
                                 confidence_reasoning: str = None,
                                 duplicate_flag: bool = False) -> int:
        """Insert Salesforce mapping for a call"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if we need to add new columns (for migration support)
            self._ensure_salesforce_mapping_schema(cursor)
            
            cursor.execute('''
                INSERT INTO salesforce_mappings (
                    call_id, contact_id, contact_name, opportunity_id,
                    quinn_active_latest, contact_match_confidence, mapping_method,
                    quinn_user_id, opportunity_created_date, confidence_score,
                    confidence_reasoning, duplicate_flag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                call_id, contact_id, contact_name, opportunity_id,
                quinn_active_latest, contact_match_confidence, mapping_method,
                quinn_user_id, opportunity_created_date, confidence_score,
                confidence_reasoning, duplicate_flag
            ))
            return cursor.lastrowid
    
    def get_salesforce_mapping(self, call_id: int) -> Optional[sqlite3.Row]:
        """Get Salesforce mapping for a call"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM salesforce_mappings WHERE call_id = ?
            ''', (call_id,))
            return cursor.fetchone()
    
    # === ANALYSIS RESULTS METHODS ===
    
    def insert_analysis_result(self, call_id: int, analysis_data: Dict) -> int:
        """Insert LLM analysis result with enhanced Claude metadata AND dual-output support"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure enhanced schema is applied (includes dual-output columns)
            self._ensure_enhanced_analysis_schema(cursor)
            
            # Extract enhanced metadata
            metadata = analysis_data.get('metadata', {})
            # Also check analysis_metadata for OpenAI dual-output format
            if not metadata:
                metadata = analysis_data.get('analysis_metadata', {})
            token_usage = metadata.get('token_usage', {})
            
            # Extract dual-output structures if present
            simple_summary = analysis_data.get('simple_summary', {})
            detailed_analysis = analysis_data.get('detailed_analysis', {})
            
            cursor.execute('''
                INSERT INTO analysis_results (
                    call_id, analysis_version, core_talking_points, telnyx_products,
                    use_cases, conversation_focus_primary, conversation_focus_secondary,
                    time_distribution, ae_excitement_level, ae_confidence_level,
                    ae_sentiment_notes, prospect_interest_level, prospect_engagement_level,
                    prospect_buying_signals, prospect_concerns, next_steps_category,
                    next_steps_actions, next_steps_timeline, next_steps_probability,
                    quinn_qualification_quality, quinn_missed_opportunities,
                    quinn_strengths, analysis_confidence, llm_model_used,
                    processing_time_seconds, token_usage_input, token_usage_output,
                    token_usage_total, claude_model_used, analysis_metadata,
                    claude_response_id, claude_request_timestamp,
                    simple_summary, detailed_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                call_id,
                analysis_data.get('analysis_version', '1.0'),
                json.dumps(analysis_data.get('core_talking_points', [])),
                json.dumps(analysis_data.get('telnyx_products', [])),
                json.dumps(analysis_data.get('use_cases', [])),
                analysis_data.get('conversation_focus', {}).get('primary'),
                json.dumps(analysis_data.get('conversation_focus', {}).get('secondary', [])),
                json.dumps(analysis_data.get('conversation_focus', {}).get('time_distribution', {})),
                analysis_data.get('ae_sentiment', {}).get('excitement_level'),
                analysis_data.get('ae_sentiment', {}).get('confidence_level'),
                analysis_data.get('ae_sentiment', {}).get('notes'),
                analysis_data.get('prospect_sentiment', {}).get('interest_level') or analysis_data.get('prospect_sentiment', {}).get('excitement_level'),
                analysis_data.get('prospect_sentiment', {}).get('engagement_level'),
                json.dumps(analysis_data.get('prospect_sentiment', {}).get('buying_signals', [])),
                json.dumps(analysis_data.get('prospect_sentiment', {}).get('concerns', [])),
                analysis_data.get('next_steps', {}).get('category'),
                json.dumps(analysis_data.get('next_steps', {}).get('specific_actions', [])),
                analysis_data.get('next_steps', {}).get('timeline'),
                analysis_data.get('next_steps', {}).get('probability'),
                analysis_data.get('quinn_insights', {}).get('qualification_quality'),
                json.dumps(analysis_data.get('quinn_insights', {}).get('missed_opportunities', [])),
                json.dumps(analysis_data.get('quinn_insights', {}).get('strengths', [])),
                metadata.get('analysis_confidence') or analysis_data.get('analysis_metadata', {}).get('analysis_confidence'),
                metadata.get('llm_model_used') or analysis_data.get('analysis_metadata', {}).get('llm_model_used'),
                metadata.get('processing_time_seconds') or analysis_data.get('analysis_metadata', {}).get('processing_time_seconds'),
                # Enhanced Claude metadata
                token_usage.get('input_tokens'),
                token_usage.get('output_tokens'), 
                token_usage.get('total_tokens'),
                metadata.get('claude_model_used') or metadata.get('llm_model_used'),
                json.dumps(metadata.get('analysis_metadata', {}) or analysis_data.get('analysis_metadata', {})),
                metadata.get('claude_response_id'),
                metadata.get('claude_request_timestamp'),
                # NEW: Dual-output columns
                json.dumps(simple_summary) if simple_summary else None,
                json.dumps(detailed_analysis) if detailed_analysis else None
            ))
            return cursor.lastrowid
    
    def get_analysis_result(self, call_id: int) -> Optional[sqlite3.Row]:
        """Get analysis result for a call"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM analysis_results WHERE call_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (call_id,))
            return cursor.fetchone()
    
    def get_analysis_with_metadata(self, call_id: int) -> Optional[sqlite3.Row]:
        """Get analysis result with enhanced Claude metadata"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT *, 
                       token_usage_input,
                       token_usage_output,
                       token_usage_total,
                       claude_model_used,
                       analysis_metadata,
                       claude_response_id,
                       claude_request_timestamp,
                       simple_summary,
                       detailed_analysis
                FROM analysis_results 
                WHERE call_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (call_id,))
            return cursor.fetchone()
    
    def get_dual_output_analysis(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis result with both simple summary and detailed analysis"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    id,
                    call_id,
                    analysis_version,
                    simple_summary,
                    detailed_analysis,
                    core_talking_points,
                    telnyx_products,
                    use_cases,
                    ae_excitement_level,
                    ae_confidence_level,
                    prospect_interest_level,
                    prospect_engagement_level,
                    next_steps_category,
                    quinn_qualification_quality,
                    analysis_confidence,
                    llm_model_used,
                    processing_time_seconds,
                    created_at
                FROM analysis_results 
                WHERE call_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (call_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            result = dict(row)
            
            # Parse JSON fields
            if result.get('simple_summary'):
                result['simple_summary'] = json.loads(result['simple_summary'])
            if result.get('detailed_analysis'):
                result['detailed_analysis'] = json.loads(result['detailed_analysis'])
            if result.get('core_talking_points'):
                result['core_talking_points'] = json.loads(result['core_talking_points'])
            if result.get('telnyx_products'):
                result['telnyx_products'] = json.loads(result['telnyx_products'])
            if result.get('use_cases'):
                result['use_cases'] = json.loads(result['use_cases'])
            
            return result
    
    def get_simple_summary(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get just the simple 9-category summary for quick access"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    simple_summary,
                    analysis_version,
                    analysis_confidence,
                    llm_model_used,
                    created_at
                FROM analysis_results 
                WHERE call_id = ? AND simple_summary IS NOT NULL
                ORDER BY created_at DESC LIMIT 1
            ''', (call_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            result = dict(row)
            if result.get('simple_summary'):
                result['simple_summary'] = json.loads(result['simple_summary'])
            
            return result
    
    def get_token_usage_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get Claude token usage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    claude_model_used,
                    COUNT(*) as analysis_count,
                    SUM(token_usage_total) as total_tokens,
                    AVG(token_usage_total) as avg_tokens_per_analysis,
                    SUM(token_usage_input) as total_input_tokens,
                    SUM(token_usage_output) as total_output_tokens
                FROM analysis_results 
                WHERE created_at >= datetime('now', '-{} days')
                  AND token_usage_total IS NOT NULL
                GROUP BY claude_model_used
                ORDER BY total_tokens DESC
            '''.format(days))
            
            stats = [dict(row) for row in cursor.fetchall()]
            
            # Overall totals
            cursor.execute('''
                SELECT 
                    SUM(token_usage_total) as total_tokens,
                    COUNT(*) as total_analyses,
                    AVG(token_usage_total) as avg_tokens
                FROM analysis_results 
                WHERE created_at >= datetime('now', '-{} days')
                  AND token_usage_total IS NOT NULL
            '''.format(days))
            
            totals = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            return {
                'timeframe_days': days,
                'by_model': stats,
                'totals': totals,
                'generated_at': datetime.now().isoformat()
            }
    
    def get_recent_analysis_summary(self, days: int = 7, limit: int = 50) -> List[sqlite3.Row]:
        """Get recent analysis summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM recent_analysis_summary
                WHERE call_date >= date('now', '-{} days')
                ORDER BY call_date DESC
                LIMIT ?
            '''.format(days), (limit,))
            return cursor.fetchall()
    
    # === SLACK NOTIFICATIONS METHODS ===
    
    def insert_slack_notification(self, call_id: int, channel: str, 
                                 notification_type: str, message_ts: str = None,
                                 message_preview: str = None) -> int:
        """Record a Slack notification"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO slack_notifications (
                    call_id, channel, message_ts, notification_type, message_preview
                ) VALUES (?, ?, ?, ?, ?)
            ''', (call_id, channel, message_ts, notification_type, message_preview))
            return cursor.lastrowid
    
    def get_slack_notifications(self, call_id: int) -> List[sqlite3.Row]:
        """Get Slack notifications for a call"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM slack_notifications 
                WHERE call_id = ? 
                ORDER BY sent_at DESC
            ''', (call_id,))
            return cursor.fetchall()
    
    # === QUINN LEARNING METHODS ===
    
    def insert_quinn_feedback(self, call_id: int, analysis_result_id: int,
                             feedback_type: str, feedback_data: Dict,
                             provided_by: str, feedback_source: str) -> int:
        """Insert Quinn learning feedback"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quinn_learning_feedback (
                    call_id, analysis_result_id, feedback_type, feedback_data,
                    provided_by, feedback_source
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                call_id, analysis_result_id, feedback_type,
                json.dumps(feedback_data), provided_by, feedback_source
            ))
            return cursor.lastrowid
    
    def get_quinn_learning_insights(self) -> List[sqlite3.Row]:
        """Get Quinn learning insights summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM quinn_learning_insights')
            return cursor.fetchall()
    
    # === UTILITY METHODS ===
    
    def insert_enhanced_analysis_result(self, call_id: int, analysis_data: Dict,
                                       token_usage: Dict = None, claude_metadata: Dict = None) -> int:
        """Insert analysis result with enhanced Claude metadata (convenience method)"""
        # Merge enhanced metadata into analysis_data
        enhanced_data = analysis_data.copy()
        metadata = enhanced_data.setdefault('metadata', {})
        
        if token_usage:
            metadata['token_usage'] = token_usage
            
        if claude_metadata:
            metadata.update(claude_metadata)
        
        return self.insert_analysis_result(call_id, enhanced_data)
    
    def get_processing_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing statistics for the last N hours with enhanced Claude metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total calls processed
            cursor.execute('''
                SELECT COUNT(*) as total_calls, 
                       COUNT(CASE WHEN processed THEN 1 END) as processed_calls
                FROM calls 
                WHERE created_at >= datetime('now', '-{} hours')
            '''.format(hours))
            call_stats = cursor.fetchone()
            
            # Processing operations
            cursor.execute('''
                SELECT operation_type, status, COUNT(*) as count
                FROM processing_logs 
                WHERE start_time >= datetime('now', '-{} hours')
                GROUP BY operation_type, status
            '''.format(hours))
            operation_stats = cursor.fetchall()
            
            # Average analysis scores
            cursor.execute('''
                SELECT AVG(ae_excitement_level) as avg_ae_excitement,
                       AVG(prospect_interest_level) as avg_prospect_interest,
                       AVG(quinn_qualification_quality) as avg_quinn_quality,
                       AVG(analysis_confidence) as avg_analysis_confidence
                FROM analysis_results ar
                JOIN calls c ON ar.call_id = c.id
                WHERE c.call_date >= datetime('now', '-{} hours')
            '''.format(hours))
            score_stats = cursor.fetchone()
            
            # Enhanced Claude token usage stats for the timeframe
            cursor.execute('''
                SELECT SUM(token_usage_total) as total_tokens_used,
                       AVG(token_usage_total) as avg_tokens_per_analysis,
                       COUNT(CASE WHEN claude_model_used IS NOT NULL THEN 1 END) as claude_analyses_count,
                       AVG(processing_time_seconds) as avg_processing_time
                FROM analysis_results ar
                JOIN calls c ON ar.call_id = c.id
                WHERE c.call_date >= datetime('now', '-{} hours')
            '''.format(hours))
            claude_stats = cursor.fetchone()
            
            return {
                'timeframe_hours': hours,
                'calls': dict(call_stats) if call_stats else {},
                'operations': [dict(row) for row in operation_stats],
                'average_scores': dict(score_stats) if score_stats else {},
                'claude_usage': dict(claude_stats) if claude_stats else {},
                'generated_at': datetime.now().isoformat()
            }
    
    def cleanup_old_data(self, retention_days: int = 90):
        """Clean up old data beyond retention period"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean up old processing logs
            cursor.execute('''
                DELETE FROM processing_logs 
                WHERE start_time < ?
            ''', (cutoff_date,))
            logs_deleted = cursor.rowcount
            
            # Clean up old notifications (keep call data)
            cursor.execute('''
                DELETE FROM slack_notifications 
                WHERE sent_at < ?
            ''', (cutoff_date,))
            notifications_deleted = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Cleaned up {logs_deleted} old logs, {notifications_deleted} old notifications")
            return logs_deleted, notifications_deleted
    
    def calculate_confidence_score(self, contact_found: bool = False, has_quinn_data: bool = False,
                                 has_opportunity: bool = False, opportunity_in_window: bool = False,
                                 has_event_record: bool = False, exact_name_match: bool = False,
                                 duplicate_contacts: bool = False) -> tuple[int, str]:
        """Calculate confidence score and reasoning based on available data"""
        if not contact_found:
            return 0, "No contact found"
        
        if has_event_record:
            return 10, "Event record exists with matching WhoId and Subject"
        
        if has_opportunity and opportunity_in_window and has_quinn_data:
            return 9, "Contact + Quinn opportunity + 14-day window match"
        
        if has_opportunity and has_quinn_data:
            return 8, "Contact + Quinn opportunity (outside 14-day window)"
        
        if has_quinn_data and exact_name_match:
            score = 6 if not duplicate_contacts else 5
            reason = "Contact + Quinn latest date exists"
            if duplicate_contacts:
                reason += " (multiple matches found)"
            return score, reason
        
        if exact_name_match:
            return 3, "Contact found with exact name match, no Quinn validation data"
        
        return 1, "Contact found but poor match quality"


# Database singleton instance
_db_instance = None

def get_db(db_path: str = None) -> AECallAnalysisDB:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = AECallAnalysisDB(db_path or "ae_call_analysis.db")
    return _db_instance