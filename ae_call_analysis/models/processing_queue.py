"""
Asynchronous processing queue models and management
Handles coordination of call analysis processing with SLA compliance
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Priority(int, Enum):
    """Processing priority levels"""
    HIGH = 1      # Recent calls (< 1 hour old) for near real-time
    STANDARD = 5  # Regular processing with 30-minute SLA  
    LOW = 9       # Batch reprocessing and historical analysis

class QueueStatus(str, Enum):
    """Queue item processing states"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class RetryCategory(str, Enum):
    """Categories of errors for retry logic"""
    RETRIABLE = "retriable"          # Rate limits, timeouts, temporary API errors
    NON_RETRIABLE = "non_retriable"  # Auth failures, malformed requests
    CONTENT_ISSUES = "content_issues" # Transcript filtering, content policy violations

@dataclass
class ProcessingContext:
    """Context information for processing operations"""
    call_id: str
    fellow_id: str
    priority: Priority = Priority.STANDARD
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class QueueItem:
    """Individual item in the processing queue"""
    queue_id: str
    call_data: Dict[str, Any]
    priority: Priority
    context: ProcessingContext
    status: QueueStatus = QueueStatus.PENDING
    retry_count: int = 0
    last_error: Optional[str] = None
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def processing_time(self) -> Optional[timedelta]:
        """Calculate processing time if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def queue_wait_time(self) -> timedelta:
        """Calculate time spent waiting in queue"""
        start_time = self.started_at or datetime.now()
        return start_time - self.queued_at
    
    @property
    def total_time(self) -> timedelta:
        """Calculate total time from queue to completion"""
        end_time = self.completed_at or datetime.now()
        return end_time - self.queued_at

class QueueMetrics(BaseModel):
    """Queue performance and health metrics"""
    queue_depth: int = Field(description="Current number of items in queue")
    processing_count: int = Field(description="Items currently being processed")
    completed_count: int = Field(description="Items completed successfully")
    failed_count: int = Field(description="Items that failed processing")
    
    average_processing_time: float = Field(description="Average processing time in seconds")
    average_queue_wait_time: float = Field(description="Average time waiting in queue")
    sla_compliance_rate: float = Field(description="Percentage meeting SLA", ge=0, le=100)
    
    throughput_per_hour: float = Field(description="Items processed per hour")
    error_rate: float = Field(description="Percentage of failed items", ge=0, le=100)
    
    last_updated: datetime = Field(default_factory=datetime.now)

class ProcessingTracker:
    """Tracks individual call processing for SLA monitoring"""
    
    def __init__(self, call_id: str, sla_target_minutes: int = 30):
        self.call_id = call_id
        self.sla_target = timedelta(minutes=sla_target_minutes)
        self.start_time = datetime.now()
        self.stages: Dict[str, datetime] = {}
        self.completed_at: Optional[datetime] = None
    
    def mark_stage(self, stage_name: str) -> None:
        """Mark completion of a processing stage"""
        self.stages[stage_name] = datetime.now()
        logger.debug(f"Call {self.call_id} completed stage: {stage_name}")
    
    def complete(self) -> None:
        """Mark processing as complete"""
        self.completed_at = datetime.now()
        processing_time = self.completed_at - self.start_time
        
        if processing_time > self.sla_target:
            logger.warning(
                f"SLA violation: Call {self.call_id} took {processing_time.total_seconds():.1f}s "
                f"(target: {self.sla_target.total_seconds():.1f}s)"
            )
        else:
            logger.info(f"Call {self.call_id} processed in {processing_time.total_seconds():.1f}s")
    
    @property
    def total_processing_time(self) -> timedelta:
        """Get total processing time"""
        end_time = self.completed_at or datetime.now()
        return end_time - self.start_time
    
    @property
    def is_sla_violation(self) -> bool:
        """Check if processing violates SLA"""
        return self.total_processing_time > self.sla_target
    
    def get_stage_times(self) -> Dict[str, float]:
        """Get timing for each stage in seconds"""
        times = {}
        prev_time = self.start_time
        
        for stage, stage_time in sorted(self.stages.items(), key=lambda x: x[1]):
            times[stage] = (stage_time - prev_time).total_seconds()
            prev_time = stage_time
        
        return times

class AnalysisQueue:
    """Async queue manager for call analysis processing"""
    
    def __init__(self, max_size: int = 100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._processing: Dict[str, QueueItem] = {}
        self._completed: Dict[str, QueueItem] = {}
        self._failed: Dict[str, QueueItem] = {}
        self._metrics_history: List[QueueMetrics] = []
        self._lock = asyncio.Lock()
        
        # Configuration
        self.max_size = max_size
        self.sla_target_minutes = 30
        
        logger.info(f"Initialized AnalysisQueue with max_size={max_size}")
    
    async def enqueue_call(
        self, 
        call_data: Dict[str, Any], 
        priority: Priority = Priority.STANDARD
    ) -> str:
        """
        Add call to processing queue
        
        Args:
            call_data: Complete call data including transcript
            priority: Processing priority level
            
        Returns:
            queue_id: Unique identifier for tracking
        """
        # Generate unique queue ID
        import uuid
        queue_id = str(uuid.uuid4())
        
        # Create processing context
        context = ProcessingContext(
            call_id=call_data.get('id', ''),
            fellow_id=call_data.get('fellow_id', ''),
            priority=priority
        )
        
        # Create queue item
        queue_item = QueueItem(
            queue_id=queue_id,
            call_data=call_data,
            priority=priority,
            context=context
        )
        
        # Add to queue (priority queue simulation with asyncio.Queue)
        await self._queue.put(queue_item)
        
        logger.info(f"Enqueued call {context.call_id} with priority {priority.name} (queue_id: {queue_id})")
        return queue_id
    
    async def dequeue_for_processing(self) -> Optional[QueueItem]:
        """
        Get next item from queue for processing
        
        Returns:
            QueueItem or None if queue is empty
        """
        try:
            # Wait for item with short timeout
            queue_item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            
            # Move to processing
            async with self._lock:
                queue_item.status = QueueStatus.PROCESSING
                queue_item.started_at = datetime.now()
                self._processing[queue_item.queue_id] = queue_item
            
            logger.info(f"Dequeued item {queue_item.queue_id} for processing")
            return queue_item
            
        except asyncio.TimeoutError:
            # No items available
            return None
    
    async def mark_completed(self, queue_id: str, result: Dict[str, Any]) -> None:
        """Mark item as successfully completed"""
        async with self._lock:
            if queue_id in self._processing:
                item = self._processing.pop(queue_id)
                item.status = QueueStatus.COMPLETED
                item.completed_at = datetime.now()
                self._completed[queue_id] = item
                
                processing_time = item.processing_time
                if processing_time:
                    logger.info(
                        f"Completed processing {queue_id} in {processing_time.total_seconds():.1f}s"
                    )
    
    async def mark_failed(self, queue_id: str, error: Exception) -> None:
        """Mark item as failed"""
        async with self._lock:
            if queue_id in self._processing:
                item = self._processing.pop(queue_id)
                item.status = QueueStatus.FAILED
                item.completed_at = datetime.now()
                item.last_error = str(error)
                self._failed[queue_id] = item
                
                logger.error(f"Failed processing {queue_id}: {error}")
    
    async def retry_item(self, queue_id: str) -> bool:
        """
        Retry a failed item
        
        Returns:
            True if item was re-queued, False if not eligible for retry
        """
        async with self._lock:
            if queue_id in self._failed:
                item = self._failed.pop(queue_id)
                
                # Check retry eligibility
                if item.retry_count >= 3:  # Max retries
                    logger.warning(f"Item {queue_id} exceeded max retries")
                    return False
                
                # Reset for retry
                item.status = QueueStatus.RETRYING
                item.retry_count += 1
                item.started_at = None
                item.completed_at = None
                
                # Re-queue
                await self._queue.put(item)
                logger.info(f"Re-queued item {queue_id} for retry (attempt {item.retry_count})")
                return True
        
        return False
    
    def get_queue_status(self) -> QueueMetrics:
        """Get current queue status and metrics"""
        # Calculate metrics
        total_processing = len(self._processing)
        total_completed = len(self._completed)
        total_failed = len(self._failed)
        queue_size = self._queue.qsize()
        
        # Calculate processing times
        processing_times = []
        for item in self._completed.values():
            if item.processing_time:
                processing_times.append(item.processing_time.total_seconds())
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Calculate queue wait times
        wait_times = []
        for item in list(self._completed.values()) + list(self._failed.values()):
            wait_times.append(item.queue_wait_time.total_seconds())
        
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        # SLA compliance
        sla_violations = sum(1 for item in self._completed.values() 
                           if item.total_time > timedelta(minutes=self.sla_target_minutes))
        sla_compliance_rate = ((total_completed - sla_violations) / total_completed * 100) if total_completed > 0 else 100
        
        # Error rate
        total_processed = total_completed + total_failed
        error_rate = (total_failed / total_processed * 100) if total_processed > 0 else 0
        
        # Throughput (items per hour)
        # Calculate based on last hour of completed items
        now = datetime.now()
        recent_completions = sum(1 for item in self._completed.values()
                               if item.completed_at and (now - item.completed_at) <= timedelta(hours=1))
        throughput_per_hour = recent_completions  # Approximate
        
        return QueueMetrics(
            queue_depth=queue_size,
            processing_count=total_processing,
            completed_count=total_completed,
            failed_count=total_failed,
            average_processing_time=avg_processing_time,
            average_queue_wait_time=avg_wait_time,
            sla_compliance_rate=sla_compliance_rate,
            throughput_per_hour=throughput_per_hour,
            error_rate=error_rate
        )
    
    async def cleanup_old_items(self, max_age_hours: int = 24) -> int:
        """Clean up old completed and failed items"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        async with self._lock:
            # Clean completed items
            to_remove = [queue_id for queue_id, item in self._completed.items()
                        if item.completed_at and item.completed_at < cutoff_time]
            for queue_id in to_remove:
                del self._completed[queue_id]
                cleaned_count += 1
            
            # Clean failed items
            to_remove = [queue_id for queue_id, item in self._failed.items()
                        if item.completed_at and item.completed_at < cutoff_time]
            for queue_id in to_remove:
                del self._failed[queue_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old queue items")
        
        return cleaned_count
    
    async def get_retry_candidates(self) -> List[str]:
        """Get list of failed items eligible for retry"""
        candidates = []
        for queue_id, item in self._failed.items():
            if item.retry_count < 3:  # Max retries
                candidates.append(queue_id)
        return candidates
    
    def export_metrics_history(self) -> List[Dict[str, Any]]:
        """Export metrics history for monitoring dashboards"""
        return [metrics.dict() for metrics in self._metrics_history]

# Global queue instance
_global_queue: Optional[AnalysisQueue] = None

def get_analysis_queue() -> AnalysisQueue:
    """Get or create global analysis queue instance"""
    global _global_queue
    if _global_queue is None:
        _global_queue = AnalysisQueue()
    return _global_queue