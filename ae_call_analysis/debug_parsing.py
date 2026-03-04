#!/usr/bin/env python3
"""Debug the Voxtelesys parsing step by step"""
import re

def debug_title_parsing():
    title = "Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini"
    
    print("🔍 DEBUGGING TITLE PARSING")
    print(f"Title: {title}")
    print("-" * 60)
    
    # Current patterns from V1 Enhanced
    title_patterns = [
        (r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx', "Pattern 1: Company <>&| Telnyx"),
        (r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)', "Pattern 2: Telnyx <>&| Company"),  
        (r'^Copy of ([^/]+)\s*/\s*Telnyx', "Pattern 3: Company / Telnyx"),
        (r'^Copy of (.+?)\s+and\s+\w+:', "Pattern 4: Company and Person:"),
        (r'^Copy of (.+?)\s+-\s+.*Notes by Gemini', "Pattern 5: Before date"),
    ]
    
    # Test each pattern
    for pattern, desc in title_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            print(f"✅ {desc}")
            print(f"   Match: '{match.group(1)}'")
        else:
            print(f"❌ {desc}")
    
    print("\n🔧 MISSING PATTERN:")
    # The pattern we need for "Telnyx // Voxtelesys"
    new_pattern = r'^Copy of Telnyx\s*//\s*([^-]+)'
    match = re.search(new_pattern, title, re.IGNORECASE)
    if match:
        company = match.group(1).strip()
        print(f"✅ NEW: Telnyx // Company -> '{company}'")
    else:
        print("❌ New pattern also failed")

def debug_people_extraction():
    content = """📝 Notes
Mar 4, 2026
Telnyx // Voxtelesys
Invited Chris Cho Austin Lazarus Kevin Burke"""
    
    print("\n🔍 DEBUGGING PEOPLE EXTRACTION")
    print(f"Content sample: {content[:200]}")
    print("-" * 60)
    
    # People pattern from V1 Enhanced
    people_pattern = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b'
    people_mentioned = re.findall(people_pattern, content)
    
    print(f"Raw people found: {people_mentioned}")
    
    # Filter like V1 Enhanced does
    filtered_people = list(set([p for p in people_mentioned if 
        len(p.split()) == 2 and  # Exactly 2 words
        not any(x in p.lower() for x in ['telnyx', 'meeting', 'call', 'notes', 'summary', 'details'])
    ]))
    
    print(f"Filtered people: {filtered_people}")
    
    # Known AEs
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian'
    ]
    
    # Check who is Telnyx AE
    for person in filtered_people:
        person_lower = person.lower()
        is_ae = any(ae.lower() in person_lower for ae in telnyx_aes)
        print(f"  {person}: {'✅ Telnyx AE' if is_ae else '❌ External (Prospect?)'}")

if __name__ == "__main__":
    debug_title_parsing()
    debug_people_extraction()
