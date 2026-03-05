#!/usr/bin/env python3
"""
Refined attendee extraction with multiple pattern handling
Handles different summary formats from Gemini
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

def extract_refined_attendees(content):
    """Refined attendee extraction with multiple patterns"""
    attendees = {
        'telnyx_aes': [],
        'prospects': [],
        'companies': [],
        'prospect_emails': []
    }
    
    try:
        # Get summary and details text
        lines = content.split('\n')
        summary_text = ""
        details_text = ""
        
        # Extract summary
        for i, line in enumerate(lines):
            if line.strip().lower() == 'summary':
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip():
                        summary_text = lines[j].strip()
                        break
                break
        
        # Extract details (first few paragraphs)
        for i, line in enumerate(lines):
            if line.strip().lower() == 'details':
                details_lines = []
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip():
                        details_lines.append(lines[j].strip())
                    if len(details_lines) >= 3:  # Get first 3 detail paragraphs
                        break
                details_text = ' '.join(details_lines)
                break
        
        print(f"DEBUG: Summary: {summary_text[:150]}...")
        print(f"DEBUG: Details: {details_text[:150]}...")
        
        # Extract emails from title
        title_line = content.split('\n')[0] if content else ""
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', title_line)
        attendees['prospect_emails'] = emails
        
        # PATTERN 1: Standard "X and Y of Telnyx met with Z" format
        if 'met with' in summary_text.lower() and ('telnyx' in summary_text.lower() or 'tel next' in summary_text.lower()):
            # Extract Telnyx people
            telnyx_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+and\s+([A-Z][a-z]+\s+[A-Z][a-z]+))?\s+of\s+(?:Telnyx|Tel\s*Next)'
            telnyx_matches = re.findall(telnyx_pattern, summary_text, re.IGNORECASE)
            for match in telnyx_matches:
                for name in match:
                    if name.strip():
                        attendees['telnyx_aes'].append(name.strip())
            
            # Extract prospects
            prospect_pattern = r'met with\s+([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+of\s+([^.]+?))?(?:\s+to\s+discuss|\s+of|\.)'
            prospect_matches = re.findall(prospect_pattern, summary_text, re.IGNORECASE)
            for match in prospect_matches:
                if isinstance(match, tuple):
                    attendees['prospects'].append(match[0].strip())
                    if match[1].strip():
                        attendees['companies'].append(match[1].strip())
                else:
                    attendees['prospects'].append(match.strip())
        
        # PATTERN 2: "X initiated the call with Y" format
        elif 'initiated the call' in summary_text.lower() or 'initiated' in summary_text.lower():
            # X initiated = Telnyx person, Y = prospect
            init_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+initiated the call with\s+([A-Z][a-z]+)'
            init_matches = re.findall(init_pattern, summary_text, re.IGNORECASE)
            for match in init_matches:
                attendees['telnyx_aes'].append(match[0].strip())  # Initiator is Telnyx
                attendees['prospects'].append(match[1].strip())   # Other person is prospect
        
        # PATTERN 3: Look for AEs who "confirmed", "explained", "noted" Telnyx policies/pricing
        telnyx_action_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:confirmed|explained|noted|stated).*?(?:minimum|pricing|commercial|platform|Telnyx|Tel Next)'
        telnyx_action_matches = re.findall(telnyx_action_pattern, summary_text + " " + details_text, re.IGNORECASE)
        for match in telnyx_action_matches:
            if match.strip() not in attendees['telnyx_aes']:
                attendees['telnyx_aes'].append(match.strip())
        
        # PATTERN 4: Extract from details section if summary didn't work
        if not attendees['telnyx_aes'] or not attendees['prospects']:
            # Look for "account executive" or "solutions engineer" context
            ae_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:,\s*(?:an\s+)?(?:account executive|solutions engineer|sales))'
            ae_matches = re.findall(ae_pattern, details_text, re.IGNORECASE)
            for match in ae_matches:
                if match not in attendees['telnyx_aes']:
                    attendees['telnyx_aes'].append(match)
            
            # Look for prospect names in context
            prospect_patterns = [
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:expressed|confirmed|requested|noted|stated|explained)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+of\s+([A-Z][A-Za-z\s]+)',
            ]
            
            for pattern in prospect_patterns:
                matches = re.findall(pattern, details_text)
                for match in matches:
                    if isinstance(match, tuple):
                        name = match[0].strip()
                        company = match[1].strip() if len(match) > 1 else ""
                    else:
                        name = match.strip()
                        company = ""
                    
                    # Skip if already identified as Telnyx
                    if name not in attendees['telnyx_aes']:
                        if name not in attendees['prospects']:
                            attendees['prospects'].append(name)
                        if company and company not in attendees['companies']:
                            attendees['companies'].append(company)
        
        # Clean up company names (remove extra text)
        clean_companies = []
        for company in attendees['companies']:
            # Take only the company name part
            clean_company = re.split(r'\s+(?:to discuss|is|seeks|due to)', company)[0].strip()
            if clean_company and clean_company not in clean_companies:
                clean_companies.append(clean_company)
        attendees['companies'] = clean_companies
        
        # Clean up names - remove false positives
        def is_valid_full_name(name):
            if not name or len(name.strip()) < 3:
                return False
            # Must be exactly 2 words (first and last name)
            words = name.strip().split()
            if len(words) != 2:
                return False
            # Both words should start with capital and be alphabetic
            return all(word[0].isupper() and word.isalpha() for word in words)
        
        def is_valid_prospect_name(name):
            if not name or len(name.strip()) < 2:
                return False
            # Allow 1 or 2 words for prospects (like "Ken" or "John Smith")
            words = name.strip().split()
            if len(words) > 2:
                return False
            # Words should start with capital and be alphabetic
            return all(word[0].isupper() and word.isalpha() for word in words)
        
        # Filter lists with appropriate validation
        attendees['telnyx_aes'] = [name for name in list(set(attendees['telnyx_aes'])) if is_valid_full_name(name)]
        attendees['prospects'] = [name for name in list(set(attendees['prospects'])) if is_valid_prospect_name(name)]
        
        # Remove duplicates and empty entries for other fields
        for key in ['companies', 'prospect_emails']:
            if isinstance(attendees[key], list):
                attendees[key] = [item for item in list(set(attendees[key])) if item and item.strip()]
        
        return attendees
        
    except Exception as e:
        print(f"Error in refined extraction: {e}")
        return attendees

def format_refined_call_data(call_data, content):
    """Format call data with refined attendee extraction"""
    
    attendees = extract_refined_attendees(content)
    
    # Determine primary prospect
    prospect_identifier = ""
    prospect_email = ""
    
    if attendees['prospect_emails']:
        prospect_email = attendees['prospect_emails'][0]
        prospect_identifier = prospect_email
    elif attendees['prospects']:
        prospect_identifier = attendees['prospects'][0]
    else:
        prospect_identifier = "Unknown Prospect"
    
    # Determine primary AE (prioritize those who explained Telnyx policies)
    ae_name = "Unknown"
    if attendees['telnyx_aes']:
        # Look for AE who explained/confirmed Telnyx policies (more reliable)
        policy_explainers = []
        for ae in attendees['telnyx_aes']:
            ae_context = content[max(0, content.find(ae)-50):content.find(ae)+200].lower()
            if any(word in ae_context for word in ['confirmed', 'explained', 'noted', 'minimum', 'pricing', 'commercial']):
                policy_explainers.append(ae)
        
        # Prefer policy explainers, otherwise use first AE
        ae_name = policy_explainers[0] if policy_explainers else attendees['telnyx_aes'][0]
    
    # Get primary company
    company_name = attendees['companies'][0] if attendees['companies'] else ""
    
    return {
        'prospect_name': prospect_identifier,
        'prospect_email': prospect_email,
        'ae_name': ae_name,
        'company_name': company_name,
        'attendees': attendees,
        'all_telnyx_aes': attendees['telnyx_aes'],
        'all_prospects': attendees['prospects']
    }

def test_refined_extraction():
    """Test refined extraction on challenging documents"""
    print("🎯 Testing Refined Attendee Extraction")
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
            call_data = format_refined_call_data({'id': doc_id, 'title': title}, content)
            
            print(f"✅ Refined extraction results:")
            print(f"   🎯 Primary Prospect: {call_data['prospect_name']}")
            print(f"   📧 Email: {call_data['prospect_email']}")
            print(f"   👨‍💼 Primary AE: {call_data['ae_name']}")
            print(f"   🏢 Company: {call_data['company_name']}")
            print(f"   👥 All AEs: {call_data['all_telnyx_aes']}")
            print(f"   👤 All Prospects: {call_data['all_prospects']}")
        else:
            print(f"❌ {status}")

if __name__ == "__main__":
    test_refined_extraction()