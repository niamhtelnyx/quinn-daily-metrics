"""
Tests for Context Overflow Protection System

Tests the bulletproof safeguards against OpenAI "Context overflow: prompt too large" errors.
Validates:
- Pre-flight token counting
- Smart transcript truncation
- Fallback mechanisms
- Error recovery
- Monitoring metrics
"""

import asyncio
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

# Setup logging for tests
logging.basicConfig(level=logging.INFO)

# Import modules to test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_counter import (
    TokenCounter, TokenCount, TokenLimits,
    get_token_counter, count_tokens, check_fits_context,
    recommend_model, MODEL_LIMITS
)
from services.transcript_processor import (
    TranscriptProcessor, TruncationStrategy, ProcessingResult,
    process_transcript_for_model
)


class TestTokenCounter:
    """Tests for token counting utility"""
    
    def test_basic_token_counting(self):
        """Test basic token counting works"""
        counter = TokenCounter('gpt-4o')
        result = counter.count_tokens("Hello, this is a test.")
        
        assert result.total_tokens > 0
        assert result.method in ['tiktoken', 'estimation']
        assert result.confidence > 0
        
    def test_empty_text(self):
        """Test handling of empty text"""
        counter = TokenCounter('gpt-4o')
        result = counter.count_tokens("")
        
        assert result.total_tokens == 0
        assert result.method == 'empty'
    
    def test_large_text_counting(self):
        """Test counting tokens for large text"""
        counter = TokenCounter('gpt-4o')
        large_text = "This is a test sentence. " * 10000  # ~50k chars
        result = counter.count_tokens(large_text)
        
        assert result.total_tokens > 1000
        print(f"Large text ({len(large_text):,} chars) = {result.total_tokens:,} tokens")
    
    def test_model_limits_retrieval(self):
        """Test retrieving model limits"""
        counter = TokenCounter('gpt-4o')
        limits = counter.get_model_limits()
        
        assert limits.context_limit == 128000
        assert limits.effective_input_limit < limits.context_limit
        
    def test_limits_check_within_bounds(self):
        """Test check_within_limits for small content"""
        counter = TokenCounter('gpt-4o')
        small_text = "This is a small transcript."
        system_prompt = "You are a helpful assistant."
        
        fits, details = counter.check_within_limits(small_text, system_prompt)
        
        assert fits is True
        assert details['headroom'] > 0
        assert details['is_within_limits'] is True
    
    def test_limits_check_exceeds_bounds(self):
        """Test check_within_limits for large content"""
        counter = TokenCounter('gpt-4o')
        # Create content that would exceed 128k tokens (~500k chars)
        huge_text = "This is a test sentence with many words. " * 50000
        system_prompt = "You are a helpful assistant."
        
        fits, details = counter.check_within_limits(huge_text, system_prompt)
        
        assert fits is False
        assert details['overflow_amount'] > 0
        print(f"Overflow amount: {details['overflow_amount']:,} tokens")
    
    def test_max_transcript_tokens_calculation(self):
        """Test calculating max available transcript tokens"""
        counter = TokenCounter('gpt-4o')
        system_prompt = "You are a sales call analyst. Analyze the following transcript."
        
        max_tokens = counter.calculate_max_transcript_tokens(system_prompt, output_tokens=4096)
        
        assert max_tokens > 100000  # Should have most of 128k available
        assert max_tokens < 128000  # But not all
        print(f"Max transcript tokens: {max_tokens:,}")


