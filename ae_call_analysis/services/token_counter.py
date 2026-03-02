"""
Token Counting Utility for AE Call Analysis System
Provides accurate token counting using tiktoken for OpenAI models and character estimation for Claude

Prevents context overflow errors by pre-flight checking token counts before API calls.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate OpenAI token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed - using character estimation for token counting")


@dataclass
class TokenCount:
    """Token count result with metadata"""
    total_tokens: int
    method: str  # 'tiktoken' | 'estimation'
    model_encoding: Optional[str] = None
    confidence: float = 1.0  # 1.0 for tiktoken, 0.8 for estimation


@dataclass 
class TokenLimits:
    """Model token limits configuration"""
    model_name: str
    context_limit: int           # Total context window
    safe_input_limit: int        # Safe limit for input (leaves room for output)
    max_output_tokens: int       # Max tokens for response
    reserve_buffer: int          # Extra safety buffer
    
    @property
    def effective_input_limit(self) -> int:
        """Calculate effective input limit accounting for output and buffer"""
        return self.context_limit - self.max_output_tokens - self.reserve_buffer


# Model limits registry
MODEL_LIMITS: Dict[str, TokenLimits] = {
    # OpenAI models
    'gpt-4o': TokenLimits('gpt-4o', 128000, 120000, 4096, 4000),
    'gpt-4o-mini': TokenLimits('gpt-4o-mini', 128000, 120000, 4096, 4000),
    'gpt-4-turbo': TokenLimits('gpt-4-turbo', 128000, 120000, 4096, 4000),
    'gpt-4-turbo-preview': TokenLimits('gpt-4-turbo-preview', 128000, 120000, 4096, 4000),
    'gpt-4': TokenLimits('gpt-4', 8192, 6000, 1024, 1000),
    'gpt-3.5-turbo': TokenLimits('gpt-3.5-turbo', 16385, 14000, 1024, 1000),
    'gpt-3.5-turbo-16k': TokenLimits('gpt-3.5-turbo-16k', 16385, 14000, 1024, 1000),
    
    # Claude models (for fallback scenarios)
    'claude-3-opus': TokenLimits('claude-3-opus', 200000, 180000, 4096, 8000),
    'claude-3-sonnet': TokenLimits('claude-3-sonnet', 200000, 180000, 4096, 8000),
    'claude-3-haiku': TokenLimits('claude-3-haiku', 200000, 180000, 4096, 8000),
    'claude-sonnet-4': TokenLimits('claude-sonnet-4', 200000, 180000, 4096, 8000),
    'claude-opus-4': TokenLimits('claude-opus-4', 200000, 180000, 4096, 8000),
}

# Encoding mappings for tiktoken
ENCODING_MAPPINGS = {
    'gpt-4o': 'o200k_base',
    'gpt-4o-mini': 'o200k_base',
    'gpt-4-turbo': 'cl100k_base',
    'gpt-4-turbo-preview': 'cl100k_base',
    'gpt-4': 'cl100k_base',
    'gpt-3.5-turbo': 'cl100k_base',
}


class TokenCounter:
    """
    Accurate token counting for LLM API calls.
    
    Uses tiktoken for OpenAI models when available, falls back to
    character-based estimation with conservative multipliers.
    """
    
    # Conservative chars per token for estimation (lower = more conservative)
    CHARS_PER_TOKEN_CONSERVATIVE = 3.5
    CHARS_PER_TOKEN_AVERAGE = 4.0
    
    def __init__(self, model: str = 'gpt-4o'):
        self.model = model
        self._encoder = None
        self._encoding_name = None
        
        # Initialize tiktoken encoder if available
        if TIKTOKEN_AVAILABLE:
            self._initialize_encoder()
        
        logger.info(f"TokenCounter initialized for model: {model}")
        logger.info(f"  tiktoken available: {TIKTOKEN_AVAILABLE}")
        if self._encoding_name:
            logger.info(f"  encoding: {self._encoding_name}")
    
    def _initialize_encoder(self) -> None:
        """Initialize tiktoken encoder for the model"""
        try:
            # Try model-specific encoding
            encoding_name = ENCODING_MAPPINGS.get(self.model)
            if encoding_name:
                self._encoder = tiktoken.get_encoding(encoding_name)
                self._encoding_name = encoding_name
                return
            
            # Try to get encoding for model directly
            try:
                self._encoder = tiktoken.encoding_for_model(self.model)
                self._encoding_name = f"model:{self.model}"
            except KeyError:
                # Fall back to cl100k_base (most common)
                self._encoder = tiktoken.get_encoding("cl100k_base")
                self._encoding_name = "cl100k_base (fallback)"
                
        except Exception as e:
            logger.warning(f"Failed to initialize tiktoken encoder: {e}")
            self._encoder = None
    
    def count_tokens(self, text: str) -> TokenCount:
        """
        Count tokens in text using the most accurate method available.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            TokenCount with token count and metadata
        """
        if not text:
            return TokenCount(total_tokens=0, method='empty')
        
        # Use tiktoken if available
        if self._encoder:
            try:
                tokens = self._encoder.encode(text)
                return TokenCount(
                    total_tokens=len(tokens),
                    method='tiktoken',
                    model_encoding=self._encoding_name,
                    confidence=1.0
                )
            except Exception as e:
                logger.warning(f"tiktoken encoding failed, falling back to estimation: {e}")
        
        # Fall back to conservative character estimation
        estimated_tokens = int(len(text) / self.CHARS_PER_TOKEN_CONSERVATIVE)
        return TokenCount(
            total_tokens=estimated_tokens,
            method='estimation',
            confidence=0.8
        )
    
    def count_messages_tokens(
        self, 
        messages: list,
        system_prompt: Optional[str] = None
    ) -> TokenCount:
        """
        Count tokens for a list of chat messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            
        Returns:
            TokenCount for all messages combined
        """
        total_tokens = 0
        
        # Count system prompt if provided
        if system_prompt:
            result = self.count_tokens(system_prompt)
            total_tokens += result.total_tokens
            # Add overhead for message structure
            total_tokens += 4  # <|im_start|>system\n...<|im_end|>
        
        # Count each message
        for message in messages:
            content = message.get('content', '')
            if isinstance(content, str):
                result = self.count_tokens(content)
                total_tokens += result.total_tokens
            elif isinstance(content, list):
                # Handle multi-part content (images, etc.)
                for part in content:
                    if isinstance(part, dict) and 'text' in part:
                        result = self.count_tokens(part['text'])
                        total_tokens += result.total_tokens
            
            # Add overhead for message structure
            total_tokens += 4  # <|im_start|>{role}\n...<|im_end|>
        
        # Add final assistant prompt overhead
        total_tokens += 2
        
        method = 'tiktoken' if self._encoder else 'estimation'
        return TokenCount(
            total_tokens=total_tokens,
            method=method,
            model_encoding=self._encoding_name,
            confidence=1.0 if self._encoder else 0.8
        )
    
    def get_model_limits(self) -> TokenLimits:
        """Get token limits for the current model"""
        # Try exact match
        if self.model in MODEL_LIMITS:
            return MODEL_LIMITS[self.model]
        
        # Try prefix match
        for model_key, limits in MODEL_LIMITS.items():
            if self.model.startswith(model_key):
                return limits
        
        # Default conservative limits
        logger.warning(f"Unknown model {self.model}, using conservative defaults")
        return TokenLimits(
            model_name=self.model,
            context_limit=8000,
            safe_input_limit=6000,
            max_output_tokens=1024,
            reserve_buffer=1000
        )
    
    def check_within_limits(
        self, 
        text: str, 
        system_prompt: Optional[str] = None,
        output_tokens: int = 4096
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if text fits within model's context limits.
        
        Args:
            text: Main content text (e.g., transcript)
            system_prompt: System prompt if any
            output_tokens: Reserved tokens for response
            
        Returns:
            Tuple of (is_within_limits, details_dict)
        """
        limits = self.get_model_limits()
        
        # Count tokens
        text_count = self.count_tokens(text)
        system_count = self.count_tokens(system_prompt) if system_prompt else TokenCount(0, 'empty')
        
        total_input = text_count.total_tokens + system_count.total_tokens
        total_with_output = total_input + output_tokens + 100  # 100 for message overhead
        
        available = limits.context_limit - limits.reserve_buffer
        is_safe = total_with_output <= available
        
        details = {
            'model': self.model,
            'text_tokens': text_count.total_tokens,
            'system_tokens': system_count.total_tokens,
            'output_reserved': output_tokens,
            'total_required': total_with_output,
            'context_limit': limits.context_limit,
            'safe_limit': available,
            'is_within_limits': is_safe,
            'overflow_amount': max(0, total_with_output - available),
            'headroom': max(0, available - total_with_output),
            'counting_method': text_count.method,
            'confidence': text_count.confidence
        }
        
        if not is_safe:
            logger.warning(
                f"Token limit exceeded: {total_with_output:,} > {available:,} "
                f"(overflow: {details['overflow_amount']:,})"
            )
        
        return is_safe, details
    
    def calculate_max_transcript_tokens(
        self,
        system_prompt: str,
        output_tokens: int = 4096
    ) -> int:
        """
        Calculate maximum tokens available for transcript.
        
        Args:
            system_prompt: The system prompt to use
            output_tokens: Reserved tokens for response
            
        Returns:
            Maximum tokens available for transcript content
        """
        limits = self.get_model_limits()
        system_count = self.count_tokens(system_prompt)
        
        # Calculate available tokens
        available = limits.context_limit - limits.reserve_buffer
        max_transcript = available - system_count.total_tokens - output_tokens - 200  # Overhead
        
        return max(0, max_transcript)


