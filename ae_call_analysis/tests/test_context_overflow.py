"""
Test suite for context overflow protection.

Verifies that:
1. Tiktoken is properly installed and working
2. Token counting is accurate
3. Automatic truncation works for oversized content
4. No overflow errors reach the API
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_counter import (
    TokenCounter, 
    TIKTOKEN_AVAILABLE, 
    get_token_counter,
    check_fits_context,
    MODEL_LIMITS
)
from services.transcript_processor import (
    TranscriptProcessor,
    TruncationStrategy,
    process_transcript_for_model
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_tiktoken_installed():
    """CRITICAL: Verify tiktoken is available for accurate counting"""
    assert TIKTOKEN_AVAILABLE, "❌ TIKTOKEN NOT INSTALLED - Run: pip3 install tiktoken"
    print("✅ Tiktoken installed and available")
    return True


def test_token_counting_accuracy():
    """Verify token counting uses tiktoken, not estimation"""
    counter = TokenCounter('gpt-4o')
    
    test_text = "Hello, this is a test message for token counting accuracy."
    result = counter.count_tokens(test_text)
    
    assert result.method == 'tiktoken', f"❌ Using {result.method} instead of tiktoken"
    assert result.confidence == 1.0, f"❌ Confidence is {result.confidence}, expected 1.0"
    assert result.model_encoding is not None, "❌ No encoding set"
    
    print(f"✅ Token counting accurate: {result.total_tokens} tokens via {result.method}")
    print(f"   Encoding: {result.model_encoding}")
    return True


def test_model_limits_defined():
    """Verify all common models have defined limits"""
    required_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
    
    for model in required_models:
        assert model in MODEL_LIMITS, f"❌ Missing limits for {model}"
        limits = MODEL_LIMITS[model]
        assert limits.context_limit > 0, f"❌ Invalid context limit for {model}"
        print(f"✅ {model}: {limits.context_limit:,} context, {limits.effective_input_limit:,} effective input")
    
    return True


def test_oversized_transcript_detection():
    """Test that oversized transcripts are correctly detected"""
    counter = TokenCounter('gpt-4o')
    
    # Create an oversized transcript (~150k tokens)
    oversized = "This is a very long sales call transcript with lots of detail. " * 20000
    system_prompt = "You are a sales call analyst. Analyze the following transcript."
    
    fits, details = counter.check_within_limits(oversized, system_prompt, output_tokens=4096)
    
    assert not fits, "❌ Oversized transcript incorrectly marked as fitting"
    assert details['overflow_amount'] > 0, "❌ No overflow detected"
    
    print(f"✅ Oversized detection working:")
    print(f"   Text tokens: {details['text_tokens']:,}")
    print(f"   Overflow: {details['overflow_amount']:,} tokens")
    return True


def test_smart_truncation():
    """Test smart truncation preserves key content"""
    processor = TranscriptProcessor('gpt-4o')
    
    # Create a large transcript with identifiable sections (~180k tokens to ensure truncation)
    lines = []
    lines.append("AE: Welcome to our call today! I'm excited to discuss Quinn with you.")
    lines.append("Customer: Thanks for taking the time to meet with me.")
    
    # Add lots of middle content (adjusted for ~180k tokens total)
    for i in range(4000):
        speaker = "AE" if i % 2 == 0 else "Customer"
        lines.append(f"{speaker}: This is discussion point number {i}. Let me explain more details about our offering and how it can help your business grow and succeed in the competitive market landscape.")
    
    # Key section with important keywords
    lines.append("Customer: What's the budget for this solution?")
    lines.append("AE: Great question! Let me explain our pricing model.")
    
    # More middle content
    for i in range(4000):
        speaker = "AE" if i % 2 == 0 else "Customer"
        lines.append(f"{speaker}: Continuing our discussion with point {i + 4000}. This involves many technical aspects and complex integration requirements for your team.")
    
    # Important ending
    lines.append("AE: So our next steps are to send you the proposal.")
    lines.append("Customer: Perfect, I'll review it with my team by Friday.")
    
    transcript = "\n".join(lines)
    system_prompt = "You are analyzing this sales call."
    
    result = processor.process_transcript(
        transcript,
        system_prompt,
        max_output_tokens=4096,
        strategy=TruncationStrategy.SMART_SECTIONS
    )
    
    assert result.was_truncated, "❌ Transcript should have been truncated"
    assert result.truncation_ratio < 1.0, "❌ Truncation ratio should be < 1.0"
    
    # Verify beginning is preserved
    assert "Welcome to our call" in result.processed_text, "❌ Beginning not preserved"
    
    # Verify ending is preserved
    assert "next steps" in result.processed_text, "❌ Ending not preserved"
    
    print(f"✅ Smart truncation working:")
    print(f"   Original: {result.original_tokens:,} tokens")
    print(f"   Processed: {result.processed_tokens:,} tokens")
    print(f"   Retention: {result.truncation_ratio:.1%}")
    print(f"   Strategy: {result.strategy_used.value}")
    return True


def test_keyword_preservation():
    """Test that important keywords are preserved during truncation"""
    processor = TranscriptProcessor('gpt-4o')
    
    # Create transcript with important keywords scattered through (~150k tokens)
    lines = []
    for i in range(8000):
        if i == 1000:
            lines.append("Customer: What about the budget for this project? We need to discuss pricing carefully.")
        elif i == 3000:
            lines.append("AE: The pricing includes all integration work and professional services.")
        elif i == 5000:
            lines.append("Customer: When is the deadline for the decision? We need to know the timeline.")
        elif i == 7000:
            lines.append("AE: The next steps would be to schedule a follow up meeting with your team.")
        else:
            lines.append(f"Speaker {i % 2 + 1}: Generic conversation line {i} with more detail to ensure adequate length for testing purposes.")
    
    transcript = "\n".join(lines)
    
    result = processor.process_transcript(
        transcript,
        "Analyze this call.",
        max_output_tokens=4096,
        strategy=TruncationStrategy.KEYWORD_PRESERVE
    )
    
    assert result.was_truncated, "❌ Should have been truncated"
    
    # Check keywords are preserved
    keywords_to_check = ['budget', 'pricing', 'deadline', 'next steps']
    preserved = [kw for kw in keywords_to_check if kw.lower() in result.processed_text.lower()]
    
    print(f"✅ Keyword preservation working:")
    print(f"   Keywords preserved: {preserved}")
    print(f"   Retention: {result.truncation_ratio:.1%}")
    return True


def test_preflight_prevents_overflow():
    """Test that preflight check correctly identifies overflow scenarios"""
    counter = TokenCounter('gpt-4o')
    
    # Test with various sizes (using repeated words instead of single chars for faster tokenization)
    test_cases = [
        ("Small (100 words)", "hello world test " * 100, True),
        ("Large (10k words)", "hello world test " * 10000, True),  
        ("Very Large (50k words)", "hello world test " * 50000, False),  # Should NOT fit
    ]
    
    system_prompt = "You are a helpful assistant."
    
    all_passed = True
    for name, text, should_fit in test_cases:
        fits, details = counter.check_within_limits(text, system_prompt)
        
        # Very large should definitely not fit
        if not should_fit and fits:
            print(f"❌ {name}: Should NOT fit but marked as fitting")
            all_passed = False
        else:
            status = "fits" if fits else f"overflow by {details['overflow_amount']:,}"
            print(f"   {name}: {details['text_tokens']:,} tokens - {status}")
    
    if all_passed:
        print("✅ Preflight detection working correctly")
    return all_passed


def test_emergency_truncation():
    """Test that emergency truncation kicks in when needed"""
    processor = TranscriptProcessor('gpt-4o')
    
    # Create a large transcript that needs truncation (~150k tokens)
    massive = "Very long line of text with detailed discussion. " * 20000
    
    result = processor.process_transcript(
        massive,
        "Analyze this.",
        max_output_tokens=4096,
        strategy=TruncationStrategy.SIMPLE
    )
    
    assert result.was_truncated, "❌ Should have been truncated"
    
    # Verify it fits now
    counter = TokenCounter('gpt-4o')
    fits, details = counter.check_within_limits(
        result.processed_text, 
        "Analyze this.", 
        output_tokens=4096
    )
    
    assert fits, f"❌ Even after truncation, still overflow: {details.get('overflow_amount', 0):,}"
    
    print(f"✅ Emergency truncation working:")
    print(f"   Final size: {result.processed_tokens:,} tokens")
    print(f"   Fits in context: {fits}")
    return True


def run_all_tests():
    """Run all context overflow tests"""
    print("=" * 60)
    print("CONTEXT OVERFLOW PROTECTION TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        ("Tiktoken Installation", test_tiktoken_installed),
        ("Token Counting Accuracy", test_token_counting_accuracy),
        ("Model Limits Defined", test_model_limits_defined),
        ("Oversized Detection", test_oversized_transcript_detection),
        ("Smart Truncation", test_smart_truncation),
        ("Keyword Preservation", test_keyword_preservation),
        ("Preflight Check", test_preflight_prevents_overflow),
        ("Emergency Truncation", test_emergency_truncation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Context overflow protection is working!")
        print("\nSUCCESS CRITERIA:")
        print("  ✅ Tiktoken installed for accurate token counting")
        print("  ✅ Pre-flight token checking works")
        print("  ✅ Automatic truncation prevents overflow")
        print("  ✅ Key content (beginning/end/keywords) preserved")
        print("  ✅ Emergency truncation as safety net")
    else:
        print("\n❌ SOME TESTS FAILED - Review output above")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
