"""
Integration tests for Claude API client
Tests basic connectivity, authentication, and error handling scenarios
"""

import pytest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

from ..config.settings import ClaudeConfig
from ..services.claude_client import ClaudeClient, ClaudeAPIError

class TestClaudeIntegration:
    """Test suite for Claude API integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = ClaudeConfig(
            api_key="test_key",
            model="claude-3-sonnet-20241022",
            max_tokens=1000,
            temperature=0.1,
            timeout=30.0,
            max_retries=2
        )
    
    def test_client_initialization_success(self):
        """Test successful Claude client initialization"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            assert client.config == self.config
            assert client._request_count == 0
    
    def test_client_initialization_no_api_key(self):
        """Test client initialization fails without API key"""
        config = ClaudeConfig(api_key="")
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            with pytest.raises(ValueError, match="Claude API key is required"):
                ClaudeClient(config)
    
    def test_client_initialization_no_anthropic_package(self):
        """Test graceful handling when anthropic package not available"""
        config = ClaudeConfig(api_key="test_key")
        
        # Mock anthropic as None to simulate missing package
        with patch('ae_call_analysis.services.claude_client.anthropic', None):
            with pytest.raises(ImportError, match="anthropic package is required"):
                ClaudeClient(config)
    
    @pytest.mark.asyncio
    async def test_analyze_call_transcript_success(self):
        """Test successful call transcript analysis"""
        # Mock successful Claude API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"analysis": "test result"}')]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
        mock_response.model = "claude-3-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            client = ClaudeClient(self.config)
            
            result = await client.analyze_call_transcript(
                transcript="Test call transcript",
                system_prompt="Analyze this call"
            )
            
            assert result.content == '{"analysis": "test result"}'
            assert result.usage['input_tokens'] == 100
            assert result.usage['output_tokens'] == 50
            assert result.model == "claude-3-sonnet-20241022"
            assert result.finish_reason == "end_turn"
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_analyze_empty_transcript_fails(self):
        """Test analysis fails with empty transcript"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            
            with pytest.raises(ValueError, match="Transcript cannot be empty"):
                await client.analyze_call_transcript("", "System prompt")
    
    @pytest.mark.asyncio
    async def test_analyze_empty_system_prompt_fails(self):
        """Test analysis fails with empty system prompt"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            
            with pytest.raises(ValueError, match="System prompt cannot be empty"):
                await client.analyze_call_transcript("Test transcript", "")
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry_logic(self):
        """Test retry logic handles rate limit errors"""
        from ae_call_analysis.services.claude_client import RateLimitError
        
        # Mock rate limit error followed by success
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit exceeded"),
                MagicMock(
                    content=[MagicMock(text='Success')],
                    usage=MagicMock(input_tokens=10, output_tokens=5),
                    model="claude-3-sonnet-20241022",
                    stop_reason="end_turn"
                )
            ]
        )
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            # Speed up test by reducing retry delay
            with patch('ae_call_analysis.services.claude_client.asyncio.sleep', new=AsyncMock()):
                client = ClaudeClient(self.config)
                
                result = await client.analyze_call_transcript(
                    transcript="Test transcript",
                    system_prompt="Test prompt"
                )
                
                assert result.content == 'Success'
                assert mock_client.messages.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_authentication_error_not_retried(self):
        """Test authentication errors are not retried"""
        from ae_call_analysis.services.claude_client import AuthenticationError
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=AuthenticationError("Invalid API key")
        )
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            client = ClaudeClient(self.config)
            
            with pytest.raises(ClaudeAPIError, match="Authentication failed"):
                await client.analyze_call_transcript(
                    transcript="Test transcript", 
                    system_prompt="Test prompt"
                )
            
            # Should only be called once (no retries)
            assert mock_client.messages.create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test behavior when max retries are exhausted"""
        from ae_call_analysis.services.claude_client import APITimeoutError
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=APITimeoutError("Timeout")
        )
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            # Speed up test by reducing retry delay
            with patch('ae_call_analysis.services.claude_client.asyncio.sleep', new=AsyncMock()):
                client = ClaudeClient(self.config)
                
                with pytest.raises(ClaudeAPIError, match="API timeout after retries"):
                    await client.analyze_call_transcript(
                        transcript="Test transcript",
                        system_prompt="Test prompt"
                    )
                
                # Should be called max_retries + 1 times
                expected_calls = self.config.max_retries + 1
                assert mock_client.messages.create.call_count == expected_calls
    
    @pytest.mark.asyncio
    async def test_analyze_with_tools_success(self):
        """Test successful tool-based analysis"""
        # Mock tool use response
        mock_tool_block = MagicMock()
        mock_tool_block.type = 'tool_use'
        mock_tool_block.name = 'analyze_call'
        mock_tool_block.input = {'analysis': 'structured result'}
        
        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_response.usage = MagicMock(input_tokens=200, output_tokens=100)
        mock_response.model = "claude-3-sonnet-20241022"
        mock_response.stop_reason = "tool_use"
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            client = ClaudeClient(self.config)
            
            tools = [{
                "name": "analyze_call",
                "description": "Analyze call data",
                "input_schema": {"type": "object"}
            }]
            
            result = await client.analyze_with_tools(
                transcript="Test call transcript",
                tools=tools
            )
            
            # Should extract tool results as JSON
            assert "analyze_call" in result.content
            assert result.usage['input_tokens'] == 200
            assert result.usage['output_tokens'] == 100
    
    @pytest.mark.asyncio
    async def test_analyze_with_tools_no_tools_fails(self):
        """Test tool analysis fails without tools"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            
            with pytest.raises(ValueError, match="At least one tool must be provided"):
                await client.analyze_with_tools("Test transcript", [])
    
    @pytest.mark.asyncio
    async def test_connection_test_success(self):
        """Test successful connection test"""
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            client = ClaudeClient(self.config)
            
            result = await client.test_connection()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """Test connection test failure"""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic', return_value=mock_client):
            client = ClaudeClient(self.config)
            
            result = await client.test_connection()
            assert result is False
    
    def test_get_stats(self):
        """Test client statistics"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            
            stats = client.get_stats()
            
            assert stats['request_count'] == 0
            assert stats['model'] == self.config.model
            assert stats['max_tokens'] == self.config.max_tokens
            assert stats['temperature'] == self.config.temperature
    
    def test_backoff_calculation(self):
        """Test exponential backoff calculation"""
        with patch('ae_call_analysis.services.claude_client.AsyncAnthropic'):
            client = ClaudeClient(self.config)
            
            # Test backoff increases exponentially
            delay_0 = client._calculate_backoff(0)
            delay_1 = client._calculate_backoff(1)
            delay_2 = client._calculate_backoff(2)
            
            # Should increase but include jitter, so rough checks
            assert 0.5 <= delay_0 <= 2.0  # ~1s with jitter
            assert 1.0 <= delay_1 <= 4.0  # ~2s with jitter  
            assert 2.0 <= delay_2 <= 8.0  # ~4s with jitter
            
            # Test max delay cap
            delay_10 = client._calculate_backoff(10)
            assert delay_10 <= 60.0  # Should be capped at 60s

# Integration test for real Claude API (only if API key provided)
class TestClaudeRealAPI:
    """Real API tests - only run if CLAUDE_API_KEY environment variable is set"""
    
    @pytest.mark.skipif(
        not os.getenv('CLAUDE_API_KEY'),
        reason="CLAUDE_API_KEY environment variable not set"
    )
    @pytest.mark.asyncio
    async def test_real_claude_api_connection(self):
        """Test real Claude API connection (requires valid API key)"""
        config = ClaudeConfig(
            api_key=os.getenv('CLAUDE_API_KEY'),
            model="claude-3-sonnet-20241022",
            max_tokens=100
        )
        
        client = ClaudeClient(config)
        
        # Test basic connectivity
        success = await client.test_connection()
        assert success is True
    
    @pytest.mark.skipif(
        not os.getenv('CLAUDE_API_KEY'),
        reason="CLAUDE_API_KEY environment variable not set"
    )
    @pytest.mark.asyncio
    async def test_real_claude_api_analysis(self):
        """Test real Claude API analysis (requires valid API key)"""
        config = ClaudeConfig(
            api_key=os.getenv('CLAUDE_API_KEY'),
            model="claude-3-sonnet-20241022",
            max_tokens=500,
            temperature=0.1
        )
        
        client = ClaudeClient(config)
        
        # Test basic analysis
        result = await client.analyze_call_transcript(
            transcript="Hello, I'm interested in Telnyx voice services for my business. Can you tell me about pricing?",
            system_prompt="Analyze this brief sales conversation and identify key topics mentioned."
        )
        
        assert len(result.content) > 0
        assert result.usage['input_tokens'] > 0
        assert result.usage['output_tokens'] > 0
        assert result.processing_time > 0
        assert result.model == config.model