# Convenience functions
@lru_cache(maxsize=8)
def get_token_counter(model: str = 'gpt-4o') -> TokenCounter:
    """Get cached token counter for model"""
    return TokenCounter(model)


def count_tokens(text: str, model: str = 'gpt-4o') -> int:
    """Quick token count for text"""
    counter = get_token_counter(model)
    return counter.count_tokens(text).total_tokens


def check_fits_context(
    transcript: str,
    system_prompt: str,
    model: str = 'gpt-4o',
    output_tokens: int = 4096
) -> Tuple[bool, int]:
    """
    Quick check if transcript fits in model context.
    
    Returns:
        Tuple of (fits, overflow_amount)
    """
    counter = get_token_counter(model)
    fits, details = counter.check_within_limits(transcript, system_prompt, output_tokens)
    return fits, details.get('overflow_amount', 0)


def estimate_chars_for_tokens(tokens: int) -> int:
    """Estimate character count for given token count"""
    return int(tokens * TokenCounter.CHARS_PER_TOKEN_CONSERVATIVE)


# Model recommendation based on transcript size
def recommend_model(
    transcript: str,
    system_prompt: str,
    preferred_model: str = 'gpt-4o'
) -> Tuple[str, str]:
    """
    Recommend best model based on transcript size.
    
    Args:
        transcript: The transcript to analyze
        system_prompt: System prompt to use
        preferred_model: Preferred model if it fits
        
    Returns:
        Tuple of (recommended_model, reason)
    """
    counter = get_token_counter(preferred_model)
    fits, details = counter.check_within_limits(transcript, system_prompt)
    
    if fits:
        return preferred_model, "Transcript fits within model limits"
    
    # Try Claude as fallback (larger context)
    claude_counter = get_token_counter('claude-3-sonnet')
    claude_fits, claude_details = claude_counter.check_within_limits(transcript, system_prompt)
    
    if claude_fits:
        return 'claude-3-sonnet', f"Transcript too large for {preferred_model}, using Claude (200k context)"
    
    # Neither fits - need truncation
    return preferred_model, f"Transcript exceeds all model limits, truncation required"


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    counter = TokenCounter('gpt-4o')
    
    # Test with sample text
    sample = "Hello, this is a test transcript. " * 100
    result = counter.count_tokens(sample)
    print(f"Sample tokens: {result.total_tokens} (method: {result.method})")
    
    # Test limits check
    fits, details = counter.check_within_limits(sample, "You are a helpful assistant.")
    print(f"Fits within limits: {fits}")
    print(f"Details: {details}")
