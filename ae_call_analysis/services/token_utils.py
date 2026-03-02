"""
Token Utilities for AE Call Analysis System

Provides high-level utilities for token management, monitoring, and safe API calls.
This module is the recommended interface for all token-related operations.

Usage:
    from services.token_utils import safe_prepare_call, log_token_usage, TokenBudget

Features:
- Pre-flight token validation
- Automatic truncation with strategy selection  
- Token usage logging for monitoring
- Budget management for rate limiting
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime

from .token_counter import (
    TokenCounter, 
    get_token_counter, 
    check_fits_context,
    TIKTOKEN_AVAILABLE,
    MODEL_LIMITS,
    TokenCount
)
from .transcript_processor import (
    TranscriptProcessor,
    TruncationStrategy,
    ProcessingResult
)

logger = logging.getLogger(__name__)


# =============================================================================
# Token Budget Management
# =============================================================================

@dataclass
class TokenBudget:
    """
    Manages token budget for API calls.
    
    Useful for:
    - Rate limiting
    - Cost tracking
    - Batch processing with limits
    """
    max_input_tokens: int = 1_000_000    # Per time period
    max_output_tokens: int = 200_000      # Per time period
    time_period_hours: int = 1
    
    # Tracking
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    calls_made: int = 0
    period_start: datetime = field(default_factory=datetime.now)
    
    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record token usage from an API call"""
        self._check_reset_period()
        self.input_tokens_used += input_tokens
        self.output_tokens_used += output_tokens
        self.calls_made += 1
    
    def can_make_call(self, estimated_input: int, estimated_output: int = 4096) -> Tuple[bool, str]:
        """Check if a call can be made within budget"""
        self._check_reset_period()
        
        if self.input_tokens_used + estimated_input > self.max_input_tokens:
            return False, f"Input token budget exceeded ({self.input_tokens_used:,}/{self.max_input_tokens:,})"
        
        if self.output_tokens_used + estimated_output > self.max_output_tokens:
            return False, f"Output token budget exceeded ({self.output_tokens_used:,}/{self.max_output_tokens:,})"
        
        return True, "Within budget"
    
    def _check_reset_period(self) -> None:
        """Reset counters if time period has elapsed"""
        now = datetime.now()
        hours_elapsed = (now - self.period_start).total_seconds() / 3600
        
        if hours_elapsed >= self.time_period_hours:
            self.input_tokens_used = 0
            self.output_tokens_used = 0
            self.calls_made = 0
            self.period_start = now
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current budget statistics"""
        self._check_reset_period()
        return {
            'input_used': self.input_tokens_used,
            'input_max': self.max_input_tokens,
            'input_pct': (self.input_tokens_used / self.max_input_tokens * 100) if self.max_input_tokens else 0,
            'output_used': self.output_tokens_used,
            'output_max': self.max_output_tokens,
            'output_pct': (self.output_tokens_used / self.max_output_tokens * 100) if self.max_output_tokens else 0,
            'calls_made': self.calls_made,
            'period_start': self.period_start.isoformat(),
        }


# Global budget instance (optional usage)
_global_budget: Optional[TokenBudget] = None


def get_global_budget() -> TokenBudget:
    """Get or create global token budget"""
    global _global_budget
    if _global_budget is None:
        _global_budget = TokenBudget()
    return _global_budget


# =============================================================================
# Safe Call Preparation
# =============================================================================

@dataclass
class PreparedCall:
    """Result of preparing a call for the API"""
    transcript: str
    system_prompt: str
    estimated_tokens: int
    was_truncated: bool
    truncation_ratio: float
    original_tokens: int
    strategy_used: Optional[str]
    warnings: list = field(default_factory=list)
    
    @property
    def is_safe(self) -> bool:
        """Check if call is safe to make"""
        return len(self.warnings) == 0 or all('warning' in w.lower() for w in self.warnings)


def safe_prepare_call(
    transcript: str,
    system_prompt: str,
    model: str = 'gpt-4o',
    max_output_tokens: int = 4096,
    strategy: TruncationStrategy = TruncationStrategy.SMART_SECTIONS
) -> PreparedCall:
    """
    Safely prepare a transcript for an API call.
    
    This is the RECOMMENDED way to prepare any transcript before sending to
    OpenAI or Claude APIs. It handles:
    - Token counting
    - Automatic truncation if needed
    - Logging and monitoring
    
    Args:
        transcript: Raw transcript text
        system_prompt: System prompt for the call
        model: Target model (default: gpt-4o)
        max_output_tokens: Reserved tokens for response
        strategy: Truncation strategy if needed
        
    Returns:
        PreparedCall with processed transcript and metadata
        
    Example:
        prepared = safe_prepare_call(transcript, SYSTEM_PROMPT)
        if prepared.is_safe:
            result = await client.analyze_call_transcript(
                prepared.transcript, 
                prepared.system_prompt
            )
    """
    warnings = []
    
    # Verify tiktoken is available
    if not TIKTOKEN_AVAILABLE:
        warnings.append("WARNING: tiktoken not installed, using estimation")
    
    # Get token counter
    counter = get_token_counter(model)
    
    # Count original tokens
    original_count = counter.count_tokens(transcript)
    original_tokens = original_count.total_tokens
    
    # Check if truncation needed
    fits, details = counter.check_within_limits(transcript, system_prompt, max_output_tokens)
    
    if fits:
        # No truncation needed
        return PreparedCall(
            transcript=transcript,
            system_prompt=system_prompt,
            estimated_tokens=details['total_required'],
            was_truncated=False,
            truncation_ratio=1.0,
            original_tokens=original_tokens,
            strategy_used=None,
            warnings=warnings
        )
    
    # Need truncation
    logger.warning(
        f"Transcript requires truncation: {original_tokens:,} tokens, "
        f"overflow: {details['overflow_amount']:,}"
    )
    
    processor = TranscriptProcessor(model=model)
    result = processor.process_transcript(
        transcript,
        system_prompt,
        max_output_tokens=max_output_tokens,
        strategy=strategy
    )
    
    # Verify it now fits
    fits_now, new_details = counter.check_within_limits(
        result.processed_text, system_prompt, max_output_tokens
    )
    
    if not fits_now:
        warnings.append(f"WARNING: Still over limit after truncation by {new_details['overflow_amount']:,}")
    
    return PreparedCall(
        transcript=result.processed_text,
        system_prompt=system_prompt,
        estimated_tokens=new_details['total_required'],
        was_truncated=True,
        truncation_ratio=result.truncation_ratio,
        original_tokens=original_tokens,
        strategy_used=result.strategy_used.value,
        warnings=warnings
    )


# =============================================================================
# Token Usage Logging
# =============================================================================

def log_token_usage(
    call_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    was_truncated: bool = False,
    truncation_ratio: float = 1.0,
    processing_time: float = 0.0,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log token usage for monitoring and debugging.
    
    Outputs structured log data that can be ingested by monitoring systems.
    
    Args:
        call_id: Unique identifier for the call being analyzed
        model: Model used (e.g., 'gpt-4o')
        input_tokens: Input tokens used
        output_tokens: Output tokens used
        was_truncated: Whether transcript was truncated
        truncation_ratio: Ratio of original content retained
        processing_time: Time taken for API call
        extra: Additional metadata
    """
    log_data = {
        'event': 'token_usage',
        'call_id': call_id,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'was_truncated': was_truncated,
        'truncation_ratio': truncation_ratio,
        'processing_time_ms': int(processing_time * 1000),
        'timestamp': datetime.now().isoformat(),
    }
    
    if extra:
        log_data.update(extra)
    
    # Log as structured data
    logger.info(
        f"TOKEN_USAGE: call={call_id} model={model} "
        f"in={input_tokens:,} out={output_tokens:,} "
        f"truncated={was_truncated} ratio={truncation_ratio:.1%} "
        f"time={processing_time:.2f}s"
    )
    
    # Also log full structure for monitoring systems
    logger.debug(f"TOKEN_USAGE_DATA: {log_data}")


