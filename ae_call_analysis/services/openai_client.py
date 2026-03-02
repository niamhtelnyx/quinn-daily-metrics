"""
OpenAI API Client for AE Call Analysis System
Provides async interface to OpenAI API with comprehensive error handling, retry logic,
and bulletproof context overflow protection.

This replaces ClaudeClient for users with OpenAI Pro subscriptions.

Features:
- Pre-flight token counting using tiktoken
- Smart transcript truncation for large transcripts
- Automatic fallback to Claude for oversized content
- Comprehensive error handling with graceful degradation
- Detailed monitoring and logging
"""

import asyncio
import logging
import json
import time
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from openai import AsyncOpenAI
    from openai import (
        APIError, RateLimitError, APITimeoutError, 
        BadRequestError, AuthenticationError
    )
except ImportError:
    # Graceful fallback if openai not installed
    AsyncOpenAI = None
    APIError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception
    BadRequestError = Exception
    AuthenticationError = Exception

try:
    from ..config.settings import OpenAIConfig, ClaudeConfig, get_config
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import OpenAIConfig, ClaudeConfig, get_config

# Import our new robust modules
try:
    from .token_counter import TokenCounter, get_token_counter, check_fits_context, MODEL_LIMITS
    from .transcript_processor import TranscriptProcessor, TruncationStrategy, ProcessingResult
except ImportError:
    # Fallback for direct execution
    from token_counter import TokenCounter, get_token_counter, check_fits_context, MODEL_LIMITS
    from transcript_processor import TranscriptProcessor, TruncationStrategy, ProcessingResult

logger = logging.getLogger(__name__)


class AnalysisProvider(str, Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    CLAUDE = "claude"


@dataclass
class AnalysisResult:
    """Structured result from OpenAI analysis - same interface as Claude"""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    processing_time: float
    provider: str = "openai"
    preprocessing_info: Optional[Dict[str, Any]] = None


@dataclass
class TokenUsageMetrics:
    """Detailed token usage metrics for monitoring"""
    input_tokens: int = 0
    output_tokens: int = 0
    original_transcript_tokens: int = 0
    processed_transcript_tokens: int = 0
    system_prompt_tokens: int = 0
    was_truncated: bool = False
    truncation_strategy: Optional[str] = None
    truncation_ratio: float = 1.0
    used_fallback: bool = False
    fallback_provider: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'original_transcript_tokens': self.original_transcript_tokens,
            'processed_transcript_tokens': self.processed_transcript_tokens,
            'system_prompt_tokens': self.system_prompt_tokens,
            'was_truncated': self.was_truncated,
            'truncation_strategy': self.truncation_strategy,
            'truncation_ratio': self.truncation_ratio,
            'used_fallback': self.used_fallback,
            'fallback_provider': self.fallback_provider,
        }


class ContextOverflowError(Exception):
    """Raised when content exceeds context limits after all recovery attempts"""
    def __init__(self, message: str, token_details: Dict[str, Any] = None):
        super().__init__(message)
        self.token_details = token_details or {}


