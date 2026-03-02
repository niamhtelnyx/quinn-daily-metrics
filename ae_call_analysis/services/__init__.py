"""
Services module for AE Call Analysis System
Provides business logic and external API integration services

Includes bulletproof context overflow protection:
- Pre-flight token counting
- Smart transcript truncation
- Automatic fallback to larger context models
"""

from .claude_client import ClaudeClient, ClaudeAPIError, AnalysisResult as ClaudeAnalysisResult
from .openai_client import (
    OpenAIClient, OpenAIAPIError, ContextOverflowError,
    AnalysisResult as OpenAIAnalysisResult, TokenUsageMetrics,
    create_robust_openai_client
)
from .token_counter import (
    TokenCounter, TokenCount, TokenLimits,
    get_token_counter, count_tokens, check_fits_context,
    recommend_model, MODEL_LIMITS
)
from .transcript_processor import (
    TranscriptProcessor, TruncationStrategy, ProcessingResult,
    process_transcript_for_model
)
from .analysis_prompts import TelnyxAnalysisPrompts, get_analysis_prompt_for_call, validate_tool_response

# Default AnalysisResult (from OpenAI since that's the preferred provider)
AnalysisResult = OpenAIAnalysisResult

__all__ = [
    # OpenAI (preferred) with bulletproof protection
    'OpenAIClient',
    'OpenAIAPIError',
    'ContextOverflowError',
    'OpenAIAnalysisResult',
    'TokenUsageMetrics',
    'create_robust_openai_client',
    
    # Token counting utilities
    'TokenCounter',
    'TokenCount', 
    'TokenLimits',
    'get_token_counter',
    'count_tokens',
    'check_fits_context',
    'recommend_model',
    'MODEL_LIMITS',
    
    # Transcript processing
    'TranscriptProcessor',
    'TruncationStrategy',
    'ProcessingResult',
    'process_transcript_for_model',
    
    # Claude (legacy/fallback)
    'ClaudeClient',
    'ClaudeAPIError', 
    'ClaudeAnalysisResult',
    
    # Common
    'AnalysisResult',
    'TelnyxAnalysisPrompts',
    'get_analysis_prompt_for_call',
    'validate_tool_response'
]