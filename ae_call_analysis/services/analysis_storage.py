"""
Analysis storage service with transaction safety and comprehensive data validation
Provides ACID compliant storage for LLM analysis results with error tracking and recovery
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager

try:
    from ..database.database import get_db
    from ..config.settings import get_config
    from ..models.analysis_schema import CallAnalysisResult, validate_analysis_result
    from ..models.processing_queue import QueueStatus, QueueMetrics, RetryCategory
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from database.database import get_db
    from config.settings import get_config
    from models.analysis_schema import CallAnalysisResult, validate_analysis_result
    from models.processing_queue import QueueStatus, QueueMetrics, RetryCategory

logger = logging.getLogger(__name__)

@dataclass
class StorageResult:
    """Result of storage operation"""
    success: bool
    analysis_id: Optional[int] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

@dataclass
class RetryCandidate:
    """Candidate for retry processing"""
    call_id: int
    fellow_id: str
    retry_count: int
    last_error: str
    queued_at: datetime
    priority: int

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass

class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class AnalysisStorageService:
    """
    Comprehensive analysis storage service with ACID transactions, 
    data validation, and error recovery
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.db = get_db()
        self._connection_pool = None
        
        # Storage metrics
        self.storage_count = 0
        self.validation_errors_count = 0
        self.database_errors_count = 0
        
        logger.info("Initialized AnalysisStorageService")
    
    async def initialize_schema(self) -> bool:
        """Initialize/update database schema for enhanced LLM analysis storage"""
        try:
            # Check if enhanced tables exist, create if needed
            await self._create_enhanced_tables()
            logger.info("Database schema initialization completed")
            return True
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            return False
    
    async def store_analysis_result(
        self, 
        call_id: int, 
        analysis: Union[Dict[str, Any], CallAnalysisResult]
    ) -> StorageResult:
        """
        Store analysis result with comprehensive validation and transaction safety
        
        Args:
            call_id: ID of the call being analyzed
            analysis: Analysis result (dict or Pydantic model)
            
        Returns:
            StorageResult with success status and analysis ID or error details
        """
        start_time = datetime.now()
        
        try:
            # Validate and convert to standard format
            if isinstance(analysis, dict):
                validated_analysis = validate_analysis_result(analysis)
            elif isinstance(analysis, CallAnalysisResult):
                validated_analysis = analysis
            else:
                raise ValidationError(f"Invalid analysis type: {type(analysis)}")
            
            # Convert to database JSON format
            analysis_data = validated_analysis.to_database_json()
            
            # Store with transaction safety
            async with self._get_transaction() as tx:
                # Insert main analysis result
                analysis_id = await self._insert_analysis_result(
                    tx, call_id, analysis_data, validated_analysis.analysis_metadata
                )
                
                # Update call processing status
                await self._update_call_status(tx, call_id, 'completed', analysis_id)
                
                # Record processing metrics
                processing_time = (datetime.now() - start_time).total_seconds()
                await self._record_processing_metrics(
                    tx, call_id, 'complete_analysis', processing_time, True
                )
                
                # Commit transaction
                await tx.commit()
            
            self.storage_count += 1
            logger.info(f"✅ Analysis result stored successfully for call {call_id}, ID: {analysis_id}")
            
            return StorageResult(
                success=True,
                analysis_id=analysis_id
            )
            
        except ValidationError as e:
            self.validation_errors_count += 1
            logger.error(f"❌ Validation error for call {call_id}: {e}")
            
            # Store validation error for debugging
            await self._log_validation_error(call_id, str(e), analysis if isinstance(analysis, dict) else None)
            
            return StorageResult(
                success=False,
                error_message=f"Validation error: {str(e)}",
                validation_errors=[str(e)]
            )
            
        except Exception as e:
            self.database_errors_count += 1
            logger.error(f"❌ Storage error for call {call_id}: {e}")
            
            # Log database error
            await self._log_processing_error(call_id, "database_error", str(e))
            
            return StorageResult(
                success=False,
                error_message=f"Storage error: {str(e)}"
            )
    
    async def get_analysis_by_call(self, call_id: int) -> Optional[CallAnalysisResult]:
        """Retrieve analysis result for a specific call"""
        try:
            query = """
            SELECT analysis_data, analysis_version, processing_time_seconds, 
                   token_usage, created_at
            FROM llm_analysis_results 
            WHERE call_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """
            
            result = self.db.fetch_one(query, (call_id,))
            
            if result:
                analysis_data = json.loads(result['analysis_data'])
                
                # Add metadata from database
                if 'analysis_metadata' not in analysis_data:
                    analysis_data['analysis_metadata'] = {}
                
                analysis_data['analysis_metadata'].update({
                    'analysis_version': result['analysis_version'],
                    'processing_time_seconds': result['processing_time_seconds'],
                    'token_usage': json.loads(result['token_usage']) if result['token_usage'] else {},
                    'stored_at': result['created_at']
                })
                
                return CallAnalysisResult(**analysis_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving analysis for call {call_id}: {e}")
            return None
    
    async def update_queue_status(
        self, 
        call_id: int, 
        status: QueueStatus, 
        error_message: Optional[str] = None
    ) -> bool:
        """Update queue processing status for a call"""
        try:
            if status == QueueStatus.COMPLETED:
                query = """
                UPDATE analysis_processing_queue 
                SET queue_status = ?, completed_at = ?, last_error = NULL 
                WHERE call_id = ?
                """
                self.db.execute(query, (status.value, datetime.now(), call_id))
            
            elif status == QueueStatus.FAILED:
                query = """
                UPDATE analysis_processing_queue 
                SET queue_status = ?, last_error = ?, retry_count = retry_count + 1 
                WHERE call_id = ?
                """
                self.db.execute(query, (status.value, error_message, call_id))
            
            elif status == QueueStatus.PROCESSING:
                query = """
                UPDATE analysis_processing_queue 
                SET queue_status = ?, started_at = ? 
                WHERE call_id = ?
                """
                self.db.execute(query, (status.value, datetime.now(), call_id))
            
            else:  # PENDING, RETRYING
                query = """
                UPDATE analysis_processing_queue 
                SET queue_status = ? 
                WHERE call_id = ?
                """
                self.db.execute(query, (status.value, call_id))
            
            logger.debug(f"Updated queue status for call {call_id} to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating queue status for call {call_id}: {e}")
            return False
    
    async def log_processing_error(
        self, 
        call_id: int, 
        error_category: str, 
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        retry_attempt: Optional[int] = None
    ) -> bool:
        """Log processing error for monitoring and recovery"""
        try:
            query = """
            INSERT INTO llm_processing_errors 
            (call_id, error_category, error_message, error_details, retry_attempt, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute(query, (
                call_id,
                error_category,
                error_message,
                json.dumps(error_details) if error_details else None,
                retry_attempt,
                datetime.now()
            ))
            
            logger.debug(f"Logged error for call {call_id}: {error_category}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging processing error for call {call_id}: {e}")
            return False
    
    async def record_processing_metrics(
        self,
        call_id: int,
        stage: str,
        duration_seconds: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record processing metrics for performance monitoring"""
        try:
            query = """
            INSERT INTO processing_metrics 
            (call_id, stage, start_time, end_time, duration_seconds, success, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=duration_seconds)
            
            self.db.execute(query, (
                call_id,
                stage,
                start_time,
                end_time,
                duration_seconds,
                success,
                json.dumps(metadata) if metadata else None
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording metrics for call {call_id}: {e}")
            return False
    
    async def get_retry_candidates(
        self, 
        max_retry_count: int = 3,
        min_age_minutes: int = 5
    ) -> List[RetryCandidate]:
        """Get calls that are candidates for retry processing"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=min_age_minutes)
            
            query = """
            SELECT apq.call_id, c.fellow_id, apq.retry_count, apq.last_error, 
                   apq.queued_at, apq.priority
            FROM analysis_processing_queue apq
            JOIN calls c ON apq.call_id = c.id
            WHERE apq.queue_status = 'failed' 
              AND apq.retry_count < ?
              AND apq.queued_at < ?
            ORDER BY apq.priority ASC, apq.queued_at ASC
            LIMIT 50
            """
            
            results = self.db.fetch_all(query, (max_retry_count, cutoff_time))
            
            candidates = []
            for row in results:
                candidates.append(RetryCandidate(
                    call_id=row['call_id'],
                    fellow_id=row['fellow_id'],
                    retry_count=row['retry_count'],
                    last_error=row['last_error'],
                    queued_at=row['queued_at'],
                    priority=row['priority']
                ))
            
            logger.info(f"Found {len(candidates)} retry candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting retry candidates: {e}")
            return []
    
    async def get_queue_status(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get current queue status for a specific call"""
        try:
            query = """
            SELECT queue_status, priority, retry_count, last_error, 
                   queued_at, started_at, completed_at
            FROM analysis_processing_queue 
            WHERE call_id = ?
            """
            
            result = self.db.fetch_one(query, (call_id,))
            
            if result:
                return {
                    'call_id': call_id,
                    'status': result['queue_status'],
                    'priority': result['priority'],
                    'retry_count': result['retry_count'],
                    'last_error': result['last_error'],
                    'queued_at': result['queued_at'],
                    'started_at': result['started_at'],
                    'completed_at': result['completed_at']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting queue status for call {call_id}: {e}")
            return None
    
    async def cleanup_old_data(self, retention_days: int = 90) -> Dict[str, int]:
        """Clean up old processing data and errors"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleanup_stats = {
            'errors_cleaned': 0,
            'metrics_cleaned': 0,
            'completed_queue_items_cleaned': 0
        }
        
        try:
            # Clean up old errors
            result = self.db.execute(
                "DELETE FROM llm_processing_errors WHERE occurred_at < ?",
                (cutoff_date,)
            )
            cleanup_stats['errors_cleaned'] = result.rowcount
            
            # Clean up old metrics
            result = self.db.execute(
                "DELETE FROM processing_metrics WHERE end_time < ?",
                (cutoff_date,)
            )
            cleanup_stats['metrics_cleaned'] = result.rowcount
            
            # Clean up completed queue items
            result = self.db.execute(
                "DELETE FROM analysis_processing_queue WHERE queue_status = 'completed' AND completed_at < ?",
                (cutoff_date,)
            )
            cleanup_stats['completed_queue_items_cleaned'] = result.rowcount
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return cleanup_stats
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get current storage service statistics"""
        try:
            # Get queue statistics
            queue_stats = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total_items,
                    SUM(CASE WHEN queue_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN queue_status = 'processing' THEN 1 ELSE 0 END) as processing,
                    SUM(CASE WHEN queue_status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN queue_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM analysis_processing_queue
            """)
            
            # Get error statistics
            error_stats = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total_errors,
                    COUNT(CASE WHEN occurred_at > datetime('now', '-1 hour') THEN 1 END) as errors_last_hour,
                    COUNT(CASE WHEN occurred_at > datetime('now', '-1 day') THEN 1 END) as errors_last_day
                FROM llm_processing_errors
            """)
            
            # Get analysis statistics
            analysis_stats = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total_analyses,
                    AVG(processing_time_seconds) as avg_processing_time,
                    COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as analyses_last_day
                FROM llm_analysis_results
            """)
            
            return {
                'storage_service': {
                    'storage_count': self.storage_count,
                    'validation_errors_count': self.validation_errors_count,
                    'database_errors_count': self.database_errors_count
                },
                'queue_statistics': dict(queue_stats) if queue_stats else {},
                'error_statistics': dict(error_stats) if error_stats else {},
                'analysis_statistics': dict(analysis_stats) if analysis_stats else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    
    @asynccontextmanager
    async def _get_transaction(self):
        """Get database transaction context manager"""
        # Note: This is a simplified transaction manager
        # In production, would use proper async database connection pooling
        transaction = self.db.begin_transaction()
        try:
            yield transaction
        except Exception:
            await transaction.rollback()
            raise
        else:
            await transaction.commit()
    
    async def _create_enhanced_tables(self) -> None:
        """Create enhanced database tables for LLM analysis"""
        # Note: In production, would use proper database migration system
        
        tables_sql = [
            # Enhanced analysis results table
            """
            CREATE TABLE IF NOT EXISTS llm_analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL,
                analysis_version VARCHAR(50) NOT NULL,
                analysis_data TEXT NOT NULL,
                confidence_score INTEGER CHECK (confidence_score >= 1 AND confidence_score <= 10),
                processing_time_seconds REAL,
                token_usage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (call_id) REFERENCES calls(id)
            )
            """,
            
            # Processing queue table  
            """
            CREATE TABLE IF NOT EXISTS analysis_processing_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL,
                queue_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (call_id) REFERENCES calls(id)
            )
            """,
            
            # Error tracking table
            """
            CREATE TABLE IF NOT EXISTS llm_processing_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL,
                error_category VARCHAR(50) NOT NULL,
                error_message TEXT NOT NULL,
                error_details TEXT,
                retry_attempt INTEGER,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (call_id) REFERENCES calls(id)
            )
            """,
            
            # Performance metrics table
            """
            CREATE TABLE IF NOT EXISTS processing_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL,
                stage VARCHAR(50) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                duration_seconds REAL NOT NULL,
                success BOOLEAN NOT NULL,
                metadata TEXT,
                FOREIGN KEY (call_id) REFERENCES calls(id)
            )
            """
        ]
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_llm_analysis_call_id ON llm_analysis_results(call_id)",
            "CREATE INDEX IF NOT EXISTS idx_llm_analysis_confidence ON llm_analysis_results(confidence_score)",
            "CREATE INDEX IF NOT EXISTS idx_queue_status ON analysis_processing_queue(queue_status)",
            "CREATE INDEX IF NOT EXISTS idx_queue_priority ON analysis_processing_queue(priority, queued_at)",
            "CREATE INDEX IF NOT EXISTS idx_errors_category ON llm_processing_errors(error_category)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_call_stage ON processing_metrics(call_id, stage)"
        ]
        
        # Execute table creation
        for sql in tables_sql:
            self.db.execute(sql)
        
        # Execute index creation
        for sql in indexes_sql:
            self.db.execute(sql)
        
        logger.info("Enhanced database tables and indexes created successfully")
    
    async def _insert_analysis_result(
        self, 
        tx, 
        call_id: int, 
        analysis_data: Dict[str, Any], 
        metadata
    ) -> int:
        """Insert analysis result with transaction"""
        query = """
        INSERT INTO llm_analysis_results 
        (call_id, analysis_version, analysis_data, confidence_score, 
         processing_time_seconds, token_usage)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        result = tx.execute(query, (
            call_id,
            metadata.analysis_version,
            json.dumps(analysis_data),
            metadata.analysis_confidence,
            metadata.processing_time_seconds,
            json.dumps(metadata.token_usage) if metadata.token_usage else None
        ))
        
        return result.lastrowid
    
    async def _update_call_status(self, tx, call_id: int, status: str, analysis_id: int) -> None:
        """Update call processing status"""
        # This would update the main calls table
        # For now, just update the queue
        query = """
        INSERT OR REPLACE INTO analysis_processing_queue 
        (call_id, queue_status, completed_at)
        VALUES (?, ?, ?)
        """
        
        tx.execute(query, (call_id, status, datetime.now()))
    
    async def _record_processing_metrics(
        self, 
        tx, 
        call_id: int, 
        stage: str, 
        duration: float, 
        success: bool
    ) -> None:
        """Record processing metrics within transaction"""
        query = """
        INSERT INTO processing_metrics 
        (call_id, stage, start_time, end_time, duration_seconds, success)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=duration)
        
        tx.execute(query, (call_id, stage, start_time, end_time, duration, success))
    
    async def _log_validation_error(
        self, 
        call_id: int, 
        error_message: str, 
        raw_data: Optional[Dict[str, Any]]
    ) -> None:
        """Log validation error for debugging"""
        await self.log_processing_error(
            call_id, 
            "validation_error", 
            error_message,
            {"raw_analysis_data": raw_data} if raw_data else None
        )
    
    async def _log_processing_error(
        self, 
        call_id: int, 
        category: str, 
        message: str
    ) -> None:
        """Helper to log processing errors"""
        try:
            query = """
            INSERT INTO llm_processing_errors 
            (call_id, error_category, error_message, occurred_at)
            VALUES (?, ?, ?, ?)
            """
            
            self.db.execute(query, (call_id, category, message, datetime.now()))
        except Exception as e:
            logger.error(f"Failed to log processing error: {e}")

# Factory function for easy integration
def get_analysis_storage_service() -> AnalysisStorageService:
    """Get configured analysis storage service instance"""
    return AnalysisStorageService()