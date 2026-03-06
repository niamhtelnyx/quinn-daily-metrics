#!/usr/bin/env python3
"""
Response Length Validator - Prevent context overflow errors
Analyzes response length and suggests chunking strategies
"""

import sys
import re
import tiktoken

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in text using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # Fallback estimation: ~4 chars per token
        return len(text) // 4

def analyze_response_structure(text: str) -> dict:
    """Analyze response structure for chunking opportunities"""
    
    # Count sections and subsections
    h2_sections = len(re.findall(r'^## ', text, re.MULTILINE))
    h3_sections = len(re.findall(r'^### ', text, re.MULTILINE))
    code_blocks = len(re.findall(r'```', text)) // 2
    bullet_lists = len(re.findall(r'^\- ', text, re.MULTILINE))
    
    # Identify large sections
    sections = re.split(r'^## ', text, flags=re.MULTILINE)
    large_sections = []
    
    for i, section in enumerate(sections[1:], 1):  # Skip first split
        section_tokens = count_tokens(section)
        if section_tokens > 5000:  # Large section threshold
            large_sections.append({
                'index': i,
                'tokens': section_tokens,
                'preview': section[:100] + "..." if len(section) > 100 else section
            })
    
    return {
        'total_tokens': count_tokens(text),
        'h2_sections': h2_sections,
        'h3_sections': h3_sections,
        'code_blocks': code_blocks,
        'bullet_lists': bullet_lists,
        'large_sections': large_sections,
        'avg_section_tokens': count_tokens(text) // max(h2_sections, 1)
    }

def suggest_chunking_strategy(analysis: dict) -> list:
    """Suggest how to break down a large response"""
    suggestions = []
    
    total_tokens = analysis['total_tokens']
    
    # Context overflow prevention
    if total_tokens > 180000:  # 90% of 200K limit
        suggestions.append({
            'level': 'CRITICAL',
            'message': f'Response is {total_tokens:,} tokens - WILL CAUSE OVERFLOW',
            'action': 'Break into multiple responses immediately'
        })
    elif total_tokens > 150000:  # 75% of limit
        suggestions.append({
            'level': 'WARNING',
            'message': f'Response is {total_tokens:,} tokens - approaching limit',
            'action': 'Consider breaking into 2-3 responses'
        })
    
    # Section-based chunking
    if analysis['h2_sections'] > 5:
        suggestions.append({
            'level': 'INFO',
            'message': f'{analysis["h2_sections"]} main sections detected',
            'action': 'Consider grouping related sections into separate responses'
        })
    
    # Large section warnings
    if analysis['large_sections']:
        for section in analysis['large_sections']:
            suggestions.append({
                'level': 'WARNING',
                'message': f'Section {section["index"]} is {section["tokens"]:,} tokens',
                'action': f'Break down: {section["preview"]}'
            })
    
    # Code-heavy responses
    if analysis['code_blocks'] > 10:
        suggestions.append({
            'level': 'INFO',
            'message': f'{analysis["code_blocks"]} code blocks detected',
            'action': 'Consider separating implementation from documentation'
        })
    
    return suggestions

def create_chunking_plan(text: str, max_chunk_tokens: int = 45000) -> list:
    """Create a specific plan for breaking text into chunks"""
    
    sections = re.split(r'^## ', text, flags=re.MULTILINE)
    chunks = []
    current_chunk = sections[0]  # Intro/header
    current_tokens = count_tokens(current_chunk)
    
    for i, section in enumerate(sections[1:], 1):
        section_with_header = "## " + section
        section_tokens = count_tokens(section_with_header)
        
        # If adding this section would exceed limit, start new chunk
        if current_tokens + section_tokens > max_chunk_tokens:
            chunks.append({
                'chunk_num': len(chunks) + 1,
                'tokens': current_tokens,
                'preview': current_chunk[:200] + "..." if len(current_chunk) > 200 else current_chunk
            })
            current_chunk = section_with_header
            current_tokens = section_tokens
        else:
            current_chunk += section_with_header
            current_tokens += section_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            'chunk_num': len(chunks) + 1,
            'tokens': current_tokens,
            'preview': current_chunk[:200] + "..." if len(current_chunk) > 200 else current_chunk
        })
    
    return chunks

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 response-length-validator.py <text_file_or_text>")
        print("       echo 'text' | python3 response-length-validator.py -")
        sys.exit(1)
    
    # Get input text
    if sys.argv[1] == '-':
        text = sys.stdin.read()
    elif sys.argv[1].endswith(('.txt', '.md')):
        with open(sys.argv[1], 'r') as f:
            text = f.read()
    else:
        text = sys.argv[1]
    
    # Analyze the response
    analysis = analyze_response_structure(text)
    suggestions = suggest_chunking_strategy(analysis)
    
    # Print results
    print("📊 Response Length Analysis")
    print(f"   Total tokens: {analysis['total_tokens']:,}")
    print(f"   Sections: {analysis['h2_sections']} (## headers)")
    print(f"   Subsections: {analysis['h3_sections']} (### headers)")
    print(f"   Code blocks: {analysis['code_blocks']}")
    print(f"   Average section size: {analysis['avg_section_tokens']:,} tokens")
    print("")
    
    # Print suggestions
    if suggestions:
        print("⚠️  Optimization Suggestions:")
        for suggestion in suggestions:
            level_emoji = {
                'CRITICAL': '🚨',
                'WARNING': '⚠️',
                'INFO': 'ℹ️'
            }
            emoji = level_emoji.get(suggestion['level'], '•')
            print(f"   {emoji} {suggestion['message']}")
            print(f"     → {suggestion['action']}")
        print("")
    
    # Create chunking plan if needed
    if analysis['total_tokens'] > 50000:
        chunks = create_chunking_plan(text)
        print("📋 Suggested Chunking Plan:")
        for chunk in chunks:
            print(f"   Chunk {chunk['chunk_num']}: {chunk['tokens']:,} tokens")
            print(f"     Preview: {chunk['preview']}")
        print(f"\n   Total chunks needed: {len(chunks)}")
        print(f"   Reduction: {analysis['total_tokens']:,} → {max(chunk['tokens'] for chunk in chunks):,} tokens per response")
    
    # Exit codes for automation
    if analysis['total_tokens'] > 180000:
        sys.exit(2)  # Critical - will cause overflow
    elif analysis['total_tokens'] > 150000:
        sys.exit(1)  # Warning - approaching limit
    else:
        sys.exit(0)  # OK

if __name__ == "__main__":
    main()