"""
Error tracking and monitoring models for comprehensive system observability
Provides data structures for error events, metrics, and recovery tracking
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

class ErrorSeverity(str, Enum):
    """Error severity levels for classification and response"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EscalationLevel(str, Enum):
    """Error escalation levels for operational alerting"""
    LOW = "low"           # Log only, no immediate action needed
    MEDIUM = "medium"     # Monitor, may need attention
    HIGH = "high"         # Immediate attention required
    CRITICAL = "critical" # System-wide impact, urgent response needed

class RecoveryStatus(str, Enum):
    """Status of recovery attempts"""
    NOT_ATTEMPTED = "not_attempted"
    IN_PROGRESS = "in_progress"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class RecoveryAction:
    """Defines recovery action for error scenarios"""
    should_retry: bool = False
    should_escalate: bool = False
    delay_seconds: float = 0.0
    max_retries: int = 3
    fallback_action: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.LOW
    custom_handler: Optional[str] = None  # Name of custom handler function
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'should_retry': self.should_retry,
            'should_escalate': self.should_escalate,
            'delay_seconds': self.delay_seconds,
            'max_retries': self.max_retries,
            'fallback_action': self.fallback_action,
            'escalation_level': self.escalation_level.value,
            'custom_handler': self.custom_handler
        }

@dataclass
class ErrorEvent:
    """Comprehensive error event for tracking and analysis"""
    error_id: str
    call_id: str
    error_category: str
    error_message: str
    exception_type: str
    context: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.now)
    processing_stage: str = "unknown"
    retry_attempt: int = 0
    escalation_level: EscalationLevel = EscalationLevel.LOW
    
    # Recovery tracking
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_status: RecoveryStatus = RecoveryStatus.NOT_ATTEMPTED
    recovery_details: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'call_id': self.call_id,
            'error_category': self.error_category,
            'error_message': self.error_message,
            'exception_type': self.exception_type,
            'context': self.context,
            'occurred_at': self.occurred_at.isoformat(),
            'processing_stage': self.processing_stage,
            'retry_attempt': self.retry_attempt,
            'escalation_level': self.escalation_level.value,
            'recovery_attempted': self.recovery_attempted,
            'recovery_successful': self.recovery_successful,
            'recovery_status': self.recovery_status.value,
            'recovery_details': self.recovery_details,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorEvent':
        """Create ErrorEvent from dictionary"""
        return cls(
            error_id=data['error_id'],
            call_id=data['call_id'],
            error_category=data['error_category'],
            error_message=data['error_message'],
            exception_type=data['exception_type'],
            context=data.get('context', {}),
            occurred_at=datetime.fromisoformat(data['occurred_at']),
            processing_stage=data.get('processing_stage', 'unknown'),
            retry_attempt=data.get('retry_attempt', 0),
            escalation_level=EscalationLevel(data.get('escalation_level', 'low')),
            recovery_attempted=data.get('recovery_attempted', False),
            recovery_successful=data.get('recovery_successful', False),
            recovery_status=RecoveryStatus(data.get('recovery_status', 'not_attempted')),
            recovery_details=data.get('recovery_details'),
            metadata=data.get('metadata', {})
        )

class ErrorMetrics(BaseModel):
    """Comprehensive error metrics for monitoring and alerting"""
    
    # Count metrics
    total_errors: int = 0
    errors_by_category: Dict[str, int] = Field(default_factory=dict)
    errors_by_severity: Dict[str, int] = Field(default_factory=dict)
    errors_by_stage: Dict[str, int] = Field(default_factory=dict)
    
    # Time-based metrics
    errors_last_hour: int = 0
    errors_last_day: int = 0
    errors_last_week: int = 0
    
    # Recovery metrics
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    recovery_success_rate: float = 0.0
    
    # Escalation metrics
    escalations_by_level: Dict[str, int] = Field(default_factory=dict)
    escalations_last_hour: int = 0
    escalations_last_day: int = 0
    
    # Performance impact metrics
    avg_processing_delay: float = 0.0
    max_processing_delay: float = 0.0
    calls_affected: int = 0
    
    # Trending metrics
    error_rate_trend: List[float] = Field(default_factory=list)  # Last 24 hours
    top_error_categories: List[tuple] = Field(default_factory=list)
    
    def calculate_rates(self) -> Dict[str, float]:
        """Calculate various error and recovery rates"""
        return {
            'overall_error_rate': self.total_errors / max(self.calls_affected, 1) * 100,
            'recovery_success_rate': self.successful_recoveries / max(self.recovery_attempts, 1) * 100,
            'escalation_rate': sum(self.escalations_by_level.values()) / max(self.total_errors, 1) * 100,
            'hourly_error_rate': self.errors_last_hour / max(1, 1) * 100,  # Per hour
            'daily_error_rate': self.errors_last_day / max(24, 24) * 100   # Per day
        }

