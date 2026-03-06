#!/usr/bin/env python3
"""
Enhanced AI-powered content analysis with OpenAI
Replaces rule-based extraction with intelligent analysis
"""

import os
import openai
from dotenv import load_dotenv
from content_parser import parse_meeting_name

def get_ai_insights_and_company_description(content, meeting_name):
    """
    Use OpenAI to extract insights AND generate company description
    Returns: (insights_dict, company_description)
    """
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return get_fallback_insights(content), "technology company"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Parse meeting name to get company
    prospect_name, company_name = parse_meeting_name(meeting_name)
    
    # Enhanced AI analysis prompt
    prompt = f"""Analyze this sales meeting content and extract key insights:

MEETING: {meeting_name}
CONTENT: {content[:3000]}  

Please provide:

1. COMPANY DESCRIPTION for the PROSPECT/CLIENT company "{company_name}" (NOT Telnyx):
   - What business/industry is {company_name} in?
   - What does {company_name} sell or provide?
   - Target market or customers of {company_name}
   - Business model of {company_name} if clear
   - Format as: "descriptive business phrase" (100-200 chars)
   - Focus on the CLIENT company, not Telnyx

2. PAIN POINTS (3 key challenges mentioned):
   - Specific problems or frustrations discussed
   - Technical or business challenges
   - Implementation concerns

3. PRODUCT FOCUS (products/services discussed):
   - Which Telnyx products were mentioned or relevant
   - APIs, services, or solutions of interest

4. NEXT STEPS (actions mentioned):
   - Follow-up activities planned
   - Technical evaluations needed
   - Decision timelines mentioned

Format your response as JSON:
{{
  "company_description": "detailed business description here",
  "pain_points": ["point 1", "point 2", "point 3"],
  "products": ["product 1", "product 2"],
  "next_steps": ["step 1", "step 2"],
  "attendees": ["email1@domain.com", "email2@domain.com"]
}}

Focus on being specific and actionable. Extract actual content, don't invent details."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for best analysis quality
            messages=[
                {"role": "system", "content": "You are a sales intelligence analyst who extracts actionable insights from meeting transcripts and identifies business models."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        try:
            # Clean AI response (remove markdown code blocks if present)
            clean_response = ai_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]  # Remove ```json
            if clean_response.startswith('```'):
                clean_response = clean_response[3:]   # Remove ```
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]  # Remove trailing ```
            
            analysis = json.loads(clean_response)
            
            # Structure insights in our expected format
            insights = {
                'pain_points': analysis.get('pain_points', [])[:3],
                'products': analysis.get('products', [])[:3],
                'next_steps': analysis.get('next_steps', [])[:3],
                'attendees': analysis.get('attendees', [])[:5],
                'company_info': analysis.get('company_description', '')
            }
            
            # Clean company description
            company_desc = analysis.get('company_description', '').strip()
            if len(company_desc) > 200:
                company_desc = company_desc[:197] + "..."
            
            return insights, company_desc
            
        except json.JSONDecodeError:
            print(f"  ⚠️ AI response not valid JSON, using fallback")
            return get_fallback_insights(content), f"technology company in {company_name.lower()} sector"
        
    except Exception as e:
        print(f"  ⚠️ OpenAI API error: {str(e)[:50]}")
        return get_fallback_insights(content), "technology company"

def get_fallback_insights(content):
    """Fallback to rule-based extraction if AI fails"""
    # Import the original function as fallback
    from content_parser import extract_insights_from_content
    return extract_insights_from_content(content)

def get_enhanced_company_description(company_name, company_domain=None, context_content=""):
    """
    Generate rich company description using AI with context
    This is the standalone version for cases without meeting content
    """
    
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "technology company"
    
    client = openai.OpenAI(api_key=api_key)
    
    # Enhanced prompt with context
    domain_info = f" (website: {company_domain})" if company_domain else ""
    context_info = f"\n\nContext from meeting: {context_content[:500]}" if context_content else ""
    
    prompt = f"""What type of business is {company_name}{domain_info}?{context_info}

Provide a detailed business description that covers:
- Specific industry/sector and niche
- What products/services they provide
- Target market and customer types
- Business model or revenue approach
- Geographic focus if relevant
- Key differentiators if clear

Format as a descriptive phrase for: "CompanyName is a ___"

Examples:
✅ "peer-to-peer lending platform connecting European investors with company loans in regulated marketplace"
✅ "AI-powered lead generation and sales automation platform for B2B technology companies"
✅ "call tracking and marketing attribution software helping agencies measure ROI across channels"

Aim for 100-200 characters. Be specific and professional."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You create detailed, accurate business descriptions based on company names, domains, and context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=80,
            temperature=0.3
        )
        
        description = response.choices[0].message.content.strip()
        
        # Clean up
        if description.startswith('"') and description.endswith('"'):
            description = description[1:-1]
        
        # Remove company name prefixes
        prefixes = [f"{company_name} is a ", f"{company_name} is an ", "is a ", "is an "]
        # Add more generic prefixes
        prefixes.extend(["is a ", "is an ", "a ", "an "])
        for prefix in prefixes:
            if description.startswith(prefix):
                description = description[len(prefix):].strip()
                break
        
        return description[:200].strip()
        
    except Exception as e:
        return "technology company exploring communications solutions"

# Test function
def test_ai_analysis():
    """Test the enhanced AI analysis"""
    
    test_content = """
    Meeting with Afranga team to discuss their peer-to-peer lending platform.
    They're facing challenges with payment processing for their European loan marketplace.
    Key pain points include high transaction fees and slow settlement times for investor payouts.
    They're interested in Telnyx's Voice API for customer support calls and SMS for loan notifications.
    Next steps: Technical evaluation of payment APIs and implementation timeline discussion.
    Attendees: john@afranga.com, sarah.tech@afranga.com
    """
    
    test_meeting = "Afranga -- Telnyx Integration Call"
    
    print("🧪 TESTING AI-ENHANCED ANALYSIS")
    print("=" * 35)
    
    insights, company_desc = get_ai_insights_and_company_description(test_content, test_meeting)
    
    print(f"🏢 Company Description: {company_desc}")
    print(f"🔴 Pain Points: {insights['pain_points']}")
    print(f"💡 Products: {insights['products']}")
    print(f"🚀 Next Steps: {insights['next_steps']}")
    print(f"👥 Attendees: {insights['attendees']}")

if __name__ == "__main__":
    test_ai_analysis()