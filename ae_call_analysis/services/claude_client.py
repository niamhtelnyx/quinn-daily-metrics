"""
Claude API Client for AE Call Analysis System
Provides async interface to Claude API with comprehensive error handling and retry logic
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import anthropic
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic._exceptions import (
        APIError, RateLimitError, APITimeoutError, 
        BadRequestError, AuthenticationError
    )
except ImportError:
    # Graceful fallback if anthropic not installed
    anthropic = None
    Anthropic = None
    AsyncAnthropic = None
    APIError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception
    BadRequestError = Exception
    AuthenticationError = Exception

try:
    from ..config.settings import ClaudeConfig
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import ClaudeConfig

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Structured result from Claude analysis"""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    processing_time: float

class ClaudeClient:
    """
    Async Claude API client with hybrid authentication support.
    
    Authentication modes:
    - "direct": Production API key from environment variable
    - "clawdbot": Development OAuth via Clawdbot auth profiles  
    - "claude_cli": Development OAuth via Claude CLI credentials
    - "none": No authentication (client will not function)
    
    All OAuth tokens (sk-ant-oat01-...) work identically to API keys with
    the Anthropic API - no special handling required.
    """
    
    # Class-level auth mode descriptions
    AUTH_MODE_LABELS = {
        "direct": "🔑 Production (API Key)",
        "clawdbot": "🔐 Development (Clawdbot OAuth)",
        "claude_cli": "🔐 Development (Claude CLI OAuth)",
        "none": "⚠️ No Authentication"
    }
    
    def __init__(self, config: ClaudeConfig):
        if anthropic is None:
            raise ImportError(
                "anthropic package is required. Install with: pip install anthropic>=0.15.0"
            )
        
        self.config = config
        self._request_count = 0
        self._last_request_time = 0
        
        # Get auth mode (with backwards compatibility)
        auth_mode = getattr(config, 'auth_mode', None)
        if auth_mode is None:
            # Infer from token format for backwards compatibility
            if config.api_key.startswith("sk-ant-oat"):
                auth_mode = "clawdbot"  # OAuth token
            elif config.api_key:
                auth_mode = "direct"  # Standard API key
            else:
                auth_mode = "none"
        
        self.auth_mode = auth_mode
        
        # Validate configuration
        if not config.api_key:
            raise ValueError(
                "Claude authentication required. Options:\n"
                "\n"
                "PRODUCTION:\n"
                "  export ANTHROPIC_API_KEY='sk-ant-api03-...'\n"
                "\n"
                "DEVELOPMENT:\n"
                "  Option 1: Run 'claude auth login' (Claude CLI)\n"
                "  Option 2: Configure Clawdbot OAuth profiles\n"
                "            (~/.clawdbot/agents/main/agent/auth-profiles.json)\n"
                "\n"
                "Authentication is auto-detected in this priority order."
            )
        
        # Initialize client - all token types work the same way
        self.client = AsyncAnthropic(api_key=config.api_key)
        
        # Log initialization with mode context
        mode_label = self.AUTH_MODE_LABELS.get(auth_mode, f"Unknown ({auth_mode})")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"Claude Client Initialized")
        logger.info(f"  Auth Mode: {mode_label}")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Max Tokens: {config.max_tokens}")
        if auth_mode in ("clawdbot", "claude_cli"):
            logger.info(f"  Note: Using OAuth - no console.anthropic.com needed!")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    async def analyze_call_transcript(
        self, 
        transcript: str, 
        system_prompt: str
    ) -> AnalysisResult:
        """
        Analyze call transcript using Claude with structured output
        
        Args:
            transcript: Raw call transcript text
            system_prompt: System prompt for analysis context
            
        Returns:
            AnalysisResult with analysis content and metadata
            
        Raises:
            ClaudeAPIError: For API-related errors
            ValueError: For invalid input parameters
        """
        if not transcript.strip():
            raise ValueError("Transcript cannot be empty")
        
        if not system_prompt.strip():
            raise ValueError("System prompt cannot be empty")
        
        # Log request details (without sensitive data)
        logger.info(f"Starting Claude analysis - transcript length: {len(transcript)}")
        start_time = time.time()
        
        try:
            # Execute the analysis with retry logic
            result = await self._execute_with_retry(
                self._make_claude_request,
                transcript=transcript,
                system_prompt=system_prompt
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Claude analysis completed in {processing_time:.2f}s")
            
            return AnalysisResult(
                content=result.content[0].text,
                usage={
                    'input_tokens': result.usage.input_tokens,
                    'output_tokens': result.usage.output_tokens
                },
                model=result.model,
                finish_reason=result.stop_reason,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Claude analysis failed after {processing_time:.2f}s: {e}")
            raise ClaudeAPIError(f"Analysis failed: {str(e)}") from e
    
    async def analyze_with_tools(
        self, 
        transcript: str, 
        tools: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        Analyze transcript with tool use for structured output
        
        Args:
            transcript: Raw call transcript text
            tools: List of tool definitions for structured output
            
        Returns:
            AnalysisResult with tool call results
        """
        if not transcript.strip():
            raise ValueError("Transcript cannot be empty")
        
        if not tools:
            raise ValueError("At least one tool must be provided")
        
        logger.info(f"Starting Claude tool-use analysis - {len(tools)} tools available")
        start_time = time.time()
        
        try:
            result = await self._execute_with_retry(
                self._make_tool_request,
                transcript=transcript,
                tools=tools
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Claude tool analysis completed in {processing_time:.2f}s")
            
            return AnalysisResult(
                content=self._extract_tool_results(result),
                usage={
                    'input_tokens': result.usage.input_tokens,
                    'output_tokens': result.usage.output_tokens
                },
                model=result.model,
                finish_reason=result.stop_reason,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Claude tool analysis failed after {processing_time:.2f}s: {e}")
            raise ClaudeAPIError(f"Tool analysis failed: {str(e)}") from e
    
    async def _make_claude_request(
        self, 
        transcript: str, 
        system_prompt: str
    ):
        """Make basic Claude API request"""
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[
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
        """Make Claude API request with tool use"""
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            tools=tools,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this sales call transcript using the provided tools:\n\n{transcript}"
                }
            ]
        )
        return response
    
    def _extract_tool_results(self, response) -> str:
        """Extract tool call results from Claude response"""
        tool_results = []
        
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                tool_results.append({
                    'tool_name': content_block.name,
                    'tool_input': content_block.input
                })
            elif hasattr(content_block, 'text'):
                # Regular text response
                tool_results.append({'text': content_block.text})
        
        return json.dumps(tool_results, indent=2)
    
    async def _execute_with_retry(self, func, **kwargs):
        """Execute function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Rate limiting
                await self._respect_rate_limits()
                
                # Execute the function
                result = await func(**kwargs)
                self._request_count += 1
                self._last_request_time = time.time()
                
                return result
                
            except RateLimitError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    # Extract retry delay from headers if available
                    retry_delay = self._extract_retry_delay(e) or self._calculate_backoff(attempt)
                    logger.warning(f"Rate limit hit, retrying in {retry_delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error("Rate limit retries exhausted")
                    raise ClaudeAPIError("Rate limit exceeded after retries") from e
                    
            except APITimeoutError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.warning(f"API timeout, retrying in {backoff_delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    logger.error("API timeout retries exhausted")
                    raise ClaudeAPIError("API timeout after retries") from e
                    
            except (APIError, BadRequestError) as e:
                # These are usually not retriable
                logger.error(f"Non-retriable API error: {e}")
                raise ClaudeAPIError(f"API error: {str(e)}") from e
                
            except AuthenticationError as e:
                # Authentication errors are never retriable
                logger.error(f"Authentication error: {e}")
                raise ClaudeAPIError("Authentication failed - check API key") from e
                
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.warning(f"Unexpected error, retrying in {backoff_delay:.1f}s (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    logger.error(f"Unexpected error retries exhausted: {e}")
                    raise ClaudeAPIError(f"Unexpected error: {str(e)}") from e
        
        # Should not reach here, but just in case
        raise ClaudeAPIError("All retry attempts exhausted") from last_exception
    
    async def _respect_rate_limits(self):
        """Implement basic rate limiting to avoid hitting API limits"""
        # Simple rate limiting - ensure minimum time between requests
        min_interval = 0.1  # 100ms between requests (600 req/min max)
        
        if self._last_request_time > 0:
            time_since_last = time.time() - self._last_request_time
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        base_delay = 1.0  # 1 second base delay
        max_delay = 60.0  # Cap at 60 seconds
        
        # Exponential backoff: 2^attempt
        delay = min(base_delay * (2 ** attempt), max_delay)
        
        # Add jitter (±25% randomization)
        import random
        jitter = delay * 0.25
        delay += random.uniform(-jitter, jitter)
        
        return max(0.1, delay)  # Minimum 100ms delay
    
    def _extract_retry_delay(self, error: Exception) -> Optional[float]:
        """Extract retry delay from rate limit error headers"""
        try:
            # Try to extract from error message or headers
            # Claude API may include retry-after information
            if hasattr(error, 'response') and hasattr(error.response, 'headers'):
                retry_after = error.response.headers.get('retry-after')
                if retry_after:
                    return float(retry_after)
        except:
            pass
        
        return None
    
    def _handle_api_error(self, error: Exception) -> None:
        """Handle and categorize API errors for logging and monitoring"""
        if isinstance(error, RateLimitError):
            logger.warning(f"Rate limit error: {error}")
        elif isinstance(error, APITimeoutError):
            logger.warning(f"Timeout error: {error}")
        elif isinstance(error, AuthenticationError):
            logger.error(f"Authentication error: {error}")
        elif isinstance(error, BadRequestError):
            logger.error(f"Bad request error: {error}")
        elif isinstance(error, APIError):
            logger.error(f"API error: {error}")
        else:
            logger.error(f"Unexpected error: {error}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Claude API connection with minimal request.
        
        Works with all authentication modes:
        - Direct API keys (production)
        - Clawdbot OAuth tokens (development)
        - Claude CLI OAuth tokens (development)
        
        Returns:
            Dict with 'success', 'auth_mode', 'model', and 'error' (if failed)
        """
        mode_label = self.AUTH_MODE_LABELS.get(self.auth_mode, self.auth_mode)
        
        result = {
            "success": False,
            "auth_mode": self.auth_mode,
            "auth_mode_label": mode_label,
            "model": self.config.model,
            "error": None
        }
        
        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            result["success"] = True
            result["model"] = response.model
            
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"✅ CONNECTION TEST: SUCCESS")
            logger.info(f"   Auth Mode: {mode_label}")
            logger.info(f"   Model: {response.model}")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return result
            
        except AuthenticationError as e:
            result["error"] = str(e)
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.error(f"❌ CONNECTION TEST: AUTHENTICATION FAILED")
            logger.error(f"   Auth Mode: {mode_label}")
            logger.error(f"   Error: {e}")
            
            # Mode-specific recovery suggestions
            if self.auth_mode == "clawdbot":
                logger.error(f"   Recovery: OAuth token may be expired.")
                logger.error(f"             Try refreshing Clawdbot authentication.")
            elif self.auth_mode == "claude_cli":
                logger.error(f"   Recovery: Run 'claude auth login' to refresh token.")
            elif self.auth_mode == "direct":
                logger.error(f"   Recovery: Verify your API key at console.anthropic.com")
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return result
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ CONNECTION TEST: FAILED")
            logger.error(f"   Auth Mode: {mode_label}")
            logger.error(f"   Error: {e}")
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client usage statistics including authentication mode"""
        return {
            'request_count': self._request_count,
            'last_request_time': self._last_request_time,
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'auth_mode': self.auth_mode,
            'auth_mode_label': self.AUTH_MODE_LABELS.get(self.auth_mode, self.auth_mode),
            'is_production': self.auth_mode == "direct",
            'is_development': self.auth_mode in ("clawdbot", "claude_cli")
        }

class ClaudeAPIError(Exception):
    """Custom exception for Claude API errors"""
    pass