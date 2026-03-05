#!/usr/bin/env python3
"""Test the current parsing vs improved parsing"""

import re

def extract_attendees_from_content_improved(content, title=""):
    """Improved attendee extraction with better patterns"""
    prospect_name = 'Unknown Prospect'
    prospect_email = ''
    ae_name = 'Unknown AE'
    
    # Enhanced list of known Telnyx AEs
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'decliner slides', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian', 'milan', 'jackson', 'jon lucas'
    ]
    
    try:
        # First, try to extract from title (most reliable)
        title_patterns = [
            r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx',  # "Company <> Telnyx" or "Company | Telnyx"
            r'^Copy of (.+?)\s+and\s+\w+:',              # "Company and Person:"
            r'^Copy of ([^/]+)\s*/\s*Telnyx',            # "Company / Telnyx"
            r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)',      # "Telnyx <> Company"
            r'^Copy of (.+?)\s+-\s+.*Notes by Gemini',   # Extract before date
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                potential_company = match.group(1).strip()
                # Clean up company name
                potential_company = re.sub(r'\s*(meeting|call|sync|demo)\s*$', '', potential_company, flags=re.IGNORECASE)
                if len(potential_company) > 2 and 'telnyx' not in potential_company.lower():
                    prospect_name = potential_company.title()
                    print(f"📋 Title pattern match: '{prospect_name}' from '{title}'")
                    break
        
        # Extract people mentioned in content
        people_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b'
        people_mentioned = re.findall(people_pattern, content)
        
        print(f"👥 People found: {people_mentioned}")
        
        # Identify Telnyx AE from people mentioned
        for person in people_mentioned:
            person_lower = person.lower()
            if any(ae.lower() in person_lower for ae in telnyx_aes):
                ae_name = person.title()
                print(f"🎯 Identified Telnyx AE: {ae_name}")
                break
            # Look for common Telnyx names even if not in our list
            if any(name in person_lower for name in ['ryan', 'niamh', 'tyron', 'kai', 'danilo']):
                ae_name = person.title()
                print(f"🎯 Identified likely Telnyx AE: {ae_name}")
                break
        
        # Extract email addresses 
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # Filter out Telnyx emails to find prospect email
        for email in emails:
            if '@telnyx.com' not in email.lower():
                prospect_email = email
                if prospect_name == 'Unknown Prospect':
                    prospect_name = email.split('@')[0].replace('.', ' ').title()
                break
        
        # If still unknown prospect, try more content patterns
        if prospect_name == 'Unknown Prospect':
            content_patterns = [
                r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:team|discussed|explained|confirmed)',
                r'including\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'with\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+explaining'
            ]
            
            for pattern in content_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if 'telnyx' not in match.lower() and len(match) > 2:
                        prospect_name = match.strip()
                        print(f"📄 Content pattern match: {prospect_name}")
                        break
                if prospect_name != 'Unknown Prospect':
                    break
        
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }
        
    except Exception as e:
        print(f"⚠️ Error extracting attendees: {str(e)}")
        return {
            'prospect_name': prospect_name,
            'prospect_email': prospect_email,
            'ae_name': ae_name
        }

# Test with the problematic SelfLabs content
test_title = "Copy of SelfLabs <> Telnyx Recurring Call - 2026/03/02 11:55 MST - Notes by Gemini"
test_content = """SelfLabs <> Telnyx Recurring Call
Invited   
Attachments  
Meeting records   

Summary
The team, including Milan Cheeks, Jackson Smrecansky, and Jon Lucas, discussed several operational and technical topics, beginning with the first use of Bitcoin for payment enabled by the CEO, with Milan Cheeks explaining the goal of moving all payments to the blockchain for transparency, while Jackson Smrecansky clarified that exceeding the $5,000 spending commitment only requires replenishing the balance."""

print("=== TESTING IMPROVED PARSING ===")
print(f"Title: {test_title}")
print()

result = extract_attendees_from_content_improved(test_content, test_title)
print()
print("=== RESULTS ===")
print(f"Prospect: {result['prospect_name']}")
print(f"Email: {result['prospect_email']}")  
print(f"AE: {result['ae_name']}")