# =============================================================================
# Utility Functions
# =============================================================================

def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = 'gpt-4o'
) -> Dict[str, float]:
    """
    Estimate cost for token usage.
    
    Pricing as of 2024 (may need updates):
    - gpt-4o: $5/1M input, $15/1M output
    - gpt-4o-mini: $0.15/1M input, $0.60/1M output
    """
    pricing = {
        'gpt-4o': {'input': 5.0, 'output': 15.0},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'gpt-4-turbo': {'input': 10.0, 'output': 30.0},
    }
    
    rates = pricing.get(model, {'input': 5.0, 'output': 15.0})
    
    input_cost = (input_tokens / 1_000_000) * rates['input']
    output_cost = (output_tokens / 1_000_000) * rates['output']
    
    return {
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_cost': input_cost + output_cost,
        'currency': 'USD',
        'model': model,
    }


def get_system_status() -> Dict[str, Any]:
    """
    Get status of token management system.
    
    Useful for health checks and debugging.
    """
    return {
        'tiktoken_available': TIKTOKEN_AVAILABLE,
        'models_configured': list(MODEL_LIMITS.keys()),
        'global_budget': get_global_budget().get_stats() if _global_budget else None,
        'timestamp': datetime.now().isoformat(),
    }


def validate_environment() -> Tuple[bool, list]:
    """
    Validate that the environment is properly configured for token management.
    
    Returns:
        Tuple of (is_valid, issues_list)
    """
    issues = []
    
    if not TIKTOKEN_AVAILABLE:
        issues.append("CRITICAL: tiktoken not installed - run: pip3 install tiktoken")
    
    # Test token counting
    try:
        counter = get_token_counter('gpt-4o')
        result = counter.count_tokens("test")
        if result.method != 'tiktoken':
            issues.append(f"WARNING: Token counting using {result.method}, not tiktoken")
    except Exception as e:
        issues.append(f"ERROR: Token counter failed: {e}")
    
    return len([i for i in issues if 'CRITICAL' in i or 'ERROR' in i]) == 0, issues


