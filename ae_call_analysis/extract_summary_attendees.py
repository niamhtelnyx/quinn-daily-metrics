#!/usr/bin/env python3
"""
Extract attendees from the Summary section - much more reliable
The summary always says "X and Y of Telnyx met with Z of Company"
"""

import re
import subprocess

def get_google_doc_content(doc_id):
    """Get content from a Google Doc"""
    try:
        result = subprocess.run(
            f'source /Users/niamhcollins/clawd/.env.gog && gog docs cat {doc_id}',
            shell=True,
            capture_output=True,
            text=True,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout.strip(), f"✅ Document content retrieved ({len(result.stdout)} chars)"
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def extract_attendees_from_summary(content):
    """Extract attendees from the Summary section - much more reliable approach"""
    attendees = {
        'telnyx_aes': [],
        'prospects': [],
        'companies': [],
        'prospect_emails': []
    }
    
    try:
        # Find the summary section
        lines = content.split('\n')
        summary_text = ""
        
        for i, line in enumerate(lines):
            if line.strip().lower() == 'summary':
                # Get the next non-empty line (the actual summary)
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip():
                        summary_text = lines[j].strip()
                        break
                break
        
        if not summary_text:
            # Fallback: use first substantial line
            for line in lines:
                if len(line.strip()) > 50 and 'met with' in line.lower():
                    summary_text = line.strip()
                    break
        
        print(f"DEBUG: Summary text: {summary_text[:200]}...")
        
        if summary_text:
            # Extract attendees using common patterns in summaries
            
            # Pattern 1: "X and Y of Telnyx/Tel Next met with Z"
            telnyx_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)?)\s+of\s+(?:Telnyx|Tel\s*Next)'
            prospect_pattern = r'met with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:of\s+([^.]+))?'
            
            # Extract Telnyx employees
            telnyx_matches = re.findall(telnyx_pattern, summary_text, re.IGNORECASE)
            for match in telnyx_matches:
                # Split on "and" to get individual names
                names = re.split(r'\s+and\s+', match, flags=re.IGNORECASE)
                for name in names:
                    clean_name = name.strip()
                    if clean_name and len(clean_name.split()) <= 3:  # Reasonable name length
                        attendees['telnyx_aes'].append(clean_name)
            
            # Extract prospects
            prospect_matches = re.findall(prospect_pattern, summary_text, re.IGNORECASE)
            for match in prospect_matches:
                if isinstance(match, tuple):
                    prospect_name = match[0].strip()
                    company = match[1].strip() if len(match) > 1 and match[1] else ""
                else:
                    prospect_name = match.strip()
                    company = ""
                
                if prospect_name:
                    attendees['prospects'].append(prospect_name)
                if company:
                    attendees['companies'].append(company)
            
            # Alternative pattern: "The [Company] team" or "Prospect Name" in different contexts
            if not attendees['prospects']:
                # Look for other name patterns
                alt_patterns = [
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:expressed|confirmed|requested|noted|stated)',
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+of\s+([A-Z][A-Za-z\s]+)',
                ]
                
                for pattern in alt_patterns:
                    matches = re.findall(pattern, summary_text)
                    for match in matches:
                        if isinstance(match, tuple):
                            name = match[0].strip()
                            company = match[1].strip() if len(match) > 1 else ""
                        else:
                            name = match.strip()
                            company = ""
                        
                        # Skip if this looks like a Telnyx person
                        if name not in attendees['telnyx_aes']:
                            attendees['prospects'].append(name)
                            if company:
                                attendees['companies'].append(company)
        
        # Extract emails from title or content
        title_line = content.split('\n')[0] if content else ""
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', title_line)
        attendees['prospect_emails'] = emails
        
        # Remove duplicates
        attendees['telnyx_aes'] = list(set(attendees['telnyx_aes']))
        attendees['prospects'] = list(set(attendees['prospects']))
        attendees['companies'] = list(set(attendees['companies']))
        attendees['prospect_emails'] = list(set(attendees['prospect_emails']))
        
        return attendees
        
    except Exception as e:
        print(f"Error extracting summary attendees: {e}")
        return attendees

def test_summary_extraction():
    """Test summary-based attendee extraction"""
    print("🎯 Testing Summary-Based Attendee Extraction")
    print("=" * 60)
    
    test_docs = [
        ("1RR-2K3mRD_DymfFTxRS_dhYXrHKVo8n0SFto-uPRvss", "roly@meetgail.com and Ryan"),
        ("1rptvzzdTNQnXfG5Yb02X6CF5ZOITJwc2lgf2ugYZKxw", "Ken <> Ryan"),
        ("1c5Zpdvmy3vFGu3xnyl3xWeVLMxBs7UtpuAFk2UZC3lI", "sruthi@eltropy.com and Rob")
    ]
    
    for doc_id, title in test_docs:
        print(f"\n📄 Testing: {title}")
        print("-" * 40)
        
        content, status = get_google_doc_content(doc_id)
        if content:
            attendees = extract_attendees_from_summary(content)
            
            print(f"✅ Summary extraction results:")
            print(f"   👨‍💼 Telnyx AEs: {attendees['telnyx_aes']}")
            print(f"   👤 Prospects: {attendees['prospects']}")
            print(f"   🏢 Companies: {attendees['companies']}")
            print(f"   📧 Emails: {attendees['prospect_emails']}")
            
            # Determine primary prospect and AE
            primary_prospect = ""
            if attendees['prospect_emails']:
                primary_prospect = attendees['prospect_emails'][0]
            elif attendees['prospects']:
                primary_prospect = attendees['prospects'][0]
            
            primary_ae = attendees['telnyx_aes'][0] if attendees['telnyx_aes'] else "Unknown"
            
            print(f"   🎯 PRIMARY: {primary_prospect} | AE: {primary_ae}")
        else:
            print(f"❌ {status}")

if __name__ == "__main__":
    test_summary_extraction()