"""
Asynchronous processing pipeline for LLM analysis workloads
Implements 3-retry logic, SLA monitoring, and queue management for reliable processing
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import random

try:
    from ..config.settings import get_config
    from ..models.processing_queue import (
        AnalysisQueue, QueueItem, QueueStatus, Priority, RetryCategory,
        ProcessingContext, ProcessingMetrics, SLAMetrics
    )
    from ..services.claude_client import ClaudeClient, ClaudeAPIError
    from ..services.analysis_prompts import get_analysis_prompt_for_call, validate_tool_response
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import get_config
    from models.processing_queue import (
        AnalysisQueue, QueueItem, QueueStatus, Priority, RetryCategory,
        ProcessingContext, QueueMetrics
    )
    from services.claude_client import ClaudeClient, ClaudeAPIError
    from services.analysis_prompts import get_analysis_prompt_for_call, validate_tool_response

logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    backoff_multiplier: float = 2.0

@dataclass
class ProcessingResult:
    """Result of processing operation"""
    success: bool
    call_id: str
    analysis_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    retries_used: int = 0
    final_retry: bool = False

class RetryManager:
    """Manages retry logic with exponential backoff"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        
    async def execute_with_retry(
        self, 
        func: Callable, 
        context: ProcessingContext,
        **kwargs
    ) -> ProcessingResult:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                result = await func(**kwargs)
                processing_time = time.time() - start_time
                
                return ProcessingResult(
                    success=True,
                    call_id=context.call_id,
                    analysis_data=result,
                    processing_time=processing_time,
                    retries_used=attempt
                )
                
            except Exception as e:
                last_exception = e
                processing_time = time.time() - start_time
                
                # Determine if error is retriable
                retry_category = self._categorize_error(e)
                
                if attempt < self.config.max_retries and retry_category == RetryCategory.RETRIABLE:
                    # Calculate backoff delay
                    delay = self._calculate_backoff(attempt)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for call {context.call_id}: {str(e)}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-retriable error or max retries reached
                    logger.error(
                        f"Processing failed for call {context.call_id} after {attempt + 1} attempts: {str(e)}"
                    )
                    
                    return ProcessingResult(
                        success=False,
                        call_id=context.call_id,
                        error_message=str(e),
                        processing_time=processing_time,
                        retries_used=attempt,
                        final_retry=attempt >= self.config.max_retries
                    )
        
        # Should not reach here, but handle gracefully
        return ProcessingResult(
            success=False,
            call_id=context.call_id,
            error_message=str(last_exception) if last_exception else "Unknown error",
            processing_time=0.0,
            retries_used=self.config.max_retries,
            final_retry=True
        )
    
    def _categorize_error(self, error: Exception) -> RetryCategory:
        """Categorize error to determine if retry is appropriate"""
        error_str = str(error).lower()
        
        # Claude API specific errors
        if isinstance(error, ClaudeAPIError):
            if 'rate limit' in error_str or 'too many requests' in error_str:
                return RetryCategory.RETRIABLE
            elif 'timeout' in error_str or 'connection' in error_str:
                return RetryCategory.RETRIABLE
            elif 'authentication' in error_str or 'api key' in error_str:
                return RetryCategory.NON_RETRIABLE
            elif 'content filter' in error_str or 'policy' in error_str:
                return RetryCategory.CONTENT_ISSUES
            else:
                return RetryCategory.RETRIABLE  # Default to retriable for unknown Claude errors
        
        # Network and connection errors (typically retriable)
        if any(keyword in error_str for keyword in [
            'connection', 'network', 'timeout', 'dns', 'socket'
        ]):
            return RetryCategory.RETRIABLE
        
        # Database errors (sometimes retriable)
        if any(keyword in error_str for keyword in [
            'database', 'deadlock', 'lock timeout'
        ]):
            return RetryCategory.RETRIABLE
        
        # Content and validation errors (usually not retriable)
        if any(keyword in error_str for keyword in [
            'validation', 'schema', 'malformed', 'invalid json'
        ]):
            return RetryCategory.NON_RETRIABLE
        
        # Default to retriable for unknown errors
        return RetryCategory.RETRIABLE
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = min(
            self.config.base_delay * (self.config.backoff_multiplier ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add ±25% jitter to prevent thundering herd
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 100ms delay

class SLAMonitor:
    """Monitors processing performance against SLA requirements"""
    
    def __init__(self, target_sla_minutes: int = 30):
        self.target_sla = timedelta(minutes=target_sla_minutes)
        self.processing_times: List[float] = []
        self.violations: List[Dict[str, Any]] = []
        self.start_times: Dict[str, datetime] = {}
    
    def start_tracking(self, call_id: str) -> None:
        """Start tracking processing time for a call"""
        self.start_times[call_id] = datetime.now()
        logger.debug(f"Started SLA tracking for call {call_id}")
    
    def complete_tracking(self, call_id: str, success: bool = True) -> Dict[str, Any]:
        """Complete tracking and check SLA compliance"""
        end_time = datetime.now()
        start_time = self.start_times.pop(call_id, end_time)
        processing_time = end_time - start_time
        
        # Record processing time
        self.processing_times.append(processing_time.total_seconds())
        
        # Check SLA compliance
        sla_compliant = processing_time <= self.target_sla
        
        if not sla_compliant:
            violation = {
                'call_id': call_id,
                'processing_time': processing_time.total_seconds(),
                'target_seconds': self.target_sla.total_seconds(),
                'violation_amount': (processing_time - self.target_sla).total_seconds(),
                'timestamp': end_time.isoformat(),
                'success': success
            }
            self.violations.append(violation)
            logger.warning(
                f"SLA violation for call {call_id}: "
                f"{processing_time.total_seconds():.1f}s > {self.target_sla.total_seconds()}s"
            )
        
        return {
            'call_id': call_id,
            'processing_time_seconds': processing_time.total_seconds(),
            'sla_compliant': sla_compliant,
            'success': success
        }
    
    def get_sla_metrics(self) -> QueueMetrics:
        """Get current SLA performance metrics"""
        if not self.processing_times:
            return QueueMetrics(
                queue_depth=0,
                processing_count=0,
                completed_count=0,
                failed_count=0,
                average_processing_time=0.0,
                average_queue_wait_time=0.0,
                sla_compliance_rate=100.0,
                throughput_per_hour=0.0,
                error_rate=0.0
            )
        
        # Calculate percentiles
        sorted_times = sorted(self.processing_times)
        n = len(sorted_times)
        
        p50 = sorted_times[int(n * 0.5)] if n > 0 else 0
        p90 = sorted_times[int(n * 0.9)] if n > 0 else 0
        p99 = sorted_times[int(n * 0.99)] if n > 0 else 0
        
        # Calculate compliance rate
        compliant_calls = sum(1 for t in self.processing_times if t <= self.target_sla.total_seconds())
        compliance_rate = (compliant_calls / len(self.processing_times)) * 100
        
        # Count recent violations
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_violations = len([
            v for v in self.violations 
            if datetime.fromisoformat(v['timestamp']) >= one_hour_ago
        ])
        
        return QueueMetrics(
            queue_depth=0,
            processing_count=0,
            completed_count=len(self.processing_times),
            failed_count=0,
            average_processing_time=sum(self.processing_times) / len(self.processing_times),
            average_queue_wait_time=0.0,
            sla_compliance_rate=compliance_rate,
            throughput_per_hour=len(self.processing_times),
            error_rate=0.0
        )

class BatchProcessor:
    """Handles batch processing for cost optimization"""
    
    def __init__(self, max_batch_size: int = 5, max_tokens_per_batch: int = 150000):
        self.max_batch_size = max_batch_size
        self.max_tokens_per_batch = max_tokens_per_batch
    
    def can_batch_calls(self, calls: List[Dict[str, Any]]) -> bool:
        """Determine if calls are suitable for batching"""
        if len(calls) < 2:
            return False
        
        # Check total token count estimate
        total_tokens = sum(len(call.get('transcript', '')) for call in calls)
        if total_tokens > self.max_tokens_per_batch:
            return False
        
        # Check if calls are from similar timeframe (within 4 hours)
        timestamps = [call.get('created_at') for call in calls if call.get('created_at')]
        if len(timestamps) > 1:
            time_span = max(timestamps) - min(timestamps)
            if time_span.total_seconds() > 4 * 3600:  # 4 hours
                return False
        
        return True
    
    async def process_batch(
        self, 
        calls: List[Dict[str, Any]], 
        claude_client: ClaudeClient
    ) -> List[ProcessingResult]:
        """Process multiple calls in a single batch request"""
        logger.info(f"Processing batch of {len(calls)} calls")
        
        # For now, process individually but with shared context
        # Future enhancement: true batch API calls
        results = []
        
        for call in calls:
            try:
                # Process each call individually
                transcript = call.get('transcript', '')
                title = call.get('title', 'Unknown Call')
                
                system_prompt, tool_definition, user_prompt = get_analysis_prompt_for_call(
                    transcript, {
                        'title': title,
                        'date': call.get('created_at', datetime.now()).isoformat(),
                        'batch_processing': True
                    }
                )
                
                start_time = time.time()
                claude_result = await claude_client.analyze_with_tools(
                    transcript=user_prompt,
                    tools=[tool_definition]
                )
                
                # Parse and validate result
                tool_results = json.loads(claude_result.content)
                if isinstance(tool_results, list) and len(tool_results) > 0:
                    for tool_result in tool_results:
                        if isinstance(tool_result, dict) and 'tool_input' in tool_result:
                            analysis_data = validate_tool_response(tool_result['tool_input'])
                            break
                    else:
                        raise ValueError("No valid tool call found in batch response")
                else:
                    raise ValueError("Invalid batch tool response format")
                
                processing_time = time.time() - start_time
                
                results.append(ProcessingResult(
                    success=True,
                    call_id=call.get('id', 'unknown'),
                    analysis_data=analysis_data,
                    processing_time=processing_time
                ))
                
            except Exception as e:
                logger.error(f"Batch processing failed for call {call.get('id', 'unknown')}: {e}")
                results.append(ProcessingResult(
                    success=False,
                    call_id=call.get('id', 'unknown'),
                    error_message=str(e)
                ))
        
        logger.info(f"Batch processing completed: {sum(1 for r in results if r.success)}/{len(results)} successful")
        return results

class AsyncAnalysisProcessor:
    """Main asynchronous analysis processor with comprehensive error handling and SLA monitoring"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.claude_client = ClaudeClient(self.config.claude) if self.config.claude.api_key else None
        
        # Processing components
        self.queue = AnalysisQueue(max_size=100)
        self.retry_manager = RetryManager()
        self.sla_monitor = SLAMonitor(target_sla_minutes=30)
        self.batch_processor = BatchProcessor()
        
        # State management
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.processed_count = 0
        self.failed_count = 0
        
        logger.info(f"Initialized AsyncAnalysisProcessor with {self.config.processing.max_concurrent_operations} workers")
    
    async def start_processing(self, num_workers: int = None) -> None:
        """Start the async processing pipeline"""
        if self.is_running:
            logger.warning("Processing is already running")
            return
        
        num_workers = num_workers or self.config.processing.max_concurrent_operations
        self.is_running = True
        
        logger.info(f"Starting async processing with {num_workers} workers")
        
        # Start worker tasks
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        logger.info("Async processing started successfully")
    
    async def stop_processing(self) -> None:
        """Stop the async processing pipeline gracefully"""
        if not self.is_running:
            return
        
        logger.info("Stopping async processing...")
        self.is_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        logger.info("Async processing stopped")
    
    async def queue_for_analysis(self, call_data: Dict[str, Any], priority: Priority = Priority.STANDARD) -> str:
        """Queue a call for analysis"""
        context = ProcessingContext(
            call_id=call_data.get('id', 'unknown'),
            fellow_id=call_data.get('fellow_id', ''),
            priority=priority,
            metadata=call_data
        )
        
        queue_id = await self.queue.enqueue_call(call_data, priority)
        self.sla_monitor.start_tracking(context.call_id)
        
        logger.info(f"Queued call {context.call_id} for analysis with priority {priority.name}")
        return queue_id
    
    async def analyze_call_immediately(self, call_data: Dict[str, Any]) -> ProcessingResult:
        """Analyze a call immediately without queuing"""
        context = ProcessingContext(
            call_id=call_data.get('id', 'unknown'),
            fellow_id=call_data.get('fellow_id', ''),
            metadata=call_data
        )
        
        self.sla_monitor.start_tracking(context.call_id)
        
        try:
            result = await self.retry_manager.execute_with_retry(
                self._analyze_single_call,
                context,
                call_data=call_data
            )
            
            # Update SLA tracking
            sla_result = self.sla_monitor.complete_tracking(context.call_id, result.success)
            
            if result.success:
                self.processed_count += 1
                logger.info(f"✅ Immediate analysis completed for call {context.call_id}")
            else:
                self.failed_count += 1
                logger.error(f"❌ Immediate analysis failed for call {context.call_id}: {result.error_message}")
            
            return result
            
        except Exception as e:
            self.failed_count += 1
            self.sla_monitor.complete_tracking(context.call_id, False)
            logger.error(f"❌ Immediate analysis exception for call {context.call_id}: {e}")
            
            return ProcessingResult(
                success=False,
                call_id=context.call_id,
                error_message=str(e)
            )
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Worker loop for processing queued items"""
        logger.info(f"Worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get next item from queue
                queue_item = await self.queue.dequeue_for_processing()
                
                if not queue_item:
                    # No items available, wait briefly
                    await asyncio.sleep(1.0)
                    continue
                
                # Process the call
                context = ProcessingContext(
                    call_id=queue_item.call_data.get('id', 'unknown'),
                    fellow_id=queue_item.call_data.get('fellow_id', ''),
                    metadata=queue_item.call_data
                )
                
                logger.debug(f"Worker {worker_name} processing call {context.call_id}")
                
                result = await self.retry_manager.execute_with_retry(
                    self._analyze_single_call,
                    context,
                    call_data=queue_item.call_data
                )
                
                # Update queue status and SLA tracking
                if result.success:
                    await self.queue.mark_completed(queue_item.queue_id, result.analysis_data)
                    self.processed_count += 1
                    logger.debug(f"✅ Worker {worker_name} completed call {context.call_id}")
                else:
                    await self.queue.mark_failed(queue_item.queue_id, Exception(result.error_message))
                    self.failed_count += 1
                    logger.error(f"❌ Worker {worker_name} failed call {context.call_id}: {result.error_message}")
                
                sla_result = self.sla_monitor.complete_tracking(context.call_id, result.success)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} encountered unexpected error: {e}")
                # Continue processing other items
                await asyncio.sleep(1.0)
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _analyze_single_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single call (used by retry manager)"""
        if not self.claude_client:
            raise Exception("Claude client not available")
        
        transcript = call_data.get('transcript', '')
        if not transcript.strip():
            raise ValueError("Empty transcript")
        
        title = call_data.get('title', 'Unknown Call')
        
        # Get structured analysis prompts
        system_prompt, tool_definition, user_prompt = get_analysis_prompt_for_call(
            transcript, {
                'title': title,
                'date': call_data.get('created_at', datetime.now()).isoformat(),
                'call_id': call_data.get('id'),
                'fellow_id': call_data.get('fellow_id')
            }
        )
        
        # Execute Claude analysis with tools
        claude_result = await self.claude_client.analyze_with_tools(
            transcript=user_prompt,
            tools=[tool_definition]
        )
        
        # Parse and validate tool response
        try:
            tool_results = json.loads(claude_result.content)
            if isinstance(tool_results, list) and len(tool_results) > 0:
                for tool_result in tool_results:
                    if isinstance(tool_result, dict) and 'tool_input' in tool_result:
                        analysis_data = validate_tool_response(tool_result['tool_input'])
                        break
                else:
                    raise ValueError("No valid tool call found in Claude response")
            else:
                raise ValueError("Invalid Claude tool response format")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Tool response parsing failed: {e}, falling back to content parsing")
            # Fallback: try to extract JSON from raw content
            analysis_data = self._parse_fallback_response(claude_result.content, transcript, title)
        
        # Enhance metadata
        if 'analysis_metadata' not in analysis_data:
            analysis_data['analysis_metadata'] = {}
        
        analysis_data['analysis_metadata'].update({
            'analysis_version': '2.0-async-structured',
            'llm_model_used': claude_result.model,
            'processing_time_seconds': claude_result.processing_time,
            'token_usage': claude_result.usage,
            'claude_finish_reason': claude_result.finish_reason,
            'async_processed': True
        })
        
        return analysis_data
    
    def _parse_fallback_response(self, claude_content: str, transcript: str, title: str) -> Dict[str, Any]:
        """Parse fallback response when tool calling fails"""
        from models.analysis_schema import create_fallback_analysis
        
        logger.warning("Using fallback analysis due to Claude tool parsing failure")
        fallback_result = create_fallback_analysis(transcript, title)
        
        # Try to enhance with any insights from Claude's raw content
        content_lower = claude_content.lower()
        
        # Basic sentiment enhancement
        if 'very interested' in content_lower or 'excited' in content_lower:
            fallback_result.prospect_sentiment.excitement_level = min(8, fallback_result.prospect_sentiment.excitement_level + 2)
        elif 'interested' in content_lower:
            fallback_result.prospect_sentiment.excitement_level = min(7, fallback_result.prospect_sentiment.excitement_level + 1)
        
        # Mark as fallback in metadata
        fallback_result.analysis_metadata.used_fallback_analysis = True
        fallback_result.analysis_metadata.required_manual_review = True
        fallback_result.analysis_metadata.analysis_confidence = 4  # Lower confidence for fallback
        
        return fallback_result.dict()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status and metrics"""
        queue_status = self.queue.get_queue_status()
        sla_metrics = self.sla_monitor.get_sla_metrics()
        
        return {
            'is_running': self.is_running,
            'active_workers': len(self.worker_tasks),
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'success_rate': (self.processed_count / (self.processed_count + self.failed_count) * 100) if (self.processed_count + self.failed_count) > 0 else 100.0,
            'queue_status': queue_status,
            'sla_metrics': sla_metrics,
            'claude_client_available': self.claude_client is not None
        }

# Utility functions for external use
async def process_call_async(call_data: Dict[str, Any], priority: Priority = Priority.STANDARD) -> ProcessingResult:
    """Utility function to process a single call asynchronously"""
    processor = AsyncAnalysisProcessor()
    
    try:
        await processor.start_processing(num_workers=1)
        result = await processor.analyze_call_immediately(call_data)
        return result
    finally:
        await processor.stop_processing()

async def batch_process_calls(calls: List[Dict[str, Any]]) -> List[ProcessingResult]:
    """Utility function to batch process multiple calls"""
    processor = AsyncAnalysisProcessor()
    batch_processor = BatchProcessor()
    
    if not processor.claude_client:
        raise Exception("Claude client not available for batch processing")
    
    try:
        # Check if calls are suitable for batching
        if batch_processor.can_batch_calls(calls):
            logger.info(f"Processing {len(calls)} calls as batch")
            return await batch_processor.process_batch(calls, processor.claude_client)
        else:
            # Process individually
            logger.info(f"Processing {len(calls)} calls individually (not suitable for batching)")
            await processor.start_processing(num_workers=min(3, len(calls)))
            
            results = []
            for call in calls:
                result = await processor.analyze_call_immediately(call)
                results.append(result)
            
            return results
    finally:
        await processor.stop_processing()