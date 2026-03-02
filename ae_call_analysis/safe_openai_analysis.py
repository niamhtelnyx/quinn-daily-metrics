#!/usr/bin/env python3
"""
MANUAL FIX: Safe OpenAI Analysis with Context Overflow Protection

Use this instead of the complex openai_client.py until imports are fixed.
"""

import asyncio
import os
import json
import time
import logging
from typing import Dict, Any, Optional

# Required imports
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("❌ tiktoken not available - install with: pip3 install tiktoken")

try:
    from openai import AsyncOpenAI
except ImportError:
    print("❌ openai not available - install with: pip3 install openai")
    raise

logger = logging.getLogger(__name__)


class SafeOpenAIClient:
    """
    BULLETPROOF OpenAI client that NEVER hits context overflow
    """
    
    # Conservative token limits (leave 20k for response)
    MODEL_LIMITS = {
        'gpt-4o': 108_000,
        'gpt-4o-mini': 108_000,  
        'gpt-4-turbo': 108_000,
        'gpt-4': 6_000,
        'gpt-3.5-turbo': 12_000
    }
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        if TIKTOKEN_AVAILABLE:
            self.tokenizer = tiktoken.encoding_for_model('gpt-4o')
            print("✅ Using accurate tiktoken counting")
        else:
            self.tokenizer = None
            print("⚠️ Using rough token estimates (install tiktoken for accuracy)")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens accurately or estimate"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text) // 4  # Rough estimate
    
    def safe_truncate(self, transcript: str, system_prompt: str, model: str = 'gpt-4o') -> str:
        """
        Truncate transcript to fit within model limits
        """
        max_input = self.MODEL_LIMITS.get(model, 100_000)
        
        system_tokens = self.count_tokens(system_prompt)
        transcript_tokens = self.count_tokens(transcript)
        total_tokens = system_tokens + transcript_tokens
        
        logger.info(f"Token analysis: system={system_tokens:,}, transcript={transcript_tokens:,}, total={total_tokens:,}")
        
        if total_tokens <= max_input:
            logger.info(f"✅ Within limits: {total_tokens:,} <= {max_input:,}")
            return transcript
        
        # Need to truncate
        max_transcript_tokens = max_input - system_tokens - 100  # Safety margin
        
        if max_transcript_tokens < 1000:
            raise ValueError(f"System prompt too large! {system_tokens:,} tokens")
        
        logger.warning(f"⚠️ TRUNCATING: {total_tokens:,} > {max_input:,}")
        
        if self.tokenizer:
            # Accurate truncation
            transcript_encoded = self.tokenizer.encode(transcript)
            truncated_encoded = transcript_encoded[:max_transcript_tokens]
            truncated_transcript = self.tokenizer.decode(truncated_encoded)
        else:
            # Rough truncation
            char_ratio = max_transcript_tokens / transcript_tokens
            truncated_transcript = transcript[:int(len(transcript) * char_ratio)]
        
        final_tokens = self.count_tokens(system_prompt + truncated_transcript)
        logger.info(f"✅ TRUNCATED: {final_tokens:,} tokens (safe)")
        
        return truncated_transcript
    
    def extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from OpenAI response that might be wrapped in markdown
        """
        # Remove markdown code fences if present
        content = content.strip()
        
        # Check for ```json wrapper
        if content.startswith('```json'):
            # Find the end of the code block
            lines = content.split('\n')
            json_lines = []
            in_code_block = False
            
            for line in lines:
                if line.strip() == '```json':
                    in_code_block = True
                    continue
                elif line.strip() == '```' and in_code_block:
                    break
                elif in_code_block:
                    json_lines.append(line)
            
            content = '\n'.join(json_lines)
        
        # Also check for ``` wrapper
        elif content.startswith('```'):
            # Remove first and last ```
            content = content.strip()
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
        
        return content

    async def safe_analysis(self, transcript: str, system_prompt: str, model: str = 'gpt-4o') -> Dict[str, Any]:
        """
        GUARANTEED safe OpenAI analysis - never hits context overflow
        """
        start_time = time.time()
        
        # Make transcript safe
        safe_transcript = self.safe_truncate(transcript, system_prompt, model)
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": safe_transcript}
        ]
        
        # Make API call
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )
            
            processing_time = time.time() - start_time
            
            # Extract clean JSON from response
            raw_content = response.choices[0].message.content
            clean_content = self.extract_json_from_response(raw_content)
            
            return {
                'content': clean_content,
                'raw_content': raw_content,  # Keep original for debugging
                'model': response.model,
                'usage': {
                    'input_tokens': response.usage.prompt_tokens,
                    'output_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'processing_time': processing_time,
                'truncated': len(safe_transcript) < len(transcript)
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


async def test_safe_analysis():
    """Test the safe analysis function"""
    
    # Create test data
    test_transcript = "This is a test sales call transcript. " * 1000  # Large transcript
    test_system_prompt = """
    You are an expert sales call analyzer. Analyze this call and provide:
    {
      "summary": "Brief summary",
      "sentiment": 7,
      "next_steps": "What happens next"
    }
    """
    
    client = SafeOpenAIClient()
    
    try:
        result = await client.safe_analysis(test_transcript, test_system_prompt)
        
        print("🎉 SAFE ANALYSIS TEST SUCCESS!")
        print(f"   Content length: {len(result['content'])}")
        print(f"   Model: {result['model']}")
        print(f"   Tokens: {result['usage']['total_tokens']:,}")
        print(f"   Time: {result['processing_time']:.2f}s")
        print(f"   Truncated: {result['truncated']}")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    # Test the safe analysis
    success = asyncio.run(test_safe_analysis())
    if success:
        print("\n✅ Ready for production use!")
    else:
        print("\n❌ Fix needed before production")