#!/usr/bin/env python3
"""
Debug why prospect parsing returns 'Unknown Prospect' for Voxtelesys content
"""
import re

def extract_attendees_from_content(content, title=""):
    """Exact copy of the function from V1_GOOGLE_DRIVE_ENHANCED.py"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # Enhanced list of known Telnyx AEs
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian'
    ]
    
    try:
        print(f"🔍 DEBUGGING PARSING")
        print(f"Title: {title}")
        print(f"Content length: {len(content)}")
        print(f"First 200 chars: {content[:200]}")
        print("-" * 60)
        
        # PRIORITY 1: Extract from title (most reliable)
        title_patterns = [
            (r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx', "Company <> Telnyx"),  # "Company <> Telnyx"
            (r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)', "Telnyx <> Company"),      # "Telnyx <> Company"  
            (r'^Copy of ([^/]+)\s*/\s*Telnyx', "Company / Telnyx"),            # "Company / Telnyx"
            (r'^Copy of (.+?)\s+and\s+\w+:', "Company and Person:"),              # "Company and Person:"
            (r'^Copy of (.+?)\s+-\s+.*Notes by Gemini', "Extract before date"),   # Extract before date
        ]
        
        print("1️⃣ Testing title patterns:")
        for pattern, desc in title_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                potential_company = match.group(1).strip()
                # Clean up company name
                potential_company = re.sub(r'\s*(meeting|call|sync|demo)\s*$', '', potential_company, flags=re.IGNORECASE)
                potential_company = re.sub(r'\s*(intro|recurring)\s*', ' ', potential_company, flags=re.IGNORECASE).strip()
                print(f"   ✅ {desc}: '{potential_company}'")
                if len(potential_company) > 2 and 'telnyx' not in potential_company.lower():
                    prospect_name = potential_company.title()
                    print(f"   🎯 Set prospect_name: '{prospect_name}'")
                    break
                else:
                    print(f"   ❌ Rejected: len={len(potential_company)}, contains_telnyx={'telnyx' in potential_company.lower()}")
            else:
                print(f"   ❌ {desc}: No match")
        
        print(f"\n2️⃣ After title parsing: prospect_name = '{prospect_name}'")
        
        # PRIORITY 2: Extract people mentioned in content (for AE identification)
        people_pattern = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b'  # More precise: FirstName LastName
        people_mentioned = re.findall(people_pattern, content)
        
        print(f"\n3️⃣ People found in content: {people_mentioned}")
        
        # Remove duplicates and filter obvious non-names
        filtered_people = list(set([p for p in people_mentioned if 
            len(p.split()) == 2 and  # Exactly 2 words
            not any(x in p.lower() for x in ['telnyx', 'meeting', 'call', 'notes', 'summary', 'details'])
        ]))
        
        print(f"   Filtered people: {filtered_people}")
        
        # Identify Telnyx AE from people mentioned
        for person in filtered_people:
            person_lower = person.lower()
            # Check against known AEs
            is_known_ae = any(ae.lower() in person_lower for ae in telnyx_aes)
            print(f"   {person}: {'✅ Known AE' if is_known_ae else '❌ Unknown'}")
            
            if is_known_ae:
                ae_name = person.title()
                print(f"   🎯 Set ae_name: '{ae_name}'")
                break
            # Check for partial matches on first names of known AEs
            first_name = person.split()[0].lower()
            first_name_match = first_name in [ae.split()[0] for ae in telnyx_aes if ' ' in ae]
            if first_name_match:
                ae_name = person.title()
                print(f"   🎯 Set ae_name via first name: '{ae_name}'")
                break
        
        # PRIORITY 3: Extract email addresses 
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        print(f"\n4️⃣ Emails found: {emails}")
        
        # Filter out Telnyx emails to find prospect email
        for email in emails:
            if '@telnyx.com' not in email.lower():
                prospect_email = email
                print(f"   🎯 Non-Telnyx email: {prospect_email}")
                # Use email domain as company if still unknown
                if prospect_name == 'Unknown Prospect':
                    domain = email.split('@')[1].split('.')[0]
                    prospect_name = domain.title()
                    print(f"   🎯 Set prospect_name from domain: '{prospect_name}'")
                break
        
        print(f"\n🎯 FINAL RESULT:")
        print(f"   prospect_name: '{prospect_name}'")
        print(f"   prospect_email: '{prospect_email}'")
        print(f"   ae_name: '{ae_name}'")
        
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {
            'prospect_name': 'Unknown Prospect',
            'prospect_email': '',
            'ae_name': 'Unknown AE'
        }

# Test with actual Voxtelesys data
title = "Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini"
content = """
Telnyx // Voxtelesys
Invited   
Attachments  
Meeting records   

Summary
The meeting between Kevin Burke, Austin Lazarus, and Chris Cho focused on technical requirements for outbound calling using CLX switches and Texids, particularly addressing Kevin Burke's concerns about pricing and the necessity of using an alt SPID with their existing Local Routing Number (LRN) and Net Number ID (NND). Chris Cho presented number termination options, favoring a seamless two-factor authentication (2FA) process where Kevin Burke could intercept and return the code via an API, which Chris Cho recommended running for about a day to verify all numbers; Chris Cho also noted that whitelisting a whole Operating Company Number (OCN) or SPID for termination is disallowed, requiring 2FA for each number. Kevin Burke decided to check the feasibility and associated cost of the 2FA process internally, indicating that the integration is a long-term goal for redundancy and resiliency, likely facing pushback due to current development focus and an earliest discussion timeline of Q3 this year.
"""

if __name__ == "__main__":
    result = extract_attendees_from_content(content, title)
