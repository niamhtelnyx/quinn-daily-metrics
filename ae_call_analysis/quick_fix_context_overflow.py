#!/usr/bin/env python3
"""
QUICK FIX: Prevent OpenAI Context Overflow
Add this check before every OpenAI API call
"""
import sys

try:
    import tiktoken
    print("✅ tiktoken available")
except ImportError:
    print("❌ Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tiktoken"])
    import tiktoken
    print("✅ tiktoken installed")

def safe_openai_analysis(transcript_text, system_prompt, model="gpt-4o"):
    """
    Bulletproof OpenAI call that never overflows context.
    """
    # Get tokenizer for model
    enc = tiktoken.encoding_for_model(model)
    
    # Count tokens
    system_tokens = len(enc.encode(system_prompt))
    transcript_tokens = len(enc.encode(transcript_text))
    total_input_tokens = system_tokens + transcript_tokens
    
    # Model limits (leave room for response)
    MODEL_LIMITS = {
        'gpt-4o': 108_000,        # 128k - 20k for response
        'gpt-4-turbo': 108_000,   # 128k - 20k for response  
        'gpt-3.5-turbo': 12_000   # 16k - 4k for response
    }
    
    max_input = MODEL_LIMITS.get(model, 100_000)
    
    print(f"🔍 Token Analysis:")
    print(f"   System prompt: {system_tokens:,} tokens")
    print(f"   Transcript: {transcript_tokens:,} tokens") 
    print(f"   Total input: {total_input_tokens:,} tokens")
    print(f"   Model limit: {max_input:,} tokens")
    
    # Check if within limits
    if total_input_tokens <= max_input:
        print(f"✅ SAFE: {total_input_tokens:,} <= {max_input:,}")
        return transcript_text  # Return as-is
    
    # TRUNCATE if needed
    print(f"⚠️ TRUNCATING: {total_input_tokens:,} > {max_input:,}")
    
    # Calculate how much transcript we can keep
    max_transcript_tokens = max_input - system_tokens - 100  # Safety margin
    
    if max_transcript_tokens < 1000:
        raise ValueError(f"System prompt too large! Uses {system_tokens:,} tokens, only {max_input:,} available")
    
    # Truncate transcript to fit
    transcript_encoded = enc.encode(transcript_text)
    truncated_encoded = transcript_encoded[:max_transcript_tokens]
    truncated_text = enc.decode(truncated_encoded)
    
    # Verify final size
    final_tokens = len(enc.encode(system_prompt + truncated_text))
    print(f"✅ TRUNCATED: {final_tokens:,} tokens (removed {transcript_tokens - len(truncated_encoded):,} tokens)")
    
    return truncated_text


# Test the function
if __name__ == "__main__":
    # Test with oversized content
    test_transcript = "This is a test transcript. " * 50000  # Very large
    test_system_prompt = "Analyze this call transcript and provide insights."
    
    try:
        result = safe_openai_analysis(test_transcript, test_system_prompt)
        print(f"\n✅ SUCCESS: Processed safely, result length: {len(result):,} chars")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")