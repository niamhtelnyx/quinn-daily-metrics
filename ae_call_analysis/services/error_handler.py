"""
Comprehensive error handling and recovery system for LLM analysis pipeline
Provides categorization, escalation, and automated recovery for production reliability
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    from ..config.settings import get_config
    from ..services.claude_client import ClaudeAPIError
    from ..models.processing_queue import RetryCategory, ProcessingContext
    from ..models.error_tracking import ErrorEvent, EscalationLevel, RecoveryAction
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import get_config
    from services.claude_client import ClaudeAPIError
    from models.processing_queue import RetryCategory, ProcessingContext
    from models.error_tracking import ErrorEvent, EscalationLevel, RecoveryAction

# Import OpenAI errors for context overflow handling
try:
    from ..services.openai_client import OpenAIAPIError, ContextOverflowError
except ImportError:
    try:
        from services.openai_client import OpenAIAPIError, ContextOverflowError
    except ImportError:
        OpenAIAPIError = Exception
        ContextOverflowError = Exception

logger = logging.getLogger(__name__)

class ErrorCategory(str, Enum):
    """Comprehensive error categorization for handling and reporting"""
    
    # Claude API errors
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    API_TIMEOUT = "api_timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    CONTENT_FILTERED = "content_filtered"
    TOKEN_LIMIT_EXCEEDED = "token_limit_exceeded"
    QUOTA_EXCEEDED = "quota_exceeded"
    
    # Context overflow specific (OpenAI)
    CONTEXT_OVERFLOW = "context_overflow"
    TRANSCRIPT_TOO_LARGE = "transcript_too_large"
    TRUNCATION_FAILED = "truncation_failed"
    
    # Data processing errors
    TRANSCRIPT_INVALID = "transcript_invalid"
    TRANSCRIPT_EMPTY = "transcript_empty"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    JSON_PARSE_ERROR = "json_parse_error"
    TOOL_RESPONSE_INVALID = "tool_response_invalid"
    
    # Database errors
    DATABASE_CONNECTION_FAILED = "database_connection_failed"
    DATABASE_TIMEOUT = "database_timeout"
    TRANSACTION_FAILED = "transaction_failed"
    CONSTRAINT_VIOLATION = "constraint_violation"
    
    # System errors
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    SERVICE_UNAVAILABLE = "service_unavailable"
    
    # Business logic errors
    MISSING_REQUIRED_DATA = "missing_required_data"
    INVALID_CALL_STATE = "invalid_call_state"
    PROCESSING_TIMEOUT = "processing_timeout"
    
    # Unknown/unexpected errors
    UNKNOWN_ERROR = "unknown_error"

class EscalationLevel(str, Enum):
    """Error escalation levels for operational alerting"""
    LOW = "low"           # Log only, no immediate action needed
    MEDIUM = "medium"     # Monitor, may need attention
    HIGH = "high"         # Immediate attention required
    CRITICAL = "critical" # System-wide impact, urgent response needed

@dataclass
class RecoveryAction:
    """Defines recovery action for error scenarios"""
    should_retry: bool = False
    should_escalate: bool = False
    delay_seconds: float = 0.0
    max_retries: int = 3
    fallback_action: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.LOW
    custom_handler: Optional[Callable] = None

@dataclass
class ErrorHandlingResult:
    """Result of error handling operation"""
    handled: bool
    recovery_action: RecoveryAction
    error_logged: bool = True
    escalated: bool = False
    custom_recovery_applied: bool = False

@dataclass
class ErrorEvent:
    """Comprehensive error event for tracking and analysis"""
    error_id: str
    call_id: str
    error_category: ErrorCategory
    error_message: str
    exception_type: str
    context: Dict[str, Any]
    occurred_at: datetime
    processing_stage: str
    retry_attempt: int = 0
    escalation_level: EscalationLevel = EscalationLevel.LOW
    
    # Recovery tracking
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_details: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

class ErrorMetrics:
    """Track error metrics for monitoring and alerting"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.escalation_counts: Dict[str, int] = {}
        self.recovery_success_counts: Dict[str, int] = {}
        self.recent_errors: List[ErrorEvent] = []
        self.max_recent_errors = 1000
    
    def record_error(self, event: ErrorEvent) -> None:
        """Record error event for metrics tracking"""
        category = event.error_category.value
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
        
        escalation = event.escalation_level.value
        self.escalation_counts[escalation] = self.escalation_counts.get(escalation, 0) + 1
        
        # Track recent errors (with size limit)
        self.recent_errors.append(event)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
    
    def record_recovery(self, event: ErrorEvent, successful: bool) -> None:
        """Record recovery attempt result"""
        key = f"{event.error_category.value}_{'success' if successful else 'failure'}"
        self.recovery_success_counts[key] = self.recovery_success_counts.get(key, 0) + 1
    
    def get_error_rate(self, time_window_minutes: int = 60) -> float:
        """Calculate error rate for recent time window"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_count = len([e for e in self.recent_errors if e.occurred_at >= cutoff_time])
        
        # Estimate total processing attempts (this would be improved with actual metrics)
        estimated_total = max(recent_count * 10, 100)  # Conservative estimate
        
        return (recent_count / estimated_total) * 100
    
    def get_top_errors(self, limit: int = 10) -> List[tuple]:
        """Get most frequent error categories"""
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_errors[:limit]

class EscalationManager:
    """Manages error escalation and alerting"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.escalation_handlers: Dict[EscalationLevel, List[Callable]] = {
            EscalationLevel.LOW: [],
            EscalationLevel.MEDIUM: [],
            EscalationLevel.HIGH: [],
            EscalationLevel.CRITICAL: []
        }
        
        # Default escalation handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default escalation handlers"""
        # LOW: Just log
        self.escalation_handlers[EscalationLevel.LOW].append(self._log_escalation)
        
        # MEDIUM: Log + monitor
        self.escalation_handlers[EscalationLevel.MEDIUM].extend([
            self._log_escalation,
            self._update_monitoring_metrics
        ])
        
        # HIGH: Log + alert
        self.escalation_handlers[EscalationLevel.HIGH].extend([
            self._log_escalation,
            self._update_monitoring_metrics,
            self._send_alert
        ])
        
        # CRITICAL: All actions + immediate notification
        self.escalation_handlers[EscalationLevel.CRITICAL].extend([
            self._log_escalation,
            self._update_monitoring_metrics,
            self._send_alert,
            self._send_critical_notification
        ])
    
    async def escalate_error(self, event: ErrorEvent) -> bool:
        """Execute escalation procedures for error event"""
        try:
            handlers = self.escalation_handlers.get(event.escalation_level, [])
            
            for handler in handlers:
                await handler(event)
            
            logger.info(f"Escalated {event.escalation_level.value} error for call {event.call_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate error: {e}")
            return False
    
    async def _log_escalation(self, event: ErrorEvent) -> None:
        """Log escalation event"""
        logger.warning(
            f"ESCALATION [{event.escalation_level.value.upper()}]: "
            f"Call {event.call_id}, Category: {event.error_category.value}, "
            f"Message: {event.error_message}"
        )
    
    async def _update_monitoring_metrics(self, event: ErrorEvent) -> None:
        """Update monitoring metrics (placeholder for monitoring system integration)"""
        # In production, this would integrate with monitoring systems like Prometheus, DataDog, etc.
        pass
    
    async def _send_alert(self, event: ErrorEvent) -> None:
        """Send alert to operations team (placeholder)"""
        # In production, this would integrate with alerting systems like PagerDuty, Slack, etc.
        logger.info(f"ALERT: High priority error for call {event.call_id}: {event.error_message}")
    
    async def _send_critical_notification(self, event: ErrorEvent) -> None:
        """Send critical notification for immediate response"""
        # In production, this would trigger immediate notifications
        logger.critical(
            f"CRITICAL ERROR: Immediate attention required for call {event.call_id}: "
            f"{event.error_message}"
        )