class OpenAIClient:
    """
    Async OpenAI API client for call analysis with bulletproof context overflow protection.
    
    Uses the same interface as ClaudeClient for easy swap-in replacement.
    
    Features:
    - Pre-flight token counting before API calls
    - Automatic transcript truncation using smart strategies
    - Fallback to Claude for very large transcripts
    - Comprehensive error handling and recovery
    - Detailed usage metrics and monitoring
    """
    
    # Safety margins
    CONTEXT_SAFETY_MARGIN = 0.95  # Use only 95% of available context
    MIN_OUTPUT_TOKENS = 2000     # Minimum reserved for response
    
    def __init__(self, config: 'OpenAIConfig', claude_config: Optional['ClaudeConfig'] = None):
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package is required. Install with: pip3 install openai"
            )
        
        self.config = config
        self.claude_config = claude_config
        self._request_count = 0
        self._last_request_time = 0
        
        # Initialize token counter
        self.token_counter = get_token_counter(config.model)
        
        # Initialize transcript processor
        self.transcript_processor = TranscriptProcessor(model=config.model)
        
        # Usage metrics tracking
        self._usage_metrics: List[TokenUsageMetrics] = []
        self._total_tokens_used = 0
        self._overflow_prevented_count = 0
        self._fallback_count = 0
        
        # Validate configuration
        if not config.api_key:
            raise ValueError(
                "OpenAI API key required.\n"
                "Set OPENAI_API_KEY environment variable.\n"
            )
        
        # Initialize client
        self.client = AsyncOpenAI(api_key=config.api_key)
        
        # Optional Claude client for fallback
        self._claude_client = None
        if claude_config and claude_config.api_key:
            self._init_claude_fallback(claude_config)
        
        # Get model limits
        model_limits = self.token_counter.get_model_limits()
        
        # Log initialization
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"OpenAI Client Initialized (Bulletproof Mode)")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Context Limit: {model_limits.context_limit:,} tokens")
        logger.info(f"  Safe Input Limit: {model_limits.effective_input_limit:,} tokens")
        logger.info(f"  Max Output: {config.max_tokens:,} tokens")
        logger.info(f"  Claude Fallback: {'✅ Available' if self._claude_client else '❌ Not configured'}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    def _init_claude_fallback(self, claude_config: 'ClaudeConfig') -> None:
        """Initialize Claude client for fallback on large transcripts"""
        try:
            from .claude_client import ClaudeClient
            self._claude_client = ClaudeClient(claude_config)
            logger.info("Claude fallback client initialized (200k context available)")
        except ImportError:
            logger.warning("Claude client not available - fallback disabled")
            self._claude_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Claude fallback: {e}")
            self._claude_client = None
    
    def _preflight_token_check(
        self, 
        transcript: str, 
        system_prompt: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Pre-flight check of token counts before API call.
        
        Returns:
            Tuple of (is_safe, details_dict)
        """
        fits, details = self.token_counter.check_within_limits(
            transcript, 
            system_prompt, 
            self.config.max_tokens
        )
        
        # Add model info
        details['model'] = self.config.model
        details['max_output_configured'] = self.config.max_tokens
        
        if not fits:
            logger.warning(
                f"⚠️ Pre-flight check FAILED: {details['total_required']:,} tokens required, "
                f"only {details['safe_limit']:,} available (overflow: {details['overflow_amount']:,})"
            )
        else:
            logger.debug(
                f"✅ Pre-flight check passed: {details['total_required']:,}/{details['safe_limit']:,} tokens "
                f"(headroom: {details['headroom']:,})"
            )
        
        return fits, details
    
    async def analyze_call_transcript(
        self, 
        transcript: str, 
        system_prompt: str,
        enable_fallback: bool = True,
        truncation_strategy: TruncationStrategy = TruncationStrategy.SMART_SECTIONS
    ) -> AnalysisResult:
        """
        Analyze call transcript using OpenAI with bulletproof context protection.
        
        Process:
        1. Pre-flight token check
        2. Truncate if needed using smart strategy
        3. Attempt OpenAI API call
        4. On context overflow error, truncate more aggressively and retry
        5. If still fails and Claude available, fallback to Claude
        6. Track all metrics
        
        Args:
            transcript: Raw call transcript text
            system_prompt: System prompt for analysis context
            enable_fallback: Whether to allow fallback to Claude
            truncation_strategy: Strategy for transcript truncation
            
        Returns:
            AnalysisResult with analysis content and metadata
            
        Raises:
            OpenAIAPIError: For API-related errors
            ContextOverflowError: If content exceeds limits after all recovery
            ValueError: For invalid input parameters
        """
        if not transcript.strip():
            raise ValueError("Transcript cannot be empty")
        
        if not system_prompt.strip():
            raise ValueError("System prompt cannot be empty")
        
        # Initialize metrics
        metrics = TokenUsageMetrics()
        
        # Count original tokens
        original_count = self.token_counter.count_tokens(transcript)
        metrics.original_transcript_tokens = original_count.total_tokens
        
        system_count = self.token_counter.count_tokens(system_prompt)
        metrics.system_prompt_tokens = system_count.total_tokens
        
        logger.info(
            f"Starting analysis - Transcript: {metrics.original_transcript_tokens:,} tokens, "
            f"System: {metrics.system_prompt_tokens:,} tokens"
        )
        
        start_time = time.time()
        
        # Step 1: Pre-flight check
        fits, details = self._preflight_token_check(transcript, system_prompt)
        
        # Step 2: Preprocess transcript if needed
        processed_transcript = transcript
        if not fits:
            logger.info(f"Applying {truncation_strategy.value} truncation strategy")
            
            result = self.transcript_processor.process_transcript(
                transcript,
                system_prompt,
                max_output_tokens=self.config.max_tokens,
                strategy=truncation_strategy
            )
            
            processed_transcript = result.processed_text
            metrics.processed_transcript_tokens = result.processed_tokens
            metrics.was_truncated = result.was_truncated
            metrics.truncation_strategy = result.strategy_used.value
            metrics.truncation_ratio = result.truncation_ratio
            
            self._overflow_prevented_count += 1
            
            logger.info(
                f"Truncation complete: {metrics.original_transcript_tokens:,} -> "
                f"{metrics.processed_transcript_tokens:,} tokens ({metrics.truncation_ratio:.1%} retained)"
            )
            
            # Verify it now fits
            fits_now, new_details = self._preflight_token_check(processed_transcript, system_prompt)
            if not fits_now:
                logger.warning(
                    f"Still over limit after truncation, overflow: {new_details['overflow_amount']:,}"
                )
        else:
            metrics.processed_transcript_tokens = metrics.original_transcript_tokens
        
        # Step 3: Attempt API call with retry on context overflow
        try:
            result = await self._execute_with_overflow_handling(
                processed_transcript,
                system_prompt,
                metrics,
                enable_fallback
            )
            
            processing_time = time.time() - start_time
            
            # Update metrics
            metrics.input_tokens = result.usage.get('input_tokens', 0)
            metrics.output_tokens = result.usage.get('output_tokens', 0)
            self._usage_metrics.append(metrics)
            self._total_tokens_used += metrics.input_tokens + metrics.output_tokens
            
            # Log success
            logger.info(
                f"✅ Analysis completed in {processing_time:.2f}s - "
                f"Input: {metrics.input_tokens:,}, Output: {metrics.output_tokens:,}"
            )
            
            # Add preprocessing info to result
            result.processing_time = processing_time
            result.preprocessing_info = metrics.to_dict()
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Analysis failed after {processing_time:.2f}s: {e}")
            raise
    
    async def _execute_with_overflow_handling(
        self,
        transcript: str,
        system_prompt: str,
        metrics: TokenUsageMetrics,
        enable_fallback: bool
    ) -> AnalysisResult:
        """
        Execute API call with overflow detection and recovery.
        """
        max_attempts = 3
        current_transcript = transcript
        
        for attempt in range(max_attempts):
            try:
                result = await self._execute_with_retry(
                    self._make_openai_request,
                    transcript=current_transcript,
                    system_prompt=system_prompt
                )
                
                return AnalysisResult(
                    content=result.choices[0].message.content,
                    usage={
                        'input_tokens': result.usage.prompt_tokens,
                        'output_tokens': result.usage.completion_tokens,
                    },
                    model=result.model,
                    finish_reason=result.choices[0].finish_reason,
                    processing_time=0,  # Will be set by caller
                    provider=AnalysisProvider.OPENAI.value
                )
                
            except BadRequestError as e:
                error_msg = str(e).lower()
                
                # Check for context overflow errors
                if any(kw in error_msg for kw in ['context', 'token', 'length', 'maximum']):
                    logger.warning(f"Context overflow detected (attempt {attempt + 1})")
                    
                    if attempt < max_attempts - 1:
                        # Try more aggressive truncation
                        logger.info("Applying more aggressive truncation...")
                        
                        # Calculate how much we need to cut
                        current_tokens = self.token_counter.count_tokens(current_transcript).total_tokens
                        target_tokens = int(current_tokens * 0.7)  # Reduce by 30%
                        
                        # Re-truncate
                        result = self.transcript_processor.process_transcript(
                            current_transcript,
                            system_prompt,
                            max_output_tokens=self.config.max_tokens,
                            strategy=TruncationStrategy.SPEAKER_AWARE
                        )
                        current_transcript = result.processed_text
                        
                        metrics.truncation_ratio *= 0.7
                        metrics.truncation_strategy = "emergency_" + result.strategy_used.value
                        
                        continue
                    
                    # All OpenAI attempts failed - try Claude fallback
                    if enable_fallback and self._claude_client:
                        logger.info("Attempting Claude fallback (200k context)...")
                        return await self._fallback_to_claude(
                            current_transcript, system_prompt, metrics
                        )
                    
                    # No fallback available
                    raise ContextOverflowError(
                        f"Context overflow after {max_attempts} truncation attempts",
                        token_details={
                            'model': self.config.model,
                            'original_tokens': metrics.original_transcript_tokens,
                            'processed_tokens': metrics.processed_transcript_tokens,
                        }
                    )
                
                # Non-overflow error
                raise OpenAIAPIError(f"API error: {str(e)}") from e
    
    async def _fallback_to_claude(
        self,
        transcript: str,
        system_prompt: str,
        metrics: TokenUsageMetrics
    ) -> AnalysisResult:
        """
        Fallback to Claude for large transcripts.
        Claude has 200k context vs OpenAI's 128k.
        """
        if not self._claude_client:
            raise OpenAIAPIError("Claude fallback not available")
        
        try:
            logger.info(f"Using Claude fallback - transcript: {len(transcript):,} chars")
            
            result = await self._claude_client.analyze_call_transcript(
                transcript, system_prompt
            )
            
            # Update metrics
            metrics.used_fallback = True
            metrics.fallback_provider = AnalysisProvider.CLAUDE.value
            self._fallback_count += 1
            
            logger.info(f"✅ Claude fallback successful")
            
            return AnalysisResult(
                content=result.content,
                usage={
                    'input_tokens': result.usage.get('input_tokens', 0),
                    'output_tokens': result.usage.get('output_tokens', 0),
                },
                model=result.model,
                finish_reason=result.finish_reason,
                processing_time=result.processing_time,
                provider=AnalysisProvider.CLAUDE.value
            )
            
        except Exception as e:
            logger.error(f"Claude fallback failed: {e}")
            raise OpenAIAPIError(f"Both OpenAI and Claude fallback failed: {e}") from e
    
    async def analyze_with_tools(
        self, 
        transcript: str, 
        tools: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        Analyze transcript with function calling for structured output.
        Includes context overflow protection.
        """
        if not transcript.strip():
            raise ValueError("Transcript cannot be empty")
        
        if not tools:
            raise ValueError("At least one tool must be provided")
        
        # Preprocess transcript if needed
        system_prompt = "You are analyzing a sales call transcript."
        fits, details = self._preflight_token_check(transcript, system_prompt)
        
        processed_transcript = transcript
        if not fits:
            result = self.transcript_processor.process_transcript(
                transcript,
                system_prompt,
                max_output_tokens=self.config.max_tokens
            )
            processed_transcript = result.processed_text
        
        logger.info(f"Starting OpenAI tool-use analysis - {len(tools)} tools available")
        start_time = time.time()
        
        try:
            result = await self._execute_with_retry(
                self._make_tool_request,
                transcript=processed_transcript,
                tools=tools
            )
            
            processing_time = time.time() - start_time
            logger.info(f"OpenAI tool analysis completed in {processing_time:.2f}s")
            
            return AnalysisResult(
                content=self._extract_tool_results(result),
                usage={
                    'input_tokens': result.usage.prompt_tokens,
                    'output_tokens': result.usage.completion_tokens
                },
                model=result.model,
                finish_reason=result.choices[0].finish_reason,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OpenAI tool analysis failed after {processing_time:.2f}s: {e}")
            raise OpenAIAPIError(f"Tool analysis failed: {str(e)}") from e
    
    async def _make_openai_request(
        self, 
        transcript: str, 
        system_prompt: str
    ):
        """Make basic OpenAI API request"""
        response = await self.client.chat.completions.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"Please analyze this sales call transcript:\n\n{transcript}"
                }
            ]
        )
        return response
    
    async def _make_tool_request(
        self, 
        transcript: str, 
        tools: List[Dict[str, Any]]
    ):
        """Make OpenAI API request with function calling"""
        openai_tools = self._convert_tools_to_openai_format(tools)
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            tools=openai_tools,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this sales call transcript using the provided tools:\n\n{transcript}"
                }
            ]
        )
        return response
    
    def _convert_tools_to_openai_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Claude tool format to OpenAI function format"""
        openai_tools = []
        for tool in tools:
            if tool.get('type') == 'function':
                openai_tools.append(tool)
            else:
                openai_tools.append({
                    'type': 'function',
                    'function': {
                        'name': tool.get('name', ''),
                        'description': tool.get('description', ''),
                        'parameters': tool.get('input_schema', tool.get('parameters', {}))
                    }
                })
        return openai_tools
    
    def _extract_tool_results(self, response) -> str:
        """Extract tool call results from OpenAI response"""
        tool_results = []
        message = response.choices[0].message
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_results.append({
                    'tool_name': tool_call.function.name,
                    'tool_input': json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                })
        
        if message.content:
            tool_results.append({'text': message.content})
        
        return json.dumps(tool_results, indent=2)
    
    async def _execute_with_retry(self, func, **kwargs):
        """Execute function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                await self._respect_rate_limits()
                result = await func(**kwargs)
                self._request_count += 1
                self._last_request_time = time.time()
                return result
                
            except RateLimitError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    retry_delay = self._calculate_backoff(attempt)
                    logger.warning(f"Rate limit hit, retrying in {retry_delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(retry_delay)
                    continue
                logger.error("Rate limit retries exhausted")
                raise OpenAIAPIError("Rate limit exceeded after retries") from e
                    
            except APITimeoutError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.warning(f"API timeout, retrying in {backoff_delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(backoff_delay)
                    continue
                logger.error("API timeout retries exhausted")
                raise OpenAIAPIError("API timeout after retries") from e
                    
            except BadRequestError:
                # Let caller handle - may be context overflow
                raise
                    
            except AuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                raise OpenAIAPIError("Authentication failed - check API key") from e
                
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.warning(f"Unexpected error, retrying in {backoff_delay:.1f}s (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(backoff_delay)
                    continue
                logger.error(f"Unexpected error retries exhausted: {e}")
                raise OpenAIAPIError(f"Unexpected error: {str(e)}") from e
        
        raise OpenAIAPIError("All retry attempts exhausted") from last_exception
    
    async def _respect_rate_limits(self):
        """Implement basic rate limiting"""
        min_interval = 0.1
        if self._last_request_time > 0:
            time_since_last = time.time() - self._last_request_time
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        import random
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = delay * 0.25
        delay += random.uniform(-jitter, jitter)
        return max(0.1, delay)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenAI API connection with minimal request"""
        result = {
            "success": False,
            "model": self.config.model,
            "error": None,
            "claude_fallback_available": self._claude_client is not None
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            result["success"] = True
            result["model"] = response.model
            
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"✅ CONNECTION TEST: SUCCESS")
            logger.info(f"   Model: {response.model}")
            logger.info(f"   Claude Fallback: {'Available' if result['claude_fallback_available'] else 'Not configured'}")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return result
            
        except AuthenticationError as e:
            result["error"] = str(e)
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.error(f"❌ CONNECTION TEST: AUTHENTICATION FAILED")
            logger.error(f"   Error: {e}")
            logger.error(f"   Recovery: Verify OPENAI_API_KEY is set correctly")
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return result
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ CONNECTION TEST: FAILED - {e}")
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive client usage statistics"""
        model_limits = self.token_counter.get_model_limits()
        
        return {
            'request_count': self._request_count,
            'last_request_time': self._last_request_time,
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'context_limit': model_limits.context_limit,
            'safe_input_limit': model_limits.effective_input_limit,
            'total_tokens_used': self._total_tokens_used,
            'overflow_prevented_count': self._overflow_prevented_count,
            'fallback_count': self._fallback_count,
            'claude_fallback_available': self._claude_client is not None,
            'recent_usage': [m.to_dict() for m in self._usage_metrics[-10:]],  # Last 10
        }
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of usage metrics for monitoring"""
        if not self._usage_metrics:
            return {'message': 'No usage data yet'}
        
        truncation_count = sum(1 for m in self._usage_metrics if m.was_truncated)
        fallback_count = sum(1 for m in self._usage_metrics if m.used_fallback)
        total_input = sum(m.input_tokens for m in self._usage_metrics)
        total_output = sum(m.output_tokens for m in self._usage_metrics)
        
        avg_truncation_ratio = (
            sum(m.truncation_ratio for m in self._usage_metrics if m.was_truncated) / 
            max(1, truncation_count)
        )
        
        return {
            'total_requests': len(self._usage_metrics),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'truncation_events': truncation_count,
            'truncation_rate': truncation_count / len(self._usage_metrics),
            'avg_truncation_retention': avg_truncation_ratio,
            'fallback_events': fallback_count,
            'fallback_rate': fallback_count / len(self._usage_metrics),
            'context_overflows_prevented': self._overflow_prevented_count,
        }


class OpenAIAPIError(Exception):
    """Custom exception for OpenAI API errors"""
    pass


# Factory function for easy initialization
def create_robust_openai_client(
    enable_claude_fallback: bool = True
) -> OpenAIClient:
    """
    Create a robust OpenAI client with optional Claude fallback.
    
    Args:
        enable_claude_fallback: Whether to enable Claude as fallback for large transcripts
        
    Returns:
        Configured OpenAIClient instance
    """
    config = get_config()
    
    claude_config = None
    if enable_claude_fallback and config.claude.api_key:
        claude_config = config.claude
    
    return OpenAIClient(config.openai, claude_config=claude_config)
