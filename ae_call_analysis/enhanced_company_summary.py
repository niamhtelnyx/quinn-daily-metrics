#!/usr/bin/env python3
"""
Enhanced company summary with web research capability
"""

import os
import openai
import requests
from dotenv import load_dotenv

def search_company_info(company_domain):
    """Search for company information using web search"""
    try:
        # Use web_search function from our existing tools
        import sys
        sys.path.append('/Users/niamhcollins/clawd')
        
        # Try to import web_search from clawdbot tools
        # For now, let's use a simple approach
        search_query = f"what does {company_domain} company do business"
        
        # Placeholder for actual web search - would integrate with web_search tool
        return f"Search results for {company_domain}"
        
    except:
        return None

def get_enhanced_company_summary(company_name, company_domain=None):
    """Generate company summary with optional web research"""
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "❌ No OpenAI API key found"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Enhanced prompt with multiple approaches
    prompt = f"""Create a concise 1-sentence summary for the company "{company_name}"{f" (domain: {company_domain})" if company_domain else ""}.

Try these approaches in order:
1. If you know this company, describe their core business
2. If unclear, use the domain name to infer their likely business
3. If still unclear, use "Technology company exploring communications solutions"

Requirements:
- Maximum 20 words
- Professional and specific when possible
- Focus on what they DO, not who they are
- Examples:
  ✅ "Provides payment processing solutions for e-commerce businesses"
  ✅ "Develops AI-powered customer support automation tools"  
  ✅ "Offers cloud-based inventory management software"
  ❌ "Is a technology company" (too generic)

Return only the summary sentence."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a business analyst who creates specific, actionable company descriptions based on available information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.4
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Clean up the response
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        
        return summary
        
    except Exception as e:
        return f"❌ OpenAI API error: {str(e)[:50]}"

def main():
    """Test enhanced company summary"""
    print("🚀 ENHANCED COMPANY SUMMARY TEST")
    print("=" * 35)
    
    # Test cases
    test_companies = [
        ("Afranga", "afranga.com"),
        ("Stripe", "stripe.com"),  
        ("Matelso", "matelso.com"),
        ("PracticePilotAI", "practicepilot.ai"),
        ("Commercials", None),  # Name only
        ("Trendyol", "trendyol.com")
    ]
    
    for company_name, domain in test_companies:
        print(f"\n🏢 Testing: {company_name}" + (f" ({domain})" if domain else ""))
        print("-" * 40)
        
        summary = get_enhanced_company_summary(company_name, domain)
        
        print(f"📋 Summary: {summary}")
        print(f"📏 Length: {len(summary)} characters")
        
        # Check if it's too generic
        if "technology company" in summary.lower() and len(summary) < 30:
            print("⚠️  Generic fallback - may need web research")
        else:
            print("✅ Specific business description")

if __name__ == "__main__":
    main()