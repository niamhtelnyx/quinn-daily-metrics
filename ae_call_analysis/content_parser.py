#!/usr/bin/env python3
"""
Content parsing and analysis functions
"""

import re
from config import *

def parse_google_doc_tabs(content):
    """Parse Google Doc content to separate summary and transcript tabs"""
    if not content or len(content) < MIN_CONTENT_LENGTH:
        return None, None
    
    content_lower = content.lower()
    
    # Find the best transcript section start position
    transcript_start_pos = None
    best_pattern = None
    
    for pattern in TRANSCRIPT_PATTERNS:
        matches = list(re.finditer(pattern, content_lower, re.MULTILINE | re.IGNORECASE))
        
        if matches:
            match = matches[0]
            transcript_start_pos = match.start()
            best_pattern = pattern
            print(f"        🎯 Found transcript section with pattern: {pattern}")
            break
    
    if transcript_start_pos is None:
        # Additional check for transcript content indicators
        for indicator in TRANSCRIPT_INDICATORS:
            if indicator in content_lower:
                # Look for common section dividers
                potential_dividers = ['\n\n\n', '\n---\n', '\nsummary\n', '\nnotes\n']
                
                for divider in potential_dividers:
                    pos = content_lower.find(divider)
                    if pos != -1 and pos < len(content) // 2:  # In first half
                        transcript_start_pos = pos + len(divider)
                        print(f"        🔍 Found transcript via indicator + divider")
                        break
                
                if transcript_start_pos:
                    break
    
    if transcript_start_pos is None:
        # Final check: Look for content that's clearly transcript-like
        lines = content.split('\n')
        short_lines = sum(1 for line in lines if 10 < len(line.strip()) < 60)
        total_lines = len([line for line in lines if line.strip()])
        
        if total_lines > 20 and short_lines / total_lines > 0.6:
            print(f"        🎙️ Content appears to be transcript-like, using as transcript")
            return None, content.strip()
        else:
            print(f"        📋 No transcript section found, using full content as summary")
            return content.strip(), None
    
    # Split content at transcript boundary
    summary = content[:transcript_start_pos].strip()
    transcript = content[transcript_start_pos:].strip()
    
    # Validate the split makes sense
    if len(summary) < 50:
        print(f"        ⚠️ Summary section too short ({len(summary)} chars), treating as transcript-only")
        return None, content.strip()
    
    if len(transcript) < MIN_TRANSCRIPT_LENGTH:
        print(f"        ⚠️ Transcript section too short ({len(transcript)} chars), treating as summary-only")
        return content.strip(), None
    
    # Clean up summary (remove trailing incomplete sentences)
    summary_lines = summary.split('\n')
    if summary_lines and len(summary_lines) > 1:
        last_line = summary_lines[-1].strip()
        if last_line and len(last_line) > 10 and not last_line.endswith(('.', '!', '?', ':', ';')):
            summary_lines = summary_lines[:-1]
    
    summary = '\n'.join(summary_lines).strip()
    
    print(f"        ✅ Parsed: Summary ({len(summary)} chars) + Transcript ({len(transcript)} chars)")
    
    return summary, transcript

def analyze_content_structure(content):
    """Analyze content and return structured data"""
    if not content:
        return None
    
    # Parse into summary and transcript
    summary, transcript = parse_google_doc_tabs(content)
    
    return {
        'full_content': content,
        'summary': summary,
        'transcript': transcript,
        'total_chars': len(content),
        'has_transcript': transcript is not None,
        'has_summary': summary is not None
    }

def select_best_content(content_data):
    """Select the best content for analysis based on availability and quality"""
    if not content_data:
        return None, None
    
    # Smart content selection with robust fallback
    if content_data['transcript'] and len(content_data['transcript']) > MIN_TRANSCRIPT_LENGTH:
        print(f"        🎙️ Using transcript content")
        return content_data['transcript'], 'transcript'
    elif content_data['summary'] and len(content_data['summary']) > MIN_SUMMARY_LENGTH:
        print(f"        📋 Using summary content (no transcript available)")
        return content_data['summary'], 'gemini_summary'
    elif content_data['full_content'] and len(content_data['full_content']) > MIN_SUMMARY_LENGTH:
        print(f"        📄 Using full content (parsing unclear)")
        return content_data['full_content'], 'full_content'
    else:
        print(f"        ❌ Content too short or invalid")
        return None, None

def extract_insights_from_content(content):
    """Extract meaningful insights from meeting content"""
    insights = {
        'pain_points': [],
        'products': [],
        'next_steps': [],
        'attendees': [],
        'company_info': ''
    }
    
    if not content or len(content) < MIN_CONTENT_LENGTH:
        return insights
    
    content_lower = content.lower()
    
    # Extract attendees (email patterns)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, content)
    insights['attendees'] = list(set(emails[:5]))  # Limit and dedupe
    
    # Extract pain points
    sentences = content.split('.')
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in PAIN_KEYWORDS):
            if 20 < len(sentence_clean) < MAX_INSIGHT_LENGTH:
                insights['pain_points'].append(sentence_clean)
                if len(insights['pain_points']) >= 3:
                    break
    
    # Extract product mentions
    for keyword, product_name in PRODUCT_KEYWORDS.items():
        if keyword in content_lower:
            insights['products'].append(product_name)
    
    # Extract next steps
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in ACTION_KEYWORDS):
            if 15 < len(sentence_clean) < 120:
                insights['next_steps'].append(sentence_clean)
                if len(insights['next_steps']) >= 3:
                    break
    
    return insights

def parse_meeting_name(meeting_name):
    """Parse meeting name to extract prospect and company"""
    if '--' in meeting_name:
        parts = meeting_name.split('--')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip()
    elif ' - ' in meeting_name:
        parts = meeting_name.split(' - ')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip() if len(parts) > 1 else ""
    else:
        prospect_name = meeting_name.split()[0] if meeting_name.split() else "Unknown"
        company_name = ""
    
    # Clean up company name
    if 'telnyx' in company_name.lower():
        company_parts = company_name.split(',')
        for part in company_parts:
            clean_part = part.strip()
            if 'telnyx' not in clean_part.lower() and len(clean_part) > 2:
                company_name = clean_part
                break
    
    return prospect_name, company_name