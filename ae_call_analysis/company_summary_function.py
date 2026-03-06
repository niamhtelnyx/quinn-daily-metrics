#!/usr/bin/env python3
"""
Company summary function for Slack integration
Optimized for brevity and accuracy
"""

import os
import openai
from dotenv import load_dotenv

def get_company_summary(company_name, company_domain=None):
    """
    Generate concise company summary for Slack posts
    Returns: Short business description (max 80 chars)
    """
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "technology company exploring communications solutions"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Optimized prompt for Slack format
    domain_context = f" (domain: {company_domain})" if company_domain else ""
    
    prompt = f"""Create a brief business description for "{company_name}"{domain_context}.

Requirements:
- Maximum 80 characters total
- Start with a verb (e.g., "provides", "develops", "offers")
- Focus on what they DO
- Be specific when possible, generic when necessary

Examples:
✅ "provides payment processing for online businesses" (50 chars)
✅ "develops AI customer support automation" (41 chars)
✅ "offers cloud inventory management software" (44 chars)
✅ "operates e-commerce marketplace platform" (40 chars)

For unknown companies, use:
"provides technology solutions for [relevant industry]"

Return only the description, no quotes or extra text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You create concise business descriptions under 80 characters."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=40,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Clean and validate
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        
        # Ensure it's under 80 characters
        if len(summary) > 80:
            summary = summary[:77] + "..."
        
        return summary.lower()  # Consistent lowercase for Slack
        
    except Exception as e:
        # Fallback for API errors
        return "technology company exploring communications solutions"

def test_company_summaries():
    """Test the function with various companies"""
    
    print("🧪 SLACK-OPTIMIZED COMPANY SUMMARY TEST")
    print("=" * 40)
    
    test_companies = [
        ("Afranga", "afranga.com"),
        ("Stripe", "stripe.com"),
        ("Matelso", None),
        ("PracticePilotAI", "practicepilot.ai"),
        ("Commercials", None),
        ("Unknown Corp", "unknown123.com")
    ]
    
    for company_name, domain in test_companies:
        print(f"\n🏢 {company_name}" + (f" ({domain})" if domain else ""))
        summary = get_company_summary(company_name, domain)
        
        print(f"📋 Summary: {summary}")
        print(f"📏 Length: {len(summary)}/80 chars")
        
        # Preview in Slack format
        print(f"📱 Slack preview: '{company_name} {summary} is exploring...'")
        
        if len(summary) <= 80:
            print("✅ Fits Slack format")
        else:
            print("❌ Too long for Slack")

if __name__ == "__main__":
    test_company_summaries()