#!/usr/bin/env python3
"""Test the fixed parsing logic"""
import re

def test_fixed_parsing():
    title = "Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini"
    content = """📝 Notes
Mar 4, 2026
Telnyx // Voxtelesys
Invited Chris Cho Austin Lazarus Kevin Burke"""
    
    print("🔍 TESTING FIXED PARSING")
    print("-" * 60)
    
    # NEW title patterns (with // fix)
    title_patterns = [
        (r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx', "Company <>&| Telnyx"),
        (r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)', "Telnyx <>&| Company"),  
        (r'^Copy of Telnyx\s*//\s*([^-]+)', "Telnyx // Company (NEW)"),  # NEW
        (r'^Copy of ([^/]+)\s*/\s*Telnyx', "Company / Telnyx"),
        (r'^Copy of (.+?)\s+and\s+\w+:', "Company and Person:"),
        (r'^Copy of (.+?)\s+-\s+.*Notes by Gemini', "Before date"),
    ]
    
    # Test title parsing
    prospect_name = 'Unknown Prospect'
    for pattern, desc in title_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            potential_company = match.group(1).strip()
            # Clean up company name (like in original code)
            potential_company = re.sub(r'\s*(meeting|call|sync|demo)\s*$', '', potential_company, flags=re.IGNORECASE)
            potential_company = re.sub(r'\s*(intro|recurring)\s*', ' ', potential_company, flags=re.IGNORECASE).strip()
            if len(potential_company) > 2 and 'telnyx' not in potential_company.lower():
                prospect_name = potential_company.title()
                print(f"✅ {desc} -> '{prospect_name}'")
                break
        else:
            print(f"❌ {desc}")
    
    # Test people extraction
    people_pattern = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b'
    people_mentioned = re.findall(people_pattern, content)
    
    # Filter
    filtered_people = list(set([p for p in people_mentioned if 
        len(p.split()) == 2 and
        not any(x in p.lower() for x in ['telnyx', 'meeting', 'call', 'notes', 'summary', 'details'])
    ]))
    
    print(f"\n👥 People found: {filtered_people}")
    
    # NEW AE list (with Austin Lazarus)
    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius', 'austin lazarus',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian', 'chris cho'
    ]
    
    ae_name = 'Unknown AE'
    external_person = None
    
    # Identify AE and external person
    for person in filtered_people:
        person_lower = person.lower()
        if any(ae.lower() in person_lower for ae in telnyx_aes):
            ae_name = person.title()
            print(f"✅ Telnyx AE: {ae_name}")
        else:
            external_person = person.title() 
            print(f"🎯 External person: {external_person}")
    
    # Final result
    print(f"\n🎯 FINAL EXTRACTION:")
    print(f"   Company: {prospect_name}")
    print(f"   Prospect: {external_person}")
    print(f"   AE: {ae_name}")
    
    if prospect_name != "Unknown Prospect" and external_person:
        print(f"\n✅ SUCCESS! Should search Salesforce for: {external_person} at {prospect_name}")
    else:
        print(f"\n❌ Still has issues")

if __name__ == "__main__":
    test_fixed_parsing()
