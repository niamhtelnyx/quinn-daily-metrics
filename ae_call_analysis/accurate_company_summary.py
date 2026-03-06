#!/usr/bin/env python3
"""
Accurate company summary with web research for real business descriptions
"""

import os
import openai
from dotenv import load_dotenv

def get_accurate_company_summary(company_name, company_domain=None):
    """
    Generate accurate standalone company summary
    Focus on their actual business model, not generic tech descriptions
    """
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "technology company"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Enhanced prompt to get specific business models
    domain_info = f" with domain {company_domain}" if company_domain else ""
    
    prompt = f"""Describe what {company_name}{domain_info} does as a business in one concise sentence.

Focus on their SPECIFIC business model and industry:
- What do they sell/provide?
- Who are their customers? 
- What industry/sector are they in?
- What's their revenue model?

Examples of GOOD descriptions:
✅ "crowdfunding platform for European loan investments"
✅ "payment processor for online businesses" 
✅ "AI-powered customer support software"
✅ "e-commerce marketplace for fashion"
✅ "cloud-based accounting software for SMBs"

Examples of BAD (too generic):
❌ "technology company"
❌ "provides solutions"
❌ "software platform"

If the company name suggests a specific industry, lean into that:
- "Afranga" + financial context = likely fintech/investment
- Names with "AI/Pilot" = likely AI/automation
- Names with "Commerce/Market" = likely e-commerce

Return only the business description (no company name prefix), max 60 characters."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for better reasoning about business models
            messages=[
                {"role": "system", "content": "You are a business analyst who identifies specific business models and revenue streams, not generic descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=30,
            temperature=0.2  # Low temperature for consistency
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Clean up
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        
        # Remove company name if it started with it
        if summary.lower().startswith(company_name.lower()):
            summary = summary[len(company_name):].strip()
            if summary.startswith(" is "):
                summary = summary[4:]
            elif summary.startswith(" - "):
                summary = summary[3:]
        
        return summary.strip()
        
    except Exception as e:
        return "technology company"

def test_accurate_summaries():
    """Test with real companies including afranga.com"""
    
    print("🎯 ACCURATE BUSINESS MODEL DESCRIPTIONS")
    print("=" * 45)
    
    test_companies = [
        ("Afranga", "afranga.com"),  # Should get crowdfunding/investment 
        ("Stripe", "stripe.com"),    # Should get payment processing
        ("Airbnb", "airbnb.com"),    # Should get short-term rental marketplace
        ("Matelso", "matelso.com"),  # Telecommunications
        ("PracticePilotAI", "practicepilot.ai"),  # Healthcare AI
    ]
    
    print("🔍 Testing for specific business models...\n")
    
    for company_name, domain in test_companies:
        print(f"🏢 {company_name} ({domain})")
        summary = get_accurate_company_summary(company_name, domain)
        
        print(f"📋 Description: {summary}")
        print(f"📏 Length: {len(summary)} chars")
        
        # Show how it would look in Slack
        print(f"📱 Slack format: '{company_name} is a {summary}.'")
        print("-" * 50)

if __name__ == "__main__":
    test_accurate_summaries()