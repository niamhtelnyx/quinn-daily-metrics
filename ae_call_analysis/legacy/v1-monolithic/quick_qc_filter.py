#!/usr/bin/env python3
"""
QUICK Quality Control Filter - IMMEDIATE DEPLOYMENT
Blocks garbage posts from reaching #sales-calls
"""

import json
import re

def validate_call_quality(call_data, analysis):
    """
    Quick quality validation - blocks obvious garbage
    Returns: (should_post: bool, reason: str)
    """
    
    # Extract key fields
    prospect_name = call_data.get('prospect_name', '').strip()
    ae_name = call_data.get('ae_name', '').strip()
    content = call_data.get('content', '') or ''
    
    # QUALITY GATES - Block obvious garbage
    
    # 1. Block unknown names
    if prospect_name in ['Unknown Prospect', 'Unknown', '']:
        return False, "Unknown prospect name"
    
    if ae_name in ['Unknown AE', 'Unknown', '']:
        return False, "Unknown AE name"
    
    # 2. Block if no content extracted
    if not content or len(content.strip()) < 100:
        return False, "No meaningful content extracted"
    
    # 3. Block JSON error messages in summary
    summary = analysis.get('summary', '')
    if any(indicator in summary.lower() for indicator in [
        'json', '```json', 'insufficient conversation', 'supported language',
        'no summary was produced', 'error', 'failed'
    ]):
        return False, "AI analysis contains error messages"
    
    # 4. Block if analysis is mostly empty
    key_points = analysis.get('key_points', [])
    next_steps = analysis.get('next_steps', [])
    
    if len(key_points) == 0 and len(next_steps) == 0:
        return False, "Analysis contains no actionable content"
    
    # 5. Block generic/meaningless analysis
    if len(key_points) == 1 and 'AI analysis available' in str(key_points):
        return False, "Generic AI analysis fallback"
    
    # 6. Block if prospect name looks like parsing error
    if any(indicator in prospect_name.lower() for indicator in [
        'copy of', 'notes by gemini', 'meeting -', 'porting', 'sync'
    ]):
        return False, "Prospect name looks like document title parsing error"
    
    # 7. Require minimum name length
    if len(prospect_name) < 3 or len(ae_name) < 3:
        return False, "Names too short to be meaningful"
    
    # 8. Block if summary is too short
    if len(summary.strip()) < 20:
        return False, "Summary too short to be meaningful"
    
    # ALL QUALITY GATES PASSED
    return True, "Quality validation passed"

def log_qc_result(call_data, analysis, should_post, reason):
    """Log QC decision for debugging"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prospect = call_data.get('prospect_name', 'Unknown')
    decision = "✅ APPROVED" if should_post else "❌ BLOCKED"
    
    print(f"[{timestamp}] 🛡️ QC: {decision} - {prospect} - {reason}")
    
    # Log to file for debugging
    with open('logs/qc_decisions.log', 'a') as f:
        f.write(f"[{timestamp}] {decision} | {prospect} | {reason}\n")
        if not should_post:
            f.write(f"    Content length: {len(call_data.get('content', ''))}\n")
            f.write(f"    Summary: {analysis.get('summary', '')[:100]}...\n")
            f.write(f"    AE: {call_data.get('ae_name', 'Unknown')}\n")
            f.write("\n")

if __name__ == "__main__":
    # Test with garbage example
    garbage_call = {
        'prospect_name': 'Unknown Prospect',
        'ae_name': 'Unknown AE',
        'content': None
    }
    
    garbage_analysis = {
        'summary': '```json\n{\n"summary": "No summary was produced due to insufficient conversation in a supported language.",',
        'key_points': [],
        'next_steps': []
    }
    
    should_post, reason = validate_call_quality(garbage_call, garbage_analysis)
    print(f"Garbage test: {should_post} - {reason}")
    
    # Test with good example
    good_call = {
        'prospect_name': 'Clearline Communications',
        'ae_name': 'Danilo Rodriguez',
        'content': 'This is a substantial call transcript with meaningful content about the prospect\'s needs and our solution discussion.'
    }
    
    good_analysis = {
        'summary': 'Discussed implementation timeline and technical requirements for voice infrastructure.',
        'key_points': ['API integration requirements', 'Timeline discussion'],
        'next_steps': ['Send technical proposal', 'Schedule follow-up']
    }
    
    should_post, reason = validate_call_quality(good_call, good_analysis)
    print(f"Good test: {should_post} - {reason}")