@dataclass
class MonitoringAlert:
    """Alert generated by error monitoring system"""
    alert_id: str
    alert_type: str
    severity: ErrorSeverity
    title: str
    description: str
    triggered_at: datetime = field(default_factory=datetime.now)
    
    # Trigger conditions
    error_category: Optional[str] = None
    error_threshold: Optional[float] = None
    time_window_minutes: Optional[int] = None
    
    # Context
    affected_calls: List[str] = field(default_factory=list)
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'triggered_at': self.triggered_at.isoformat(),
            'error_category': self.error_category,
            'error_threshold': self.error_threshold,
            'time_window_minutes': self.time_window_minutes,
            'affected_calls': self.affected_calls,
            'error_count': self.error_count,
            'metadata': self.metadata,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'acknowledged_by': self.acknowledged_by,
            'resolved_by': self.resolved_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class SystemHealth(BaseModel):
    """Overall system health metrics"""
    
    # Health status
    overall_status: str = "healthy"  # healthy, degraded, unhealthy, critical
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Component health
    claude_api_healthy: bool = True
    database_healthy: bool = True
    queue_healthy: bool = True
    processing_healthy: bool = True
    
    # Current metrics
    current_error_rate: float = 0.0
    queue_depth: int = 0
    processing_latency_p99: float = 0.0
    success_rate_24h: float = 100.0
    
    # Capacity metrics
    calls_processed_today: int = 0
    calls_failed_today: int = 0
    api_quota_usage: float = 0.0
    
    # Active issues
    active_alerts: int = 0
    critical_errors_last_hour: int = 0
    
    def calculate_overall_status(self) -> str:
        """Calculate overall system health status"""
        if not all([
            self.claude_api_healthy,
            self.database_healthy,
            self.queue_healthy,
            self.processing_healthy
        ]):
            return "critical"
        
        if (self.current_error_rate > 20 or 
            self.critical_errors_last_hour > 0 or
            self.success_rate_24h < 80):
            return "unhealthy"
        
        if (self.current_error_rate > 10 or 
            self.processing_latency_p99 > 300 or
            self.success_rate_24h < 95):
            return "degraded"
        
        return "healthy"
    
    def get_health_score(self) -> float:
        """Get numeric health score (0-100)"""
        component_score = sum([
            self.claude_api_healthy,
            self.database_healthy, 
            self.queue_healthy,
            self.processing_healthy
        ]) / 4 * 100
        
        performance_score = min(100, (
            (1 - min(self.current_error_rate / 100, 1)) * 30 +
            (self.success_rate_24h / 100) * 40 + 
            (1 - min(self.processing_latency_p99 / 600, 1)) * 30
        ))
        
        # Weight components (70% performance, 30% component health)
        return (performance_score * 0.7) + (component_score * 0.3)

@dataclass
class AlertRule:
    """Configuration for error monitoring alert rules"""
    rule_id: str
    rule_name: str
    description: str
    
    # Trigger conditions
    error_category: Optional[str] = None
    error_threshold: float = 10.0  # Errors per time window
    time_window_minutes: int = 60
    severity_threshold: ErrorSeverity = ErrorSeverity.HIGH
    
    # Alert configuration
    alert_severity: ErrorSeverity = ErrorSeverity.MEDIUM
    enabled: bool = True
    
    # Notification settings
    notification_channels: List[str] = field(default_factory=list)  # slack, email, pager
    notification_interval_minutes: int = 30  # Minimum time between notifications
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def check_trigger(self, metrics: ErrorMetrics, recent_errors: List[ErrorEvent]) -> bool:
        """Check if alert should be triggered based on current metrics"""
        if not self.enabled:
            return False
        
        # Time window filter
        cutoff_time = datetime.now() - timedelta(minutes=self.time_window_minutes)
        window_errors = [e for e in recent_errors if e.occurred_at >= cutoff_time]
        
        # Category filter
        if self.error_category:
            window_errors = [e for e in window_errors if e.error_category == self.error_category]
        
        # Check threshold
        error_count = len(window_errors)
        if error_count >= self.error_threshold:
            return True
        
        # Check severity escalation
        high_severity_errors = [
            e for e in window_errors 
            if EscalationLevel(e.escalation_level) >= self.severity_threshold
        ]
        
        return len(high_severity_errors) > 0

