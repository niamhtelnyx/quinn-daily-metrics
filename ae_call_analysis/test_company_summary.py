#!/usr/bin/env python3
"""
Test OpenAI API call for company summary generation
Test case: afranga.com
"""

import os
import openai
from dotenv import load_dotenv

def get_company_summary(company_domain):
    """Generate 1-sentence company summary using OpenAI API"""
    
    # Load environment variables
    load_dotenv('.env')
    
    # Set up OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "❌ No OpenAI API key found"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Prompt for company summary
    prompt = f"""Based on the company domain {company_domain}, provide a concise 1-sentence summary of what this company does. 

Requirements:
- Maximum 25 words
- Focus on their core business/product
- Professional tone
- No speculation if unclear
- If domain doesn't resolve or is unclear, say "Technology company"

Just return the summary sentence, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective for this task
            messages=[
                {"role": "system", "content": "You are a business analyst who creates concise company descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3  # Lower temperature for consistency
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        return f"❌ OpenAI API error: {str(e)[:50]}"

def main():
    """Test company summary generation"""
    print("🧪 TESTING OPENAI COMPANY SUMMARY GENERATION")
    print("=" * 45)
    
    # Test with afranga.com
    test_domain = "afranga.com"
    print(f"📋 Testing domain: {test_domain}")
    print()
    
    print("🔍 Calling OpenAI API...")
    summary = get_company_summary(test_domain)
    
    print("📊 RESULT:")
    print(f"   {summary}")
    print()
    print(f"📏 Length: {len(summary)} characters")
    
    # Test with a few more domains for comparison
    test_domains = ["stripe.com", "unknown-domain-xyz.com", "afranga.com"]
    
    print("\n🔬 ADDITIONAL TESTS:")
    print("-" * 30)
    
    for domain in test_domains:
        summary = get_company_summary(domain)
        print(f"🏢 {domain}")
        print(f"   {summary}")
        print(f"   ({len(summary)} chars)")
        print()

if __name__ == "__main__":
    main()