class LLMErrorHandler:
    """
    Comprehensive error handler for LLM analysis pipeline
    Provides intelligent error categorization, recovery, and escalation
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.error_metrics = ErrorMetrics()
        self.escalation_manager = EscalationManager(config)
        
        # Recovery strategy mappings
        self.recovery_strategies = self._build_recovery_strategies()
        
        logger.info("Initialized LLMErrorHandler with comprehensive recovery strategies")
    
    def _build_recovery_strategies(self) -> Dict[ErrorCategory, RecoveryAction]:
        """Build mapping of error categories to recovery strategies"""
        return {
            # Claude API errors
            ErrorCategory.RATE_LIMIT_EXCEEDED: RecoveryAction(
                should_retry=True,
                delay_seconds=60.0,
                max_retries=5,
                escalation_level=EscalationLevel.MEDIUM
            ),
            
            ErrorCategory.API_TIMEOUT: RecoveryAction(
                should_retry=True,
                delay_seconds=10.0,
                max_retries=3,
                escalation_level=EscalationLevel.MEDIUM
            ),
            
            ErrorCategory.AUTHENTICATION_FAILED: RecoveryAction(
                should_retry=False,
                should_escalate=True,
                escalation_level=EscalationLevel.CRITICAL,
                fallback_action="use_mock_analysis"
            ),
            
            ErrorCategory.CONTENT_FILTERED: RecoveryAction(
                should_retry=True,
                max_retries=1,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="sanitize_transcript"
            ),
            
            ErrorCategory.TOKEN_LIMIT_EXCEEDED: RecoveryAction(
                should_retry=True,
                max_retries=2,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="truncate_transcript"
            ),
            
            # Context overflow specific recovery strategies
            ErrorCategory.CONTEXT_OVERFLOW: RecoveryAction(
                should_retry=True,
                max_retries=3,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="aggressive_truncation_then_claude_fallback"
            ),
            
            ErrorCategory.TRANSCRIPT_TOO_LARGE: RecoveryAction(
                should_retry=True,
                max_retries=2,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="use_claude_200k_context"
            ),
            
            ErrorCategory.TRUNCATION_FAILED: RecoveryAction(
                should_retry=False,
                should_escalate=True,
                escalation_level=EscalationLevel.HIGH,
                fallback_action="use_summary_analysis"
            ),
            
            # Data processing errors
            ErrorCategory.TRANSCRIPT_INVALID: RecoveryAction(
                should_retry=False,
                should_escalate=True,
                escalation_level=EscalationLevel.HIGH,
                fallback_action="use_mock_analysis"
            ),
            
            ErrorCategory.TRANSCRIPT_EMPTY: RecoveryAction(
                should_retry=False,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="use_empty_transcript_analysis"
            ),
            
            ErrorCategory.SCHEMA_VALIDATION_FAILED: RecoveryAction(
                should_retry=True,
                max_retries=1,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="use_fallback_schema"
            ),
            
            ErrorCategory.TOOL_RESPONSE_INVALID: RecoveryAction(
                should_retry=True,
                max_retries=2,
                escalation_level=EscalationLevel.MEDIUM,
                fallback_action="parse_unstructured_response"
            ),
            
            # Database errors
            ErrorCategory.DATABASE_CONNECTION_FAILED: RecoveryAction(
                should_retry=True,
                delay_seconds=5.0,
                max_retries=3,
                escalation_level=EscalationLevel.HIGH
            ),
            
            ErrorCategory.TRANSACTION_FAILED: RecoveryAction(
                should_retry=True,
                delay_seconds=2.0,
                max_retries=3,
                escalation_level=EscalationLevel.MEDIUM
            ),
            
            # System errors
            ErrorCategory.NETWORK_ERROR: RecoveryAction(
                should_retry=True,
                delay_seconds=5.0,
                max_retries=3,
                escalation_level=EscalationLevel.MEDIUM
            ),
            
            ErrorCategory.SERVICE_UNAVAILABLE: RecoveryAction(
                should_retry=True,
                delay_seconds=30.0,
                max_retries=5,
                escalation_level=EscalationLevel.HIGH
            ),
            
            # Default for unknown errors
            ErrorCategory.UNKNOWN_ERROR: RecoveryAction(
                should_retry=True,
                delay_seconds=5.0,
                max_retries=2,
                escalation_level=EscalationLevel.HIGH
            )
        }
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ProcessingContext
    ) -> ErrorHandlingResult:
        """
        Handle error with comprehensive categorization, recovery, and escalation
        
        Args:
            error: The exception that occurred
            context: Processing context for the error
            
        Returns:
            ErrorHandlingResult with handling details and recovery actions
        """
        # Create error event
        error_event = self._create_error_event(error, context)
        
        # Record error metrics
        self.error_metrics.record_error(error_event)
        
        # Log error with context
        await self._log_error_with_context(error_event)
        
        # Get recovery strategy
        recovery_action = self._get_recovery_strategy(error_event.error_category)
        
        # Execute custom recovery if available
        custom_recovery_applied = False
        if recovery_action.custom_handler:
            try:
                custom_result = await recovery_action.custom_handler(error_event, context)
                custom_recovery_applied = True
                logger.info(f"Applied custom recovery for {error_event.error_category.value}")
            except Exception as e:
                logger.error(f"Custom recovery failed: {e}")
        
        # Execute escalation if needed
        escalated = False
        if (recovery_action.should_escalate or 
            recovery_action.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]):
            escalated = await self.escalation_manager.escalate_error(error_event)
        
        return ErrorHandlingResult(
            handled=True,
            recovery_action=recovery_action,
            error_logged=True,
            escalated=escalated,
            custom_recovery_applied=custom_recovery_applied
        )
    
    def _create_error_event(self, error: Exception, context: ProcessingContext) -> ErrorEvent:
        """Create comprehensive error event from exception and context"""
        error_category = self._categorize_error(error)
        escalation_level = self._determine_escalation_level(error, error_category)
        
        return ErrorEvent(
            error_id=f"{context.call_id}_{datetime.now().isoformat()}",
            call_id=context.call_id,
            error_category=error_category,
            error_message=str(error),
            exception_type=type(error).__name__,
            context={
                'fellow_id': context.fellow_id,
                'priority': context.priority.value,
                'metadata': context.metadata
            },
            occurred_at=datetime.now(),
            processing_stage=context.metadata.get('processing_stage', 'unknown'),
            retry_attempt=context.metadata.get('retry_attempt', 0),
            escalation_level=escalation_level
        )
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error for appropriate handling"""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Context overflow specific errors (check first - highest priority)
        if isinstance(error, ContextOverflowError) or error_type == 'ContextOverflowError':
            return ErrorCategory.CONTEXT_OVERFLOW
        
        if 'context overflow' in error_str or 'prompt too large' in error_str:
            return ErrorCategory.CONTEXT_OVERFLOW
        
        if 'maximum context length' in error_str or 'context_length_exceeded' in error_str:
            return ErrorCategory.CONTEXT_OVERFLOW
        
        # OpenAI specific token errors
        if isinstance(error, OpenAIAPIError) or 'openai' in error_str:
            if any(kw in error_str for kw in ['token', 'context', 'length', 'maximum']):
                if 'truncat' in error_str:
                    return ErrorCategory.TRUNCATION_FAILED
                return ErrorCategory.CONTEXT_OVERFLOW
        
        # Claude API specific errors
        if isinstance(error, ClaudeAPIError) or 'claude' in error_str:
            if 'rate limit' in error_str or 'too many requests' in error_str:
                return ErrorCategory.RATE_LIMIT_EXCEEDED
            elif 'timeout' in error_str:
                return ErrorCategory.API_TIMEOUT
            elif 'authentication' in error_str or 'api key' in error_str:
                return ErrorCategory.AUTHENTICATION_FAILED
            elif 'content' in error_str and ('filter' in error_str or 'policy' in error_str):
                return ErrorCategory.CONTENT_FILTERED
            elif 'token' in error_str and 'limit' in error_str:
                return ErrorCategory.TOKEN_LIMIT_EXCEEDED
            elif 'quota' in error_str:
                return ErrorCategory.QUOTA_EXCEEDED
        
        # Data validation errors
        if 'validation' in error_str or error_type in ['ValidationError', 'ValueError']:
            if 'transcript' in error_str:
                if 'empty' in error_str:
                    return ErrorCategory.TRANSCRIPT_EMPTY
                else:
                    return ErrorCategory.TRANSCRIPT_INVALID
            elif 'schema' in error_str:
                return ErrorCategory.SCHEMA_VALIDATION_FAILED
            elif 'json' in error_str:
                return ErrorCategory.JSON_PARSE_ERROR
            elif 'tool' in error_str:
                return ErrorCategory.TOOL_RESPONSE_INVALID
        
        # Database errors
        if any(keyword in error_str for keyword in ['database', 'sqlite', 'sql']):
            if 'connection' in error_str:
                return ErrorCategory.DATABASE_CONNECTION_FAILED
            elif 'timeout' in error_str:
                return ErrorCategory.DATABASE_TIMEOUT
            elif 'transaction' in error_str:
                return ErrorCategory.TRANSACTION_FAILED
            elif 'constraint' in error_str or 'unique' in error_str:
                return ErrorCategory.CONSTRAINT_VIOLATION
        
        # Network and connection errors
        if any(keyword in error_str for keyword in [
            'network', 'connection', 'dns', 'socket', 'refused'
        ]):
            return ErrorCategory.NETWORK_ERROR
        
        # Timeout errors
        if 'timeout' in error_str:
            return ErrorCategory.PROCESSING_TIMEOUT
        
        # Configuration errors
        if any(keyword in error_str for keyword in ['config', 'setting', 'environment']):
            return ErrorCategory.CONFIGURATION_ERROR
        
        # Resource errors
        if any(keyword in error_str for keyword in ['memory', 'resource', 'limit']):
            return ErrorCategory.RESOURCE_EXHAUSTED
        
        # Service availability
        if any(keyword in error_str for keyword in ['unavailable', '503', '502']):
            return ErrorCategory.SERVICE_UNAVAILABLE
        
        # Missing data
        if any(keyword in error_str for keyword in ['missing', 'not found', 'required']):
            return ErrorCategory.MISSING_REQUIRED_DATA
        
        # Default to unknown
        return ErrorCategory.UNKNOWN_ERROR
    
    def _determine_escalation_level(self, error: Exception, category: ErrorCategory) -> EscalationLevel:
        """Determine appropriate escalation level based on error characteristics"""
        
        # Critical errors that affect system availability
        if category in [
            ErrorCategory.AUTHENTICATION_FAILED,
            ErrorCategory.QUOTA_EXCEEDED,
            ErrorCategory.SERVICE_UNAVAILABLE
        ]:
            return EscalationLevel.CRITICAL
        
        # High priority errors that affect processing capability
        if category in [
            ErrorCategory.DATABASE_CONNECTION_FAILED,
            ErrorCategory.CONFIGURATION_ERROR,
            ErrorCategory.RESOURCE_EXHAUSTED
        ]:
            return EscalationLevel.HIGH
        
        # Medium priority errors that may indicate issues but have recovery options
        if category in [
            ErrorCategory.RATE_LIMIT_EXCEEDED,
            ErrorCategory.API_TIMEOUT,
            ErrorCategory.CONTENT_FILTERED,
            ErrorCategory.SCHEMA_VALIDATION_FAILED
        ]:
            return EscalationLevel.MEDIUM
        
        # Check error frequency for escalation
        recent_error_count = len([
            e for e in self.error_metrics.recent_errors 
            if e.error_category == category and 
               e.occurred_at >= datetime.now() - timedelta(minutes=15)
        ])
        
        if recent_error_count > 10:
            return EscalationLevel.HIGH
        elif recent_error_count > 5:
            return EscalationLevel.MEDIUM
        
        # Default to low for most errors
        return EscalationLevel.LOW
    
    def _get_recovery_strategy(self, category: ErrorCategory) -> RecoveryAction:
        """Get recovery strategy for error category"""
        return self.recovery_strategies.get(category, self.recovery_strategies[ErrorCategory.UNKNOWN_ERROR])
    
    async def _log_error_with_context(self, event: ErrorEvent) -> None:
        """Log error with comprehensive context information"""
        log_level = {
            EscalationLevel.LOW: logging.INFO,
            EscalationLevel.MEDIUM: logging.WARNING,
            EscalationLevel.HIGH: logging.ERROR,
            EscalationLevel.CRITICAL: logging.CRITICAL
        }.get(event.escalation_level, logging.ERROR)
        
        logger.log(
            log_level,
            f"LLM Processing Error - Call: {event.call_id}, "
            f"Category: {event.error_category.value}, "
            f"Stage: {event.processing_stage}, "
            f"Attempt: {event.retry_attempt}, "
            f"Message: {event.error_message}"
        )
        
        # Detailed debug logging
        logger.debug(f"Error context for {event.call_id}: {json.dumps(event.context, indent=2)}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary for monitoring"""
        return {
            'error_metrics': {
                'total_errors_by_category': self.error_metrics.error_counts,
                'escalations_by_level': self.error_metrics.escalation_counts,
                'recovery_success_rates': self.error_metrics.recovery_success_counts,
                'recent_error_rate': self.error_metrics.get_error_rate(),
                'top_errors': self.error_metrics.get_top_errors()
            },
            'recent_errors': [
                {
                    'call_id': e.call_id,
                    'category': e.error_category.value,
                    'message': e.error_message,
                    'escalation_level': e.escalation_level.value,
                    'occurred_at': e.occurred_at.isoformat()
                }
                for e in self.error_metrics.recent_errors[-10:]  # Last 10 errors
            ],
            'recovery_strategies_count': len(self.recovery_strategies)
        }

# Utility functions for external use
async def handle_processing_error(
    error: Exception, 
    call_id: str, 
    context_metadata: Dict[str, Any] = None
) -> ErrorHandlingResult:
    """Utility function to handle processing errors"""
    handler = LLMErrorHandler()
    context = ProcessingContext(
        call_id=call_id,
        fellow_id=context_metadata.get('fellow_id', '') if context_metadata else '',
        metadata=context_metadata or {}
    )
    
    return await handler.handle_error(error, context)

def get_error_handler() -> LLMErrorHandler:
    """Get configured error handler instance"""
    return LLMErrorHandler()