class ErrorReportBuilder:
    """Builder for comprehensive error reports"""
    
    def __init__(self):
        self.events: List[ErrorEvent] = []
        self.metrics: Optional[ErrorMetrics] = None
        self.health: Optional[SystemHealth] = None
        
    def add_events(self, events: List[ErrorEvent]) -> 'ErrorReportBuilder':
        """Add error events to report"""
        self.events.extend(events)
        return self
    
    def set_metrics(self, metrics: ErrorMetrics) -> 'ErrorReportBuilder':
        """Set error metrics"""
        self.metrics = metrics
        return self
    
    def set_health(self, health: SystemHealth) -> 'ErrorReportBuilder':
        """Set system health"""
        self.health = health
        return self
    
    def build_summary_report(self) -> Dict[str, Any]:
        """Build summary error report"""
        return {
            'report_generated_at': datetime.now().isoformat(),
            'total_events': len(self.events),
            'time_range': {
                'earliest': min([e.occurred_at for e in self.events]).isoformat() if self.events else None,
                'latest': max([e.occurred_at for e in self.events]).isoformat() if self.events else None
            },
            'categories': self._analyze_categories(),
            'severity_distribution': self._analyze_severity(),
            'recovery_analysis': self._analyze_recovery(),
            'trends': self._analyze_trends(),
            'recommendations': self._generate_recommendations()
        }
    
    def build_detailed_report(self) -> Dict[str, Any]:
        """Build detailed error report with event details"""
        summary = self.build_summary_report()
        summary.update({
            'detailed_events': [e.to_dict() for e in self.events],
            'metrics': self.metrics.dict() if self.metrics else None,
            'system_health': self.health.dict() if self.health else None
        })
        return summary
    
    def _analyze_categories(self) -> Dict[str, Any]:
        """Analyze error categories"""
        category_counts = {}
        for event in self.events:
            category_counts[event.error_category] = category_counts.get(event.error_category, 0) + 1
        
        return {
            'distribution': category_counts,
            'top_categories': sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _analyze_severity(self) -> Dict[str, Any]:
        """Analyze severity distribution"""
        severity_counts = {}
        for event in self.events:
            severity = event.escalation_level.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return severity_counts
    
    def _analyze_recovery(self) -> Dict[str, Any]:
        """Analyze recovery patterns"""
        attempted = len([e for e in self.events if e.recovery_attempted])
        successful = len([e for e in self.events if e.recovery_successful])
        
        return {
            'total_recovery_attempts': attempted,
            'successful_recoveries': successful,
            'recovery_rate': (successful / attempted * 100) if attempted > 0 else 0,
            'common_recovery_actions': self._get_common_recovery_actions()
        }
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze error trends over time"""
        if not self.events:
            return {}
        
        # Group by hour
        hourly_counts = {}
        for event in self.events:
            hour_key = event.occurred_at.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
        
        return {
            'hourly_distribution': {k.isoformat(): v for k, v in hourly_counts.items()},
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else None
        }
    
    def _get_common_recovery_actions(self) -> List[str]:
        """Get most common recovery actions attempted"""
        actions = []
        for event in self.events:
            if event.recovery_details and 'action' in event.recovery_details:
                actions.append(event.recovery_details['action'])
        
        action_counts = {}
        for action in actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []
        
        # Check for common patterns
        category_counts = {}
        for event in self.events:
            category_counts[event.error_category] = category_counts.get(event.error_category, 0) + 1
        
        # High rate limit errors
        if category_counts.get('rate_limit_exceeded', 0) > 5:
            recommendations.append(
                "Consider implementing more aggressive rate limiting or request batching "
                "to reduce Claude API rate limit errors"
            )
        
        # High validation errors
        if category_counts.get('schema_validation_failed', 0) > 3:
            recommendations.append(
                "Review and improve schema validation logic or Claude prompt engineering "
                "to reduce validation failures"
            )
        
        # High database errors
        if category_counts.get('database_connection_failed', 0) > 2:
            recommendations.append(
                "Investigate database connection stability and consider implementing "
                "connection pooling or circuit breaker patterns"
            )
        
        # Low recovery rate
        attempted = len([e for e in self.events if e.recovery_attempted])
        successful = len([e for e in self.events if e.recovery_successful])
        if attempted > 0 and (successful / attempted) < 0.7:
            recommendations.append(
                "Recovery success rate is low. Review recovery strategies and "
                "consider implementing more robust fallback mechanisms"
            )
        
        return recommendations

# Utility functions for error tracking
def create_error_event(
    call_id: str,
    error_category: str,
    error_message: str,
    exception_type: str = "Exception",
    context: Dict[str, Any] = None,
    processing_stage: str = "unknown"
) -> ErrorEvent:
    """Utility function to create error event"""
    return ErrorEvent(
        error_id=f"{call_id}_{datetime.now().isoformat()}",
        call_id=call_id,
        error_category=error_category,
        error_message=error_message,
        exception_type=exception_type,
        context=context or {},
        processing_stage=processing_stage
    )

def calculate_error_metrics(events: List[ErrorEvent]) -> ErrorMetrics:
    """Calculate comprehensive error metrics from events"""
    if not events:
        return ErrorMetrics()
    
    # Time boundaries
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    
    # Count metrics
    errors_by_category = {}
    errors_by_severity = {}
    errors_by_stage = {}
    escalations_by_level = {}
    
    # Time-filtered counts
    errors_last_hour = 0
    errors_last_day = 0
    errors_last_week = 0
    escalations_last_hour = 0
    escalations_last_day = 0
    
    # Recovery metrics
    recovery_attempts = 0
    successful_recoveries = 0
    
    for event in events:
        # Category counts
        cat = event.error_category
        errors_by_category[cat] = errors_by_category.get(cat, 0) + 1
        
        # Severity counts (map escalation level to severity)
        sev = event.escalation_level.value
        errors_by_severity[sev] = errors_by_severity.get(sev, 0) + 1
        
        # Stage counts
        stage = event.processing_stage
        errors_by_stage[stage] = errors_by_stage.get(stage, 0) + 1
        
        # Escalation counts
        esc_level = event.escalation_level.value
        escalations_by_level[esc_level] = escalations_by_level.get(esc_level, 0) + 1
        
        # Time-based counts
        if event.occurred_at >= one_hour_ago:
            errors_last_hour += 1
            if event.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]:
                escalations_last_hour += 1
        
        if event.occurred_at >= one_day_ago:
            errors_last_day += 1
            if event.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]:
                escalations_last_day += 1
        
        if event.occurred_at >= one_week_ago:
            errors_last_week += 1
        
        # Recovery metrics
        if event.recovery_attempted:
            recovery_attempts += 1
            if event.recovery_successful:
                successful_recoveries += 1
    
    # Calculate rates
    recovery_success_rate = (successful_recoveries / recovery_attempts * 100) if recovery_attempts > 0 else 0
    
    # Top error categories
    top_error_categories = sorted(errors_by_category.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return ErrorMetrics(
        total_errors=len(events),
        errors_by_category=errors_by_category,
        errors_by_severity=errors_by_severity,
        errors_by_stage=errors_by_stage,
        errors_last_hour=errors_last_hour,
        errors_last_day=errors_last_day,
        errors_last_week=errors_last_week,
        recovery_attempts=recovery_attempts,
        successful_recoveries=successful_recoveries,
        failed_recoveries=recovery_attempts - successful_recoveries,
        recovery_success_rate=recovery_success_rate,
        escalations_by_level=escalations_by_level,
        escalations_last_hour=escalations_last_hour,
        escalations_last_day=escalations_last_day,
        top_error_categories=top_error_categories,
        calls_affected=len(set(e.call_id for e in events))
    )