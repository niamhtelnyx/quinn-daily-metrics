#!/usr/bin/env python3
"""Test the JSON extraction fix"""

import asyncio
import json
from safe_openai_analysis import SafeOpenAIClient

async def test_json_fix():
    client = SafeOpenAIClient()
    
    # Test the JSON extraction function directly
    markdown_wrapped = '''```json
{
  "simple_summary": {
    "core_talking_points": ["Cost issues", "Scalability needs"],
    "analysis_confidence": 8
  }
}
```'''
    
    print('🔍 Testing JSON extraction...')
    
    extracted = client.extract_json_from_response(markdown_wrapped)
    print(f'Original length: {len(markdown_wrapped)}')
    print(f'Extracted length: {len(extracted)}')
    
    print(f'\nExtracted content:')
    print('='*50)
    print(extracted)
    print('='*50)
    
    # Test JSON parsing
    try:
        parsed = json.loads(extracted)
        print(f'\n✅ JSON PARSING: SUCCESS!')
        print(f'   Keys: {list(parsed.keys())}')
    except json.JSONDecodeError as e:
        print(f'\n❌ JSON PARSING: FAILED - {e}')
        
    # Now test with actual OpenAI call
    print(f'\n🔍 Testing with real OpenAI call...')
    
    system_prompt = '''Return this exact JSON:
{
  "simple_summary": {
    "core_talking_points": ["Test point 1", "Test point 2"],
    "analysis_confidence": 9
  }
}'''
    
    result = await client.safe_analysis('Test transcript', system_prompt)
    
    print(f'Response length: {len(result["content"])}')
    
    try:
        parsed = json.loads(result['content'])
        print(f'✅ REAL API CALL: JSON parsing SUCCESS!')
        print(f'   Confidence: {parsed.get("simple_summary", {}).get("analysis_confidence", "Missing")}')
    except json.JSONDecodeError as e:
        print(f'❌ REAL API CALL: JSON parsing failed - {e}')
        print(f'Raw response: {result["raw_content"][:200]}...')

if __name__ == "__main__":
    asyncio.run(test_json_fix())