class TestTranscriptProcessor:
    """Tests for smart transcript truncation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = TranscriptProcessor('gpt-4o')
        
        # Create sample transcripts of various sizes
        self.small_transcript = self._create_sample_transcript(50)  # 50 lines
        self.medium_transcript = self._create_sample_transcript(500)  # 500 lines
        self.large_transcript = self._create_sample_transcript(5000)  # 5000 lines
        self.huge_transcript = self._create_sample_transcript(20000)  # 20000 lines
        
        self.system_prompt = "You are analyzing a sales call transcript. Provide detailed insights."
    
    def _create_sample_transcript(self, num_lines: int) -> str:
        """Create a sample transcript with speaker changes and keywords"""
        lines = []
        speakers = ["Sales Rep", "Customer"]
        keywords = ["budget", "timeline", "decision", "Quinn", "integration"]
        
        for i in range(num_lines):
            speaker = speakers[i % 2]
            line = f"{speaker}: This is line {i} of the transcript discussion."
            
            # Add keywords occasionally
            if i % 50 == 0:
                kw = keywords[i % len(keywords)]
                line += f" Let's discuss the {kw}."
            
            # Add questions occasionally
            if i % 30 == 0:
                line += " What do you think?"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def test_no_truncation_needed(self):
        """Test that small transcripts aren't truncated"""
        result = self.processor.process_transcript(
            self.small_transcript,
            self.system_prompt
        )
        
        assert result.was_truncated is False
        assert result.strategy_used == TruncationStrategy.NONE
        assert result.truncation_ratio == 1.0
    
    def test_smart_section_truncation(self):
        """Test smart section truncation strategy"""
        result = self.processor.process_transcript(
            self.huge_transcript,
            self.system_prompt,
            strategy=TruncationStrategy.SMART_SECTIONS
        )
        
        assert result.was_truncated is True
        assert result.strategy_used == TruncationStrategy.SMART_SECTIONS
        assert result.truncation_ratio < 1.0
        assert result.processed_tokens < result.original_tokens
        
        # Verify structure markers are present
        assert "[..." in result.processed_text or "TRUNCATED" in result.processed_text
        
        print(f"Truncation ratio: {result.truncation_ratio:.2%}")
        print(f"Original: {result.original_tokens:,} tokens")
        print(f"Processed: {result.processed_tokens:,} tokens")
    
    def test_speaker_aware_truncation(self):
        """Test speaker-aware truncation strategy"""
        result = self.processor.process_transcript(
            self.huge_transcript,
            self.system_prompt,
            strategy=TruncationStrategy.SPEAKER_AWARE
        )
        
        assert result.was_truncated is True
        assert result.strategy_used == TruncationStrategy.SPEAKER_AWARE
        
        # Check that speaker transitions are preserved
        assert "Sales Rep:" in result.processed_text
        assert "Customer:" in result.processed_text
    
    def test_keyword_preserve_truncation(self):
        """Test keyword-preserving truncation"""
        result = self.processor.process_transcript(
            self.huge_transcript,
            self.system_prompt,
            strategy=TruncationStrategy.KEYWORD_PRESERVE
        )
        
        assert result.was_truncated is True
        assert result.strategy_used == TruncationStrategy.KEYWORD_PRESERVE
        
        # Keywords should be preserved
        text_lower = result.processed_text.lower()
        keywords_found = sum(1 for kw in ['budget', 'timeline', 'decision', 'quinn'] 
                           if kw in text_lower)
        assert keywords_found > 0, "Expected keywords to be preserved"
    
    def test_simple_truncation(self):
        """Test simple truncation fallback"""
        result = self.processor.process_transcript(
            self.huge_transcript,
            self.system_prompt,
            strategy=TruncationStrategy.SIMPLE
        )
        
        assert result.was_truncated is True
        # Simple truncation should still produce valid output
        assert len(result.processed_text) > 0
    
    def test_convenience_function(self):
        """Test the convenience function"""
        result = process_transcript_for_model(
            self.large_transcript,
            self.system_prompt,
            model='gpt-4o'
        )
        
        assert isinstance(result, ProcessingResult)


class TestModelRecommendation:
    """Tests for model recommendation based on content size"""
    
    def test_small_content_uses_preferred(self):
        """Small content should use preferred model"""
        transcript = "This is a small transcript."
        system_prompt = "Analyze this."
        
        model, reason = recommend_model(transcript, system_prompt, 'gpt-4o')
        
        assert model == 'gpt-4o'
        assert 'fits' in reason.lower()
    
    def test_large_content_recommends_claude(self):
        """Very large content should recommend Claude"""
        # Create content that exceeds GPT-4o limits but fits Claude
        huge_transcript = "Test content. " * 100000  # ~400k chars
        system_prompt = "Analyze this."
        
        model, reason = recommend_model(huge_transcript, system_prompt, 'gpt-4o')
        
        # Should either recommend Claude or note truncation is needed
        assert 'claude' in reason.lower() or 'truncation' in reason.lower()


