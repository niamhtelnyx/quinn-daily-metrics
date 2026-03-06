#!/usr/bin/env python3
"""
Final company summary function for Slack integration
Returns standalone business descriptions for proper grammar
"""

import os
import openai
from dotenv import load_dotenv

def get_company_description(company_name, company_domain=None):
    """
    Generate accurate business description for Slack company line
    Returns: Standalone description to be used in "CompanyName is a [description]."
    """
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "technology company"
    
    client = openai.OpenAI(api_key=api_key)
    
    domain_context = f" (website: {company_domain})" if company_domain else ""
    
    prompt = f"""What type of business is {company_name}{domain_context}? Provide a detailed description of their business model and value proposition.

Include as much relevant detail as possible:
- Their specific industry/sector and niche
- What products/services they sell or provide
- Their target market and customer types
- Revenue model or business approach
- Key features, differentiators, or geographic focus
- Market position (if known)

Format as a descriptive noun phrase that completes: "{company_name} is a ___"

Examples of rich descriptions:
✅ "peer-to-peer lending platform connecting European investors with high-growth company loans in a regulated marketplace"
✅ "payment processing and financial infrastructure platform serving online businesses, marketplaces, and enterprise clients globally"
✅ "AI-powered customer support automation software that helps businesses handle inquiries across multiple channels"
✅ "short-term rental marketplace connecting travelers with unique accommodations from local hosts worldwide"
✅ "call tracking and attribution software helping marketing agencies measure campaign performance and ROI"

Avoid generic terms like:
❌ "technology company"
❌ "software platform"
❌ "solutions provider"

Aim for 100-200 characters when possible. Be specific and informative. Return only the description phrase."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You identify specific business models and industries, avoiding generic tech descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=80,
            temperature=0.2
        )
        
        description = response.choices[0].message.content.strip()
        
        # Clean up response
        if description.startswith('"') and description.endswith('"'):
            description = description[1:-1]
        
        # Clean up any prefixes
        if description.lower().startswith(company_name.lower()):
            description = description[len(company_name):].strip()
        
        # Remove common prefixes that might appear
        prefixes_to_remove = [" is a ", " is an ", " is ", "is a ", "is an ", "is "]
        for prefix in prefixes_to_remove:
            if description.startswith(prefix):
                description = description[len(prefix):].strip()
                break
        
        return description.strip()
        
    except Exception as e:
        # Graceful fallback
        return "technology company exploring communications solutions"

def create_company_line(company_name, company_domain=None):
    """Create the complete company line for Slack messages"""
    
    if not company_name or company_name.lower() == 'telnyx':
        return ""  # No line needed for Telnyx or empty names
    
    description = get_company_description(company_name, company_domain)
    return f"🏢 {company_name} is a {description}."

# Test the final integration
def test_slack_integration():
    """Test how this will look in actual Slack posts"""
    
    print("📱 SLACK INTEGRATION TEST")
    print("=" * 30)
    
    test_companies = [
        ("Afranga", "afranga.com"),
        ("Commercials", None),
        ("Matelso", "matelso.com"),
        ("PracticePilotAI", "practicepilot.ai")
    ]
    
    for company_name, domain in test_companies:
        print(f"\n🏢 Testing: {company_name}")
        
        company_line = create_company_line(company_name, domain)
        
        print(f"📋 Company line: {company_line}")
        
        # Show in full Slack message context
        print("📱 In Slack message:")
        print(f"""🔔 Meeting Notes Retrieved
📆 {company_name} | Telnyx AE Team | 2026-03-06 | 🤖 AI Summary
{company_line}
🏢 Salesforce: Contact | Account | Event
📊 Scores: Interest 8/10...""")
        print("-" * 50)

if __name__ == "__main__":
    test_slack_integration()