# =============================================================================
# Decorator for Safe API Calls
# =============================================================================

def with_token_logging(call_id_extractor: Callable = None):
    """
    Decorator to add token logging to API call functions.
    
    Usage:
        @with_token_logging(lambda args: args[0].get('call_id'))
        async def analyze_call(call_data, system_prompt):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            processing_time = time.time() - start_time
            
            # Try to extract call_id
            call_id = 'unknown'
            if call_id_extractor:
                try:
                    call_id = call_id_extractor(args, kwargs) or 'unknown'
                except:
                    pass
            
            # Log if result has usage info
            if hasattr(result, 'usage') and isinstance(result.usage, dict):
                log_token_usage(
                    call_id=str(call_id),
                    model=getattr(result, 'model', 'unknown'),
                    input_tokens=result.usage.get('input_tokens', 0),
                    output_tokens=result.usage.get('output_tokens', 0),
                    was_truncated=getattr(result, 'preprocessing_info', {}).get('was_truncated', False),
                    truncation_ratio=getattr(result, 'preprocessing_info', {}).get('truncation_ratio', 1.0),
                    processing_time=processing_time
                )
            
            return result
        return wrapper
    return decorator


# =============================================================================
# Quick Check Function
# =============================================================================

def quick_check(transcript: str, model: str = 'gpt-4o') -> Dict[str, Any]:
    """
    Quick check if a transcript will fit in context.
    
    Returns a simple dict with fit status and recommendations.
    """
    counter = get_token_counter(model)
    system_prompt = "You are a sales call analyst."  # Typical prompt size
    
    fits, details = counter.check_within_limits(transcript, system_prompt)
    
    return {
        'fits': fits,
        'tokens': details['text_tokens'],
        'limit': details['safe_limit'],
        'overflow': details.get('overflow_amount', 0),
        'recommendation': 'OK' if fits else f'Truncate ~{details["overflow_amount"]:,} tokens',
        'model': model,
    }


if __name__ == "__main__":
    # Quick self-test
    logging.basicConfig(level=logging.INFO)
    
    is_valid, issues = validate_environment()
    print(f"Environment valid: {is_valid}")
    for issue in issues:
        print(f"  - {issue}")
    
    # Test quick check
    test_text = "Hello world. " * 1000
    result = quick_check(test_text)
    print(f"\nQuick check: {result}")
