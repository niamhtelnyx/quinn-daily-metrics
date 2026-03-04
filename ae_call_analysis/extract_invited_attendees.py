#!/usr/bin/env python3
"""
Extract attendees from the "Invited" section of Google Meet documents
Much more reliable than parsing from content narrative
"""

import re
import os
import sys
def get_google_doc_content(doc_id):
    """Get content from a Google Doc"""
    import subprocess
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

def extract_invited_attendees(content):
    """Extract attendees from the structured 'Invited' section"""
    attendees = {
        'invited_names': [],
        'prospect_emails': [],
        'ae_names': [],
        'all_attendees': []
    }
    
    try:
        # Look for the "Invited" section specifically
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip().lower() == 'invited' or line.strip().startswith('Invited'):
                # The next line should contain the attendee names
                if i + 1 < len(lines):
                    invited_line = lines[i + 1].strip()
                    
                    # Also check if invited info is on the same line
                    if 'invited' in line.lower() and len(line.strip()) > 10:
                        invited_line = line.replace('Invited', '').strip()
                    
                    if invited_line:
                        # Parse attendee names from the invited line
                        # They appear to be separated by spaces and are typically "First Last" format
                        
                        # First, try to identify individual names
                        # Look for patterns of "FirstName LastName" 
                        name_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b'
                        names = re.findall(name_pattern, invited_line)
                        
                        for name in names:
                            attendees['invited_names'].append(name.strip())
                            attendees['all_attendees'].append(name.strip())
                        
                        print(f"DEBUG: Invited line: '{invited_line}'")
                        print(f"DEBUG: Extracted names: {names}")
                        
                        break
        
        # Classify names as AE vs prospect
        telnyx_names = ['Ryan Simkins', 'Dan Danovich', 'Rob Messier', 'Nick Mihalovich', 'Dave Miller']  # Add known AEs
        
        for name in attendees['invited_names']:
            if name in telnyx_names or any(telnyx_name.split()[0] == name.split()[0] for telnyx_name in telnyx_names):
                attendees['ae_names'].append(name)
            else:
                # This is likely a prospect
                # Try to find their email in content or title
                first_name = name.split()[0]
                
                # Look for email patterns near this name
                name_context = content[max(0, content.find(name)-100):content.find(name)+100]
                email_pattern = r'\b[A-Za-z0-9._%+-]*' + re.escape(first_name.lower()) + r'[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                potential_emails = re.findall(email_pattern, content, re.IGNORECASE)
                
                if potential_emails:
                    attendees['prospect_emails'].append(potential_emails[0])
                
        # Also check document title for emails
        first_line = content.split('\n')[0] if content else ""
        title_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', first_line)
        for email in title_emails:
            if email not in attendees['prospect_emails']:
                attendees['prospect_emails'].append(email)
        
        return attendees
        
    except Exception as e:
        print(f"Error extracting invited attendees: {e}")
        return attendees

def test_invited_extraction():
    """Test the invited attendee extraction on real documents"""
    print("🧪 Testing Invited Attendee Extraction")
    print("=" * 50)
    
    # Test on known documents
    test_docs = [
        ("1RR-2K3mRD_DymfFTxRS_dhYXrHKVo8n0SFto-uPRvss", "roly@meetgail.com and Ryan"),
        ("1rptvzzdTNQnXfG5Yb02X6CF5ZOITJwc2lgf2ugYZKxw", "Ken <> Ryan"),
        ("1c5Zpdvmy3vFGu3xnyl3xWeVLMxBs7UtpuAFk2UZC3lI", "sruthi@eltropy.com and Rob")
    ]
    
    for doc_id, title in test_docs:
        print(f"\n📄 Testing: {title}")
        print("-" * 30)
        
        content, status = get_google_doc_content(doc_id)
        if content:
            # Show the first few lines to see the invited section
            lines = content.split('\n')[:10]
            print("📋 Document structure:")
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"   {i}: {line}")
            
            # Extract invited attendees
            attendees = extract_invited_attendees(content)
            
            print(f"\n✅ Extraction results:")
            print(f"   👥 Invited names: {attendees['invited_names']}")
            print(f"   📧 Prospect emails: {attendees['prospect_emails']}")
            print(f"   👨‍💼 AE names: {attendees['ae_names']}")
        else:
            print(f"❌ Could not retrieve content: {status}")

if __name__ == "__main__":
    test_invited_extraction()