class TestIntegrationFlow:
    """Integration tests for the complete flow"""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI API response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis result"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-4o"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 500
        return mock_response
    
    @pytest.mark.asyncio
    async def test_preflight_prevents_overflow(self):
        """Test that pre-flight check prevents overflow errors"""
        from services.openai_client import OpenAIClient
        from config.settings import OpenAIConfig
        
        # Create config with mock API key
        config = OpenAIConfig(api_key="test-key", model="gpt-4o")
        
        with patch('services.openai_client.AsyncOpenAI'):
            client = OpenAIClient(config)
            
            # Check pre-flight detection
            huge_transcript = "Test " * 200000  # Way over limit
            fits, details = client._preflight_token_check(
                huge_transcript, "System prompt"
            )
            
            assert fits is False
            assert details['overflow_amount'] > 0
    
    @pytest.mark.asyncio
    async def test_automatic_truncation_flow(self, mock_openai_response):
        """Test that automatic truncation happens when needed"""
        from services.openai_client import OpenAIClient
        from config.settings import OpenAIConfig
        
        config = OpenAIConfig(api_key="test-key", model="gpt-4o")
        
        with patch('services.openai_client.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_openai.return_value = mock_client
            
            client = OpenAIClient(config)
            
            # Create large transcript that needs truncation
            large_transcript = "Sales Rep: Hello. Customer: Hi. " * 50000
            
            result = await client.analyze_call_transcript(
                large_transcript,
                "You are a sales analyst."
            )
            
            # Should have preprocessing info
            assert result.preprocessing_info is not None
            assert result.preprocessing_info.get('was_truncated', False) or \
                   result.preprocessing_info.get('original_transcript_tokens', 0) <= \
                   result.preprocessing_info.get('processed_transcript_tokens', 0)


class TestErrorHandling:
    """Tests for error handling and recovery"""
    
    def test_context_overflow_categorization(self):
        """Test that context overflow errors are properly categorized"""
        from services.error_handler import LLMErrorHandler, ErrorCategory
        from services.openai_client import ContextOverflowError
        from models.processing_queue import ProcessingContext, Priority
        
        handler = LLMErrorHandler()
        
        # Test ContextOverflowError
        error = ContextOverflowError("Context overflow", {'tokens': 150000})
        category = handler._categorize_error(error)
        assert category == ErrorCategory.CONTEXT_OVERFLOW
        
        # Test error message detection
        error = Exception("maximum context length exceeded")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.CONTEXT_OVERFLOW
        
        # Test prompt too large
        error = Exception("prompt too large for context window")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.CONTEXT_OVERFLOW
    
    def test_recovery_strategy_for_overflow(self):
        """Test that correct recovery strategy is assigned"""
        from services.error_handler import LLMErrorHandler, ErrorCategory
        
        handler = LLMErrorHandler()
        
        strategy = handler._get_recovery_strategy(ErrorCategory.CONTEXT_OVERFLOW)
        
        assert strategy.should_retry is True
        assert strategy.max_retries >= 2
        assert 'truncation' in strategy.fallback_action.lower() or \
               'claude' in strategy.fallback_action.lower()


class TestMetricsAndMonitoring:
    """Tests for usage metrics and monitoring"""
    
    def test_token_usage_metrics_tracking(self):
        """Test that token usage is properly tracked"""
        from services.openai_client import TokenUsageMetrics
        
        metrics = TokenUsageMetrics(
            input_tokens=1000,
            output_tokens=500,
            original_transcript_tokens=50000,
            processed_transcript_tokens=30000,
            was_truncated=True,
            truncation_strategy="smart_sections",
            truncation_ratio=0.6
        )
        
        data = metrics.to_dict()
        
        assert data['input_tokens'] == 1000
        assert data['was_truncated'] is True
        assert data['truncation_ratio'] == 0.6
    
    def test_client_stats_collection(self):
        """Test that client stats are properly collected"""
        from services.openai_client import OpenAIClient
        from config.settings import OpenAIConfig
        
        config = OpenAIConfig(api_key="test-key", model="gpt-4o")
        
        with patch('services.openai_client.AsyncOpenAI'):
            client = OpenAIClient(config)
            stats = client.get_stats()
            
            assert 'model' in stats
            assert 'context_limit' in stats
            assert 'overflow_prevented_